"""Main FastAPI application for the ingestion service."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from .config import settings
from .database import db_manager
from .kafka_producer import kafka_producer
from .kafka_topics import topic_manager
from .models import HealthCheck
from .routers import (
    ai_context,  # AI context endpoint
    audio,
    # devices,  # TODO: Requires database implementation
    digital,  # Digital data (clipboard, web analytics)
    documents,  # Documents router for document ingestion
    # github,  # TODO: Check if this requires database
    health_data,  # Health monitoring data
    images,  # Images router doesn't require database
    notes,  # Notes router for text notes ingestion
    os_events,  # OS event tracking
    sensors,
    system,  # System monitoring (app monitoring, device metadata)
    unified_ingestion,  # Unified data ingestion with message type mapping
)

# urls,  # TODO: Check if this requires database
from .tracing import TracingMiddleware, get_trace_context


# Configure structured logging with trace context
def add_trace_context(logger, method_name, event_dict):
    """Add trace context to all log entries."""
    trace_context = get_trace_context()
    event_dict.update(trace_context)
    return event_dict


structlog.configure(
    processors=[
        add_trace_context,
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

    # Start database connection pool if configured
    if settings.database_url:
        try:
            await db_manager.start()
            logger.info("Database connection established")
        except Exception as e:
            logger.error("Failed to connect to database", error=str(e))
            # Don't fail startup if database is not available
            # Some endpoints can still work without it

    # Retry logic for Kafka connectivity
    max_retries = 5
    retry_delay = 5  # seconds

    for attempt in range(max_retries):
        try:
            # Start Kafka topic manager first
            await topic_manager.start()
            logger.info("Kafka topic manager started successfully")

            # Start Kafka producer
            await kafka_producer.start()
            logger.info("Kafka producer started successfully")

            break  # Success, exit retry loop

        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(
                    f"Failed to connect to Kafka (attempt {attempt + 1}/{max_retries}), retrying in {retry_delay}s",
                    error=str(e),
                )
                await asyncio.sleep(retry_delay)
            else:
                logger.error(
                    "Failed to start dependencies after all retries",
                    error=str(e),
                )
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

        # Stop database connection pool
        if db_manager.is_connected:
            await db_manager.stop()
            logger.info("Database connection pool stopped successfully")

    except Exception as e:
        logger.error("Error during shutdown", error=str(e))


# Create FastAPI application
app = FastAPI(
    title="Loom Ingestion API",
    description="FastAPI service for ingesting device data into Kafka topics",
    version="0.1.0",
    lifespan=lifespan,
)

# Add tracing middleware (must be first)
app.add_middleware(TracingMiddleware, service_name="ingestion-api")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ai_context.router)  # AI context endpoint
app.include_router(audio.router)
# app.include_router(devices.router)  # TODO: Requires database implementation
app.include_router(digital.router)  # Digital data (clipboard, web analytics)
app.include_router(documents.router)  # Documents router for document ingestion
# app.include_router(github.router)  # TODO: Check if this requires database
app.include_router(health_data.router)  # Health monitoring data
app.include_router(images.router)  # Images router doesn't require database
app.include_router(notes.router)  # Notes router for text notes ingestion
app.include_router(os_events.router)  # OS event tracking
app.include_router(sensors.router)
app.include_router(system.router)  # System monitoring (app monitoring, device metadata)
app.include_router(
    unified_ingestion.router,
)  # Unified data ingestion with message type mapping
# app.include_router(meta.router, prefix="/meta", tags=["meta"])  # Meta endpoints moved to system router
# app.include_router(urls.router)  # TODO: Check if this requires database


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
                "ai_context": "/ai/context",
                "unified_ingestion": "/ingest/message",
                "message_types": "/ingest/message-types",
                "audio_websocket": "/audio/stream/{device_id}",
                "audio_upload": "/audio/upload",
                "image_upload": "/images/upload",
                "screenshot_upload": "/images/screenshot",
                "note_upload": "/notes/upload",
                "github_ingest": "/github/ingest",
                "document_upload": "/documents/upload",
                "sensor_endpoints": {
                    "gps": "/sensor/gps",
                    "accelerometer": "/sensor/accelerometer",
                    "heartrate": "/sensor/heartrate",
                    "power": "/sensor/power",
                    "wifi": "/sensor/wifi",
                    "bluetooth": "/sensor/bluetooth",
                    "temperature": "/sensor/temperature",
                    "barometer": "/sensor/barometer",
                    "light": "/sensor/light",
                    "gyroscope": "/sensor/gyroscope",
                    "magnetometer": "/sensor/magnetometer",
                    "generic": "/sensor/generic",
                    "batch": "/sensor/batch",
                },
                "health_endpoints": {
                    "steps": "/health/steps",
                    "sleep": "/health/sleep",
                    "blood_oxygen": "/health/blood-oxygen",
                    "blood_pressure": "/health/blood-pressure",
                },
                "digital_endpoints": {
                    "clipboard": "/digital/clipboard",
                    "web_analytics": "/digital/web-analytics",
                },
                "system_app_monitoring": {
                    "macos": "/system/apps/macos",
                    "android": "/system/apps/android",
                    "android_usage": "/system/apps/android/usage",
                    "android_events": "/system/apps/android/events",
                    "android_categories": "/system/apps/android/categories",
                    "stats": "/system/apps/stats",
                },
                "device_metadata": "/system/metadata",
                "os_events": {
                    "app_lifecycle": "/os-events/app-lifecycle",
                    "system": "/os-events/system",
                    "notifications": "/os-events/notifications",
                },
                "meta": {
                    "log_activity": "/meta/log_activity",
                    "consumer_activity": "/meta/consumer_activity",
                },
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

    # Always return 200 for readiness probe, but indicate health status
    return HealthCheck(
        status="healthy" if kafka_ready else "unhealthy",
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
            "trace_id": getattr(request.state, "trace_id", None),
            "services_encountered": getattr(request.state, "services_encountered", []),
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
