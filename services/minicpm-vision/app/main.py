"""Main FastAPI application for MiniCPM-Vision service."""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any

import structlog
from fastapi import FastAPI, HTTPException, status
from prometheus_client import Counter, Histogram, generate_latest
from starlette.responses import Response

from app.config import settings
from app.kafka_consumer import create_and_run_consumer
from app.models import HealthStatus

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
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Prometheus metrics
REQUEST_COUNT = Counter(
    "minicpm_vision_requests_total",
    "Total requests",
    ["method", "endpoint", "status"],
)
REQUEST_DURATION = Histogram(
    "minicpm_vision_request_duration_seconds",
    "Request duration",
    ["method", "endpoint"],
)
IMAGES_PROCESSED = Counter(
    "minicpm_vision_images_processed_total",
    "Total images processed",
    ["status"],
)

# Global state
kafka_consumer_task = None
app_ready = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global kafka_consumer_task, app_ready
    
    logger.info(
        "Starting MiniCPM-Vision service",
        environment=settings.environment,
        kafka_servers=settings.kafka_bootstrap_servers,
        input_topics=settings.kafka_input_topics,
        output_topic=settings.kafka_output_topic,
    )
    
    try:
        # Start Kafka consumer in background
        kafka_consumer_task = asyncio.create_task(
            create_and_run_consumer(
                bootstrap_servers=settings.kafka_bootstrap_servers,
                input_topics=settings.kafka_input_topics,
                output_topic=settings.kafka_output_topic,
                consumer_group=settings.kafka_consumer_group,
                device=settings.model_device,
            )
        )
        
        # Give consumer time to initialize
        await asyncio.sleep(5)
        app_ready = True
        
        logger.info("MiniCPM-Vision service started successfully")
        
        yield
        
    except Exception as e:
        logger.error("Failed to start service", error=str(e))
        raise
        
    finally:
        app_ready = False
        
        # Cancel consumer task
        if kafka_consumer_task and not kafka_consumer_task.done():
            kafka_consumer_task.cancel()
            try:
                await kafka_consumer_task
            except asyncio.CancelledError:
                pass
                
        logger.info("MiniCPM-Vision service stopped")


# Create FastAPI app
app = FastAPI(
    title="MiniCPM-Vision Service",
    description="Vision-Language analysis service using MiniCPM-Llama3-V 2.5",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/healthz", response_model=HealthStatus)
async def health_check() -> HealthStatus:
    """Liveness probe endpoint."""
    return HealthStatus(
        status="healthy",
        timestamp=datetime.utcnow(),
    )


@app.get("/readyz", response_model=HealthStatus)
async def readiness_check() -> HealthStatus:
    """Readiness probe endpoint."""
    global app_ready
    
    checks = {
        "app_initialized": app_ready,
        "kafka_consumer": kafka_consumer_task is not None and not kafka_consumer_task.done(),
    }
    
    if all(checks.values()):
        return HealthStatus(
            status="ready",
            timestamp=datetime.utcnow(),
            checks=checks,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not_ready",
                "timestamp": datetime.utcnow().isoformat(),
                "checks": checks,
            },
        )


@app.get("/metrics")
async def metrics() -> Response:
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type="text/plain; version=0.0.4",
    )


@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint with service information."""
    return {
        "service": settings.service_name,
        "version": "0.1.0",
        "status": "running",
        "environment": settings.environment,
        "model": settings.model_name,
        "device": settings.model_device or "auto",
        "input_topics": settings.kafka_input_topics,
        "output_topic": settings.kafka_output_topic,
    }


@app.get("/status")
async def status() -> Dict[str, Any]:
    """Detailed status endpoint."""
    global kafka_consumer_task
    
    return {
        "service": settings.service_name,
        "timestamp": datetime.utcnow().isoformat(),
        "ready": app_ready,
        "kafka_consumer": {
            "running": kafka_consumer_task is not None and not kafka_consumer_task.done(),
            "task_done": kafka_consumer_task.done() if kafka_consumer_task else None,
        },
        "configuration": {
            "kafka_servers": settings.kafka_bootstrap_servers,
            "input_topics": settings.kafka_input_topics,
            "output_topic": settings.kafka_output_topic,
            "consumer_group": settings.kafka_consumer_group,
            "model_device": settings.model_device or "auto",
        },
    }


# Add middleware for metrics
@app.middleware("http")
async def track_metrics(request, call_next):
    """Track request metrics."""
    import time
    
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    # Record metrics
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code,
    ).inc()
    
    REQUEST_DURATION.labels(
        method=request.method,
        endpoint=request.url.path,
    ).observe(duration)
    
    return response


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=settings.environment == "development",
    )