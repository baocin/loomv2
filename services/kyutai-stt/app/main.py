"""Main FastAPI application for Kyutai-STT service."""

from contextlib import asynccontextmanager
from typing import Any

import structlog
import torch
from fastapi import FastAPI, Response, File, UploadFile
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from app.simple_kyutai_processor import SimpleKyutaiProcessor
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

# Prometheus metrics
audio_chunks_processed = Counter(
    "kyutai_audio_chunks_processed_total", "Total number of audio chunks processed"
)
transcripts_produced = Counter(
    "kyutai_transcripts_produced_total", "Total number of transcripts produced"
)
processing_duration = Histogram(
    "kyutai_processing_duration_seconds", "Time spent processing audio chunks"
)

# Global instances
kafka_consumer = KafkaConsumer()
asr_processor: SimpleKyutaiProcessor = None
model_loaded = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global asr_processor

    logger.info(
        "Starting Kyutai-STT service",
        environment=settings.environment,
        device=settings.model_device,
        cuda_available=torch.cuda.is_available(),
    )

    # Initialize ASR processor (but don't load model yet)
    asr_processor = SimpleKyutaiProcessor()

    try:
        # Start Kafka consumer (this will initialize the ASR model)
        await kafka_consumer.start()

        # Mark model as loaded since consumer.start() initializes it
        global model_loaded
        model_loaded = True

        logger.info("Kyutai-STT service started successfully, model loaded")

        yield

    finally:
        logger.info("Shutting down Kyutai-STT service")
        await kafka_consumer.stop()
        logger.info("Kyutai-STT service stopped")


# Create FastAPI app
app = FastAPI(
    title="Kyutai-STT Speech-to-Text Service",
    description="Kyutai Mimi STT service for Loom v2",
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


@app.post("/transcribe")
async def transcribe_audio(file: bytes = File(...)):
    """Direct transcription endpoint for testing."""
    import base64
    from app.models import AudioChunk
    from datetime import datetime
    
    global asr_processor
    
    if not asr_processor:
        return {"error": "ASR processor not initialized"}
    
    try:
        # Create a mock audio chunk
        audio_b64 = base64.b64encode(file).decode('utf-8')
        chunk = AudioChunk(
            device_id="test-device",
            recorded_at=datetime.utcnow().isoformat() + "Z",
            timestamp=datetime.utcnow().isoformat() + "Z",
            audio_data=audio_b64,
            format="mp3",
            sample_rate=16000,
            duration_seconds=5.0,  # Will be calculated properly by processor
            channels=1,
            chunk_number=1,
            file_id="test-file"
        )
        
        # Process the audio
        result = await asr_processor.process_audio_chunk(chunk)
        
        if result:
            return {
                "success": True,
                "text": result.text,
                "words": [{"word": w.word, "start": w.start_time, "end": w.end_time} for w in result.words],
                "processing_time_ms": result.processing_time_ms
            }
        else:
            return {"success": False, "error": "No transcription result"}
            
    except Exception as e:
        logger.error("Transcription failed", error=str(e))
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )
