"""Main FastAPI application for Gemma 3N Processor service."""

import asyncio
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest
from starlette.responses import Response

from .config import settings
from .kafka_consumer import KafkaConsumerManager
from .models import (
    HealthStatus,
    MultimodalRequest,
    ProcessingMetrics,
)
from .ollama_client import OllamaClient

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
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Prometheus metrics
REQUEST_COUNT = Counter(
    "gemma3n_requests_total",
    "Total number of requests processed",
    ["method", "endpoint", "status"],
)

REQUEST_DURATION = Histogram(
    "gemma3n_request_duration_seconds",
    "Request duration in seconds",
    ["method", "endpoint"],
)

PROCESSING_TIME = Histogram(
    "gemma3n_processing_time_seconds",
    "Processing time for multimodal analysis",
    ["modality_type"],
)

# Global state
ollama_client: Optional[OllamaClient] = None
kafka_consumer: Optional[KafkaConsumerManager] = None
processing_metrics = ProcessingMetrics()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    global ollama_client, kafka_consumer

    logger.info("Starting Gemma 3N Processor service", version="0.1.0")

    # Initialize Ollama client
    ollama_client = OllamaClient()

    # Wait for Ollama to be ready and pull model
    max_retries = 30
    for attempt in range(max_retries):
        if await ollama_client.health_check():
            logger.info("Ollama server is ready")
            break
        logger.info(f"Waiting for Ollama server... attempt {attempt + 1}/{max_retries}")
        await asyncio.sleep(2)
    else:
        logger.error("Ollama server not ready after maximum retries")
        raise RuntimeError("Ollama server unavailable")

    # Ensure model is available
    models = await ollama_client.list_models()
    if settings.ollama_model not in models:
        logger.info("Pulling Gemma 3N model", model=settings.ollama_model)
        await ollama_client.pull_model()

    # Initialize Kafka consumer
    kafka_consumer = KafkaConsumerManager(ollama_client)

    # Start background Kafka consumption
    kafka_task = asyncio.create_task(kafka_consumer.start_consuming())

    logger.info("Service startup completed")

    yield

    # Cleanup
    logger.info("Shutting down Gemma 3N Processor service")
    if kafka_consumer:
        await kafka_consumer.stop()
    kafka_task.cancel()
    logger.info("Service shutdown completed")


# Create FastAPI app
app = FastAPI(
    title="Gemma 3N Processor",
    description="Multimodal processing service using Gemma 3N via Ollama",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def metrics_middleware(request, call_next):
    """Middleware to collect metrics."""
    start_time = time.time()

    response = await call_next(request)

    # Record metrics
    duration = time.time() - start_time
    REQUEST_COUNT.labels(
        method=request.method, endpoint=request.url.path, status=response.status_code
    ).inc()

    REQUEST_DURATION.labels(method=request.method, endpoint=request.url.path).observe(
        duration
    )

    return response


@app.get("/healthz")
async def health_check():
    """Liveness probe - simple health check."""
    return {"status": "healthy", "timestamp": datetime.utcnow()}


@app.get("/readyz")
async def readiness_check():
    """Readiness probe - check dependencies."""
    checks = {}
    overall_status = "healthy"

    # Check Ollama
    if ollama_client:
        checks["ollama"] = await ollama_client.health_check()
        if not checks["ollama"]:
            overall_status = "unhealthy"
    else:
        checks["ollama"] = False
        overall_status = "unhealthy"

    # Check Kafka (basic connectivity)
    if kafka_consumer:
        checks["kafka"] = kafka_consumer.is_healthy()
        if not checks["kafka"]:
            overall_status = "unhealthy"
    else:
        checks["kafka"] = False
        overall_status = "unhealthy"

    status_code = 200 if overall_status == "healthy" else 503

    return Response(
        content=HealthStatus(status=overall_status, checks=checks).model_dump_json(),
        status_code=status_code,
        media_type="application/json",
    )


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type="text/plain")


@app.get("/status")
async def service_status():
    """Service status and metrics."""
    if not ollama_client:
        raise HTTPException(status_code=503, detail="Service not ready")

    models = await ollama_client.list_models()

    return {
        "service": "gemma3n-processor",
        "version": "0.1.0",
        "status": "running",
        "models": models,
        "current_model": settings.ollama_model,
        "processing_metrics": processing_metrics.model_dump(),
        "kafka_topics": settings.kafka_input_topics,
        "output_topic": settings.kafka_output_topic,
    }


@app.post("/process/text")
async def process_text(
    prompt: str,
    context: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
):
    """Process text input using Gemma 3N."""
    if not ollama_client:
        raise HTTPException(status_code=503, detail="Service not ready")

    start_time = time.time()

    try:
        with PROCESSING_TIME.labels(modality_type="text").time():
            result = await ollama_client.generate_text(
                prompt=prompt,
                context=context,
                max_tokens=max_tokens,
                temperature=temperature,
            )

        processing_time = (time.time() - start_time) * 1000

        # Update metrics
        processing_metrics.requests_processed += 1
        processing_metrics.total_processing_time += processing_time
        processing_metrics.average_processing_time = (
            processing_metrics.total_processing_time
            / processing_metrics.requests_processed
        )
        processing_metrics.last_processed = datetime.utcnow()

        return {
            "result": result,
            "processing_time_ms": processing_time,
            "model": settings.ollama_model,
        }

    except Exception as e:
        processing_metrics.errors_count += 1
        logger.error("Text processing failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@app.post("/process/image")
async def process_image(
    image_data: str,
    prompt: str = "Describe this image in detail.",
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
):
    """Process image input using Gemma 3N."""
    if not ollama_client:
        raise HTTPException(status_code=503, detail="Service not ready")

    start_time = time.time()

    try:
        with PROCESSING_TIME.labels(modality_type="image").time():
            result = await ollama_client.analyze_image(
                image_data=image_data,
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            )

        processing_time = (time.time() - start_time) * 1000

        # Update metrics
        processing_metrics.requests_processed += 1
        processing_metrics.total_processing_time += processing_time
        processing_metrics.average_processing_time = (
            processing_metrics.total_processing_time
            / processing_metrics.requests_processed
        )
        processing_metrics.last_processed = datetime.utcnow()

        return {
            "result": result,
            "processing_time_ms": processing_time,
            "model": settings.ollama_model,
        }

    except Exception as e:
        processing_metrics.errors_count += 1
        logger.error("Image processing failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@app.post("/process/multimodal")
async def process_multimodal(request: MultimodalRequest):
    """Process multimodal input using Gemma 3N."""
    if not ollama_client:
        raise HTTPException(status_code=503, detail="Service not ready")

    start_time = time.time()

    try:
        with PROCESSING_TIME.labels(modality_type="multimodal").time():
            result = await ollama_client.process_multimodal(request)

        processing_time = (time.time() - start_time) * 1000

        # Update metrics
        processing_metrics.requests_processed += 1
        processing_metrics.total_processing_time += processing_time
        processing_metrics.average_processing_time = (
            processing_metrics.total_processing_time
            / processing_metrics.requests_processed
        )
        processing_metrics.last_processed = datetime.utcnow()

        return {
            "result": result,
            "processing_time_ms": processing_time,
            "model": settings.ollama_model,
            "modalities_processed": {
                "text": bool(request.text),
                "image": bool(request.image_data),
                "audio": bool(request.audio_data),
            },
        }

    except Exception as e:
        processing_metrics.errors_count += 1
        logger.error("Multimodal processing failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=settings.environment == "development",
    )
