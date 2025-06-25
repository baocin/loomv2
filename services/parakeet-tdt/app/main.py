"""Main FastAPI application for Parakeet-TDT service."""

from contextlib import asynccontextmanager
from typing import Any

import structlog
import torch
from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from app.asr_processor import ASRProcessor
from app.config import settings
from app.kafka_consumer import KafkaConsumer

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        (structlog.processors.JSONRenderer() if settings.log_format == "json" else structlog.dev.ConsoleRenderer()),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Prometheus metrics
audio_chunks_processed = Counter("parakeet_audio_chunks_processed_total", "Total number of audio chunks processed")
transcripts_produced = Counter("parakeet_transcripts_produced_total", "Total number of transcripts produced")
processing_duration = Histogram("parakeet_processing_duration_seconds", "Time spent processing audio chunks")

# Global instances
kafka_consumer = KafkaConsumer()
asr_processor: ASRProcessor = None
model_loaded = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global asr_processor

    logger.info(
        "Starting Parakeet-TDT service",
        environment=settings.environment,
        device=settings.model_device,
        cuda_available=torch.cuda.is_available(),
    )

    # Initialize ASR processor (but don't load model yet)
    asr_processor = ASRProcessor()

    try:
        # Start Kafka consumer
        await kafka_consumer.start()
        logger.info("Parakeet-TDT service started successfully")

        yield

    finally:
        logger.info("Shutting down Parakeet-TDT service")
        await kafka_consumer.stop()
        logger.info("Parakeet-TDT service stopped")


# Create FastAPI app
app = FastAPI(
    title="Parakeet-TDT Speech-to-Text Service",
    description="NVIDIA Parakeet-TDT ASR service for Loom v2",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/healthz")
async def health() -> dict[str, str]:
    """Health check endpoint for Kubernetes liveness probe."""
    return {"status": "healthy", "service": settings.service_name}


@app.get("/readyz")
async def readiness() -> dict[str, Any]:
    """Readiness check endpoint for Kubernetes readiness probe."""
    global model_loaded

    ready = True
    checks = {
        "service": settings.service_name,
        "kafka_consumer": kafka_consumer.running,
        "model_loaded": model_loaded,
        "device": settings.model_device,
        "cuda_available": torch.cuda.is_available(),
    }

    # Check if all components are ready
    if not kafka_consumer.running or not model_loaded:
        ready = False

    return {"ready": ready, "checks": checks}


@app.post("/warmup")
async def warmup() -> dict[str, Any]:
    """Warmup endpoint to preload ASR model."""
    global model_loaded, asr_processor

    if model_loaded:
        return {
            "status": "already_loaded",
            "message": "ASR model already loaded",
            "model_loaded": True,
        }

    if not asr_processor:
        return {
            "status": "error",
            "message": "ASR processor not initialized",
        }

    try:
        logger.info("Starting ASR model warmup")
        await asr_processor.initialize()
        model_loaded = True
        logger.info("ASR model warmup completed successfully")

        return {
            "status": "success",
            "message": "ASR model loaded successfully",
            "model_loaded": True,
            "device": asr_processor.device,
            "model": settings.model_name,
        }

    except Exception as e:
        logger.error("ASR model warmup failed", error=str(e))
        return {
            "status": "error",
            "message": f"Model loading failed: {e!s}",
        }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": settings.service_name,
        "version": "1.0.0",
        "environment": settings.environment,
        "model": settings.model_name,
        "device": settings.model_device,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )
