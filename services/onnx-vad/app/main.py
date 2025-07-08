"""Main FastAPI application for ONNX-VAD service."""

from contextlib import asynccontextmanager
from typing import Any

import structlog
import torch
from fastapi import FastAPI, File, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
    Counter,
    Histogram,
    generate_latest,
)

from app.config import settings
from app.kafka_consumer import KafkaConsumer
from app.onnx_vad_processor import ONNXVADProcessor

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
        (
            structlog.processors.JSONRenderer()
            if settings.log_format == "json"
            else structlog.dev.ConsoleRenderer()
        ),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Prometheus metrics - initialize only once
if "onnx_vad_audio_chunks_processed_total" not in REGISTRY._names_to_collectors:
    audio_chunks_processed = Counter(
        "onnx_vad_audio_chunks_processed_total",
        "Total number of audio chunks processed",
    )
    speech_chunks_produced = Counter(
        "onnx_vad_speech_chunks_produced_total",
        "Total number of speech chunks produced",
    )
    processing_duration = Histogram(
        "onnx_vad_processing_duration_seconds", "Time spent processing audio chunks"
    )
else:
    # Metrics already registered
    audio_chunks_processed = REGISTRY._names_to_collectors[
        "onnx_vad_audio_chunks_processed_total"
    ]
    speech_chunks_produced = REGISTRY._names_to_collectors[
        "onnx_vad_speech_chunks_produced_total"
    ]
    processing_duration = REGISTRY._names_to_collectors[
        "onnx_vad_processing_duration_seconds"
    ]

# Global instances
kafka_consumer = KafkaConsumer()
vad_processor: ONNXVADProcessor = None
model_loaded = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global vad_processor

    logger.info(
        "Starting ONNX-VAD service",
        environment=settings.environment,
        device=settings.model_device,
        cuda_available=torch.cuda.is_available(),
    )

    # Initialize VAD processor (but don't load model yet)
    vad_processor = ONNXVADProcessor()

    try:
        # Start Kafka consumer (this will initialize the VAD model)
        await kafka_consumer.start()

        # Mark model as loaded since consumer.start() initializes it
        global model_loaded
        model_loaded = True

        logger.info("ONNX-VAD service started successfully, model loaded")

        yield

    finally:
        logger.info("Shutting down ONNX-VAD service")
        await kafka_consumer.stop()
        logger.info("ONNX-VAD service stopped")


# Create FastAPI app
app = FastAPI(
    title="ONNX-VAD Voice Activity Detection Service",
    description="ONNX-based VAD service for Loom v2",
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
    """Warmup endpoint to preload VAD model."""
    global model_loaded, vad_processor

    if model_loaded:
        return {
            "status": "already_loaded",
            "message": "VAD model already loaded",
            "model_loaded": True,
        }

    if not vad_processor:
        return {
            "status": "error",
            "message": "VAD processor not initialized",
        }

    try:
        logger.info("Starting VAD model warmup")
        await vad_processor.initialize()
        model_loaded = True
        logger.info("VAD model warmup completed successfully")

        return {
            "status": "success",
            "message": "VAD model loaded successfully",
            "model_loaded": True,
            "device": vad_processor.device,
            "model": settings.model_name,
        }

    except Exception as e:
        logger.error("VAD model warmup failed", error=str(e))
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
        "threshold": settings.vad_threshold,
    }


@app.post("/detect")
async def detect_speech(file: bytes = File(...)):
    """Direct VAD detection endpoint for testing."""
    import base64
    from datetime import datetime

    from app.models import AudioChunk

    global vad_processor

    if not vad_processor:
        return {"error": "VAD processor not initialized"}

    try:
        # Create a mock audio chunk
        audio_b64 = base64.b64encode(file).decode("utf-8")
        chunk = AudioChunk(
            device_id="test-device",
            recorded_at=datetime.utcnow().isoformat() + "Z",
            timestamp=datetime.utcnow().isoformat() + "Z",
            audio_data=audio_b64,
            format="wav",  # Assume WAV for testing
            sample_rate=16000,
            duration_seconds=5.0,  # Will be calculated properly by processor
            channels=1,
            chunk_number=1,
            file_id="test-file",
        )

        # Process the audio
        result = await vad_processor.process_audio_chunk(chunk)

        if result:
            return {
                "success": True,
                "speech_detected": result.speech_detected,
                "speech_probability": result.speech_probability,
                "speech_segments": result.speech_segments,
                "total_speech_duration": result.total_speech_duration,
                "processing_time_ms": result.processing_time_ms,
            }
        else:
            return {
                "success": True,
                "speech_detected": False,
                "message": "No speech detected",
            }

    except Exception as e:
        logger.error("VAD detection failed", error=str(e))
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )
