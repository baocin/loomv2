"""Main application for face emotion detection service."""

import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.config import settings
from app.kafka_consumer import KafkaFaceEmotionConsumer

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Global consumer instance
consumer = KafkaFaceEmotionConsumer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting face emotion detection service")
    await consumer.start()

    # Start consumption task
    consumption_task = asyncio.create_task(consumer.consume())

    yield

    # Shutdown
    logger.info("Shutting down face emotion detection service")
    await consumer.stop()
    consumption_task.cancel()

    try:
        await consumption_task
    except asyncio.CancelledError:
        pass


# Create FastAPI app
app = FastAPI(
    title="Face Emotion Detection Service",
    description="Face emotion recognition using Laion Empathic-Insight-Face",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/healthz")
async def health_check():
    """Health check endpoint."""
    health = await consumer.health_check()
    status_code = 200 if health["status"] == "healthy" else 503

    return JSONResponse(
        content={
            "status": health["status"],
            "service": settings.service_name,
            "version": "0.1.0",
            "details": health,
        },
        status_code=status_code,
    )


@app.get("/readyz")
async def readiness_check():
    """Readiness check endpoint."""
    health = await consumer.health_check()
    ready = (
        health["status"] == "healthy"
        and health.get("consumer_connected", False)
        and health.get("producer_connected", False)
        and health.get("face_processor_initialized", False)
    )

    return JSONResponse(
        content={
            "ready": ready,
            "service": settings.service_name,
            "details": health,
        },
        status_code=200 if ready else 503,
    )


@app.get("/status")
async def get_status():
    """Get detailed service status."""
    health = await consumer.health_check()

    return JSONResponse(
        content={
            "service": settings.service_name,
            "version": "0.1.0",
            "environment": settings.environment,
            "kafka": {
                "input_topic": settings.kafka_input_topic,
                "output_topic": settings.kafka_output_topic,
                "consumer_group": settings.kafka_consumer_group,
                "bootstrap_servers": settings.kafka_bootstrap_servers,
            },
            "model": {
                "name": settings.model_name,
                "device": settings.model_device,
                "cache_dir": settings.model_cache_dir,
            },
            "health": health,
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=settings.debug,
    )