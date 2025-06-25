"""Main FastAPI application for Silero VAD service."""

import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
import structlog
import uvicorn

from app.config import settings
from app.kafka_consumer import KafkaVADConsumer
from app.vad_processor import VADProcessor

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

logger = structlog.get_logger(__name__)

# Global instances
consumer: KafkaVADConsumer = None
consumer_task: asyncio.Task = None
vad_processor: VADProcessor = None
model_loaded: bool = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global consumer, consumer_task, vad_processor
    
    logger.info(
        "Starting Silero VAD service",
        environment=settings.environment,
        log_level=settings.log_level,
    )
    
    # Initialize VAD processor (but don't load model yet)
    vad_processor = VADProcessor()
    
    # Initialize consumer
    consumer = KafkaVADConsumer()
    
    try:
        # Start consumer
        await consumer.start()
        
        # Create consumer task
        consumer_task = asyncio.create_task(consumer.consume())
        
        logger.info("Silero VAD service started successfully")
        
        yield
        
    finally:
        logger.info("Shutting down Silero VAD service")
        
        # Stop consumer
        if consumer:
            await consumer.stop()
        
        # Cancel consumer task
        if consumer_task and not consumer_task.done():
            consumer_task.cancel()
            try:
                await consumer_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Silero VAD service shut down")


# Create FastAPI app
app = FastAPI(
    title="Silero VAD Service",
    description="Voice Activity Detection service using Silero VAD",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/healthz", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, str]:
    """Liveness probe endpoint."""
    return {"status": "healthy"}


@app.get("/readyz", status_code=status.HTTP_200_OK)
async def readiness_check() -> JSONResponse:
    """Readiness probe endpoint."""
    global model_loaded
    
    if not consumer or not consumer._running:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not ready", "reason": "Consumer not running"},
        )
    
    if not model_loaded:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not ready", "reason": "VAD model not loaded"},
        )
    
    # Check consumer health
    health = await consumer.health_check()
    
    if health["status"] != "healthy":
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "degraded", "details": health},
        )
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "ready", "model_loaded": model_loaded, "details": health},
    )


@app.post("/warmup", status_code=status.HTTP_200_OK)
async def warmup() -> JSONResponse:
    """Warmup endpoint to preload VAD model."""
    global model_loaded, vad_processor
    
    if model_loaded:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "already_loaded", "message": "VAD model already loaded"},
        )
    
    if not vad_processor:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "error", "message": "VAD processor not initialized"},
        )
    
    try:
        logger.info("Starting VAD model warmup")
        await vad_processor.initialize()
        model_loaded = True
        logger.info("VAD model warmup completed successfully")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "success", 
                "message": "VAD model loaded successfully",
                "model_loaded": True
            },
        )
    except Exception as e:
        logger.error("VAD model warmup failed", error=str(e))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": "error", "message": f"Model loading failed: {str(e)}"},
        )


@app.get("/metrics")
async def metrics() -> Dict[str, Any]:
    """Metrics endpoint for monitoring."""
    if not consumer:
        return {"status": "no_consumer"}
    
    health = await consumer.health_check()
    
    return {
        "service": settings.service_name,
        "environment": settings.environment,
        "model_loaded": model_loaded,
        "consumer": health,
    }


@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint."""
    return {
        "service": settings.service_name,
        "version": "0.1.0",
        "status": "running",
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=settings.debug,
    )