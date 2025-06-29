"""Schema Registry Service - Centralized JSON Schema management."""

import time
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException, status
from prometheus_client import Counter, Histogram, generate_latest

from .models import SchemaInfo, SchemaValidationRequest, SchemaValidationResponse
from .services.schema_manager import SchemaManager
from .services.cache_service import CacheService

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
validation_requests = Counter(
    "schema_validations_total",
    "Total schema validation requests",
    ["schema_name", "valid"],
)
validation_duration = Histogram(
    "schema_validation_duration_seconds", "Time spent validating schemas"
)
cache_hits = Counter("schema_cache_hits_total", "Total cache hits")
cache_misses = Counter("schema_cache_misses_total", "Total cache misses")

# Global services
schema_manager: SchemaManager = None
cache_service: CacheService = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global schema_manager, cache_service

    logger.info("Starting Schema Registry service")

    # Initialize services
    cache_service = CacheService()
    await cache_service.initialize()

    schema_manager = SchemaManager(cache_service)
    await schema_manager.initialize()

    logger.info("Schema Registry service started")
    yield

    # Cleanup
    logger.info("Shutting down Schema Registry service")
    if cache_service:
        await cache_service.close()


app = FastAPI(
    title="Loom Schema Registry",
    description="Centralized JSON Schema validation and management service",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": time.time()}


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    try:
        # Check cache connectivity
        await cache_service.ping()
        return {"status": "ready", "timestamp": time.time()}
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Service not ready"
        )


@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint."""
    from fastapi.responses import Response

    return Response(
        content=generate_latest(), media_type="text/plain; version=0.0.4; charset=utf-8"
    )


@app.post("/validate", response_model=SchemaValidationResponse)
async def validate_data(request: SchemaValidationRequest):
    """Validate data against a schema."""
    start_time = time.time()

    try:
        with validation_duration.time():
            is_valid, errors = await schema_manager.validate(
                request.schema_name, request.data
            )

        validation_requests.labels(
            schema_name=request.schema_name, valid=str(is_valid)
        ).inc()

        logger.info(
            "Schema validation completed",
            schema_name=request.schema_name,
            valid=is_valid,
            duration=time.time() - start_time,
        )

        return SchemaValidationResponse(
            valid=is_valid, errors=errors, schema_name=request.schema_name
        )

    except Exception as e:
        logger.error(
            "Schema validation failed", schema_name=request.schema_name, error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation failed: {str(e)}",
        )


@app.get("/schemas")
async def list_schemas():
    """List all available schemas."""
    try:
        schemas = await schema_manager.list_schemas()
        return {"schemas": schemas}
    except Exception as e:
        logger.error("Failed to list schemas", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list schemas",
        )


@app.get("/schemas/{schema_name}", response_model=SchemaInfo)
async def get_schema(schema_name: str):
    """Get schema by name."""
    try:
        schema_info = await schema_manager.get_schema_info(schema_name)
        if not schema_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schema '{schema_name}' not found",
            )
        return schema_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get schema", schema_name=schema_name, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get schema",
        )


@app.get("/schemas/{schema_name}/versions")
async def get_schema_versions(schema_name: str):
    """Get all versions of a schema."""
    try:
        versions = await schema_manager.get_schema_versions(schema_name)
        return {"schema_name": schema_name, "versions": versions}
    except Exception as e:
        logger.error(
            "Failed to get schema versions", schema_name=schema_name, error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get schema versions",
        )


@app.get("/stats")
async def get_stats():
    """Get service statistics."""
    try:
        stats = await schema_manager.get_stats()
        return stats
    except Exception as e:
        logger.error("Failed to get stats", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get statistics",
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8010,
        log_level="info",
        access_log=False,  # Use structured logging instead
    )
