"""Main FastAPI application for the ingestion service."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from .config import settings
from .kafka_producer import kafka_producer
from .kafka_topics import topic_manager
from .models import HealthCheck
from .routers import audio, sensors, system

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

# Prometheus metrics
requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)
request_duration = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
)
kafka_messages_total = Counter(
    "kafka_messages_total",
    "Total Kafka messages sent",
    ["topic", "status"],
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup and shutdown."""
    # Startup
    logger.info("Starting ingestion API service", version="0.1.0")

    try:
        # Start Kafka topic manager first
        await topic_manager.start()
        logger.info("Kafka topic manager started successfully")

        # Start Kafka producer
        await kafka_producer.start()
        logger.info("Kafka producer started successfully")

    except Exception as e:
        logger.error("Failed to start dependencies", error=str(e))
        raise

    yield

    # Shutdown
    logger.info("Shutting down ingestion API service")

    try:
        # Stop Kafka producer
        await kafka_producer.stop()
        logger.info("Kafka producer stopped successfully")

        # Stop Kafka topic manager
        await topic_manager.stop()
        logger.info("Kafka topic manager stopped successfully")

    except Exception as e:
        logger.error("Error during shutdown", error=str(e))


# Create FastAPI application
app = FastAPI(
    title="Loom Ingestion API",
    description="FastAPI service for ingesting device data into Kafka topics",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(audio.router)
app.include_router(sensors.router)
app.include_router(system.router)


@app.get("/", status_code=status.HTTP_200_OK)
async def root() -> JSONResponse:
    """Root endpoint with basic service information."""
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "service": "loom-ingestion-api",
            "version": "0.1.0",
            "description": "FastAPI service for ingesting device data into Kafka topics",
            "endpoints": {
                "health": "/healthz",
                "readiness": "/readyz",
                "audio_websocket": "/audio/stream/{device_id}",
                "audio_upload": "/audio/upload",
                "sensor_endpoints": "/sensor/*",
                "system_app_monitoring": "/system/apps/*",
                "device_metadata": "/system/metadata",
                "metrics": "/metrics",
                "docs": "/docs",
            },
        },
    )


@app.get("/healthz", status_code=status.HTTP_200_OK)
async def health_check() -> HealthCheck:
    """Kubernetes liveness probe endpoint.

    Returns
    -------
        Health status of the service

    """
    # Basic health check - service is running
    return HealthCheck(
        status="healthy",
        version="0.1.0",
        kafka_connected=kafka_producer.is_connected,
    )


@app.get("/readyz", status_code=status.HTTP_200_OK)
async def readiness_check() -> HealthCheck:
    """Kubernetes readiness probe endpoint.

    Returns
    -------
        Readiness status of the service and dependencies

    """
    # Check if all dependencies are ready
    kafka_ready = kafka_producer.is_connected

    if not kafka_ready:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "version": "0.1.0",
                "kafka_connected": kafka_ready,
                "details": "Kafka producer not connected",
            },
        )

    return HealthCheck(
        status="ready",
        version="0.1.0",
        kafka_connected=kafka_ready,
    )


@app.get("/metrics")
async def get_metrics() -> Response:
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.middleware("http")
async def add_metrics_middleware(request, call_next):
    """Middleware to collect HTTP request metrics."""
    import time

    method = request.method
    path = request.url.path

    # Start timer
    start_time = time.time()

    # Process request
    response = await call_next(request)

    # Record metrics
    duration = time.time() - start_time
    request_duration.labels(method=method, endpoint=path).observe(duration)
    requests_total.labels(
        method=method,
        endpoint=path,
        status_code=response.status_code,
    ).inc()

    return response


# Add custom exception handlers
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle unexpected exceptions."""
    logger.error(
        "Unhandled exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "message": "Internal server error",
            "request_id": getattr(request.state, "request_id", None),
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=False,  # Set to True for development
    )
