"""Privacy Filter Service - PII detection, redaction, and anonymization."""

import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List

import structlog
from fastapi import FastAPI, HTTPException, status
from prometheus_client import Counter, Histogram, generate_latest

from .models import (
    FilterRequest,
    FilterResponse,
    AnonymizeRequest,
    AnonymizeResponse,
    PIIDetectionRequest,
    PIIDetectionResponse,
)
from .services.privacy_engine import PrivacyEngine
from .services.audit_logger import AuditLogger

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
filter_requests = Counter(
    "privacy_filter_requests_total",
    "Total privacy filter requests",
    ["operation", "pii_detected"]
)
filter_duration = Histogram(
    "privacy_filter_duration_seconds",
    "Time spent processing privacy filters"
)
pii_entities_detected = Counter(
    "pii_entities_detected_total",
    "Total PII entities detected",
    ["entity_type"]
)

# Global services
privacy_engine: PrivacyEngine = None
audit_logger: AuditLogger = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global privacy_engine, audit_logger
    
    logger.info("Starting Privacy Filter service")
    
    # Initialize services
    privacy_engine = PrivacyEngine()
    await privacy_engine.initialize()
    
    audit_logger = AuditLogger()
    await audit_logger.initialize()
    
    logger.info("Privacy Filter service started")
    yield
    
    # Cleanup
    logger.info("Shutting down Privacy Filter service")


app = FastAPI(
    title="Loom Privacy Filter",
    description="PII detection, redaction, and anonymization service",
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
        # Check if privacy engine is ready
        is_ready = await privacy_engine.is_ready()
        if not is_ready:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Privacy engine not ready"
            )
        return {"status": "ready", "timestamp": time.time()}
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready"
        )


@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint."""
    from fastapi.responses import Response
    return Response(
        content=generate_latest(),
        media_type="text/plain; version=0.0.4; charset=utf-8"
    )


@app.post("/detect", response_model=PIIDetectionResponse)
async def detect_pii(request: PIIDetectionRequest):
    """Detect PII in text data."""
    start_time = time.time()
    
    try:
        with filter_duration.time():
            entities = await privacy_engine.detect_pii(
                request.text,
                request.entity_types,
                request.language
            )
        
        # Update metrics
        has_pii = len(entities) > 0
        filter_requests.labels(
            operation="detect",
            pii_detected=str(has_pii)
        ).inc()
        
        for entity in entities:
            pii_entities_detected.labels(entity_type=entity.entity_type).inc()
        
        # Log to audit trail
        await audit_logger.log_detection(
            request.text,
            entities,
            request.context
        )
        
        logger.info(
            "PII detection completed",
            entities_found=len(entities),
            duration=time.time() - start_time
        )
        
        return PIIDetectionResponse(
            entities=entities,
            has_pii=has_pii,
            processed_at=time.time()
        )
        
    except Exception as e:
        logger.error("PII detection failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Detection failed: {str(e)}"
        )


@app.post("/filter", response_model=FilterResponse)
async def filter_data(request: FilterRequest):
    """Filter PII from data."""
    start_time = time.time()
    
    try:
        with filter_duration.time():
            filtered_data, entities_found = await privacy_engine.filter_data(
                request.data,
                request.rules,
                request.replacement_strategy
            )
        
        # Update metrics
        has_pii = len(entities_found) > 0
        filter_requests.labels(
            operation="filter",
            pii_detected=str(has_pii)
        ).inc()
        
        for entity in entities_found:
            pii_entities_detected.labels(entity_type=entity.entity_type).inc()
        
        # Log to audit trail
        await audit_logger.log_filtering(
            request.data,
            filtered_data,
            entities_found,
            request.context
        )
        
        logger.info(
            "Data filtering completed",
            entities_filtered=len(entities_found),
            duration=time.time() - start_time
        )
        
        return FilterResponse(
            filtered_data=filtered_data,
            entities_found=entities_found,
            original_entities_count=len(entities_found),
            processed_at=time.time()
        )
        
    except Exception as e:
        logger.error("Data filtering failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Filtering failed: {str(e)}"
        )


@app.post("/anonymize", response_model=AnonymizeResponse)
async def anonymize_data(request: AnonymizeRequest):
    """Anonymize data with fake values."""
    start_time = time.time()
    
    try:
        with filter_duration.time():
            anonymized_data, anonymization_map = await privacy_engine.anonymize_data(
                request.data,
                request.entity_types,
                request.preserve_format,
                request.seed
            )
        
        # Update metrics
        filter_requests.labels(
            operation="anonymize",
            pii_detected=str(len(anonymization_map) > 0)
        ).inc()
        
        # Log to audit trail (without original data for privacy)
        await audit_logger.log_anonymization(
            len(str(request.data)),
            anonymization_map,
            request.context
        )
        
        logger.info(
            "Data anonymization completed",
            anonymizations=len(anonymization_map),
            duration=time.time() - start_time
        )
        
        return AnonymizeResponse(
            anonymized_data=anonymized_data,
            anonymization_map=anonymization_map if request.return_mapping else {},
            processed_at=time.time()
        )
        
    except Exception as e:
        logger.error("Data anonymization failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Anonymization failed: {str(e)}"
        )


@app.get("/stats")
async def get_stats():
    """Get service statistics."""
    try:
        stats = await privacy_engine.get_stats()
        return stats
    except Exception as e:
        logger.error("Failed to get stats", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get statistics"
        )


@app.get("/supported-entities")
async def get_supported_entities():
    """Get list of supported PII entity types."""
    try:
        entities = await privacy_engine.get_supported_entities()
        return {"supported_entities": entities}
    except Exception as e:
        logger.error("Failed to get supported entities", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get supported entities"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8011,
        log_level="info",
        access_log=False,
    )