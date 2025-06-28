"""Main FastAPI application for Moondream Station service."""

import asyncio
import base64
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Optional

import structlog
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest
from starlette.responses import Response

from .config import settings
from .kafka_consumer import KafkaConsumerManager
from .models import (
    HealthStatus,
    ImageAnalysisRequest,
    MoondreamAnalysisResult,
    ProcessingMetrics,
)
from .moondream_client import MoondreamClient

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
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Prometheus metrics
REQUEST_COUNT = Counter(
    'moondream_requests_total',
    'Total number of requests processed',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'moondream_request_duration_seconds',
    'Request duration in seconds',
    ['method', 'endpoint']
)

PROCESSING_TIME = Histogram(
    'moondream_processing_time_seconds',
    'Processing time for image analysis',
    ['analysis_type']
)

# Global state
moondream_client: Optional[MoondreamClient] = None
kafka_consumer: Optional[KafkaConsumerManager] = None
processing_metrics = ProcessingMetrics()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    global moondream_client, kafka_consumer
    
    logger.info("Starting Moondream Station service", version="0.1.0")
    
    # Initialize Moondream client
    moondream_client = MoondreamClient()
    
    # Wait for Moondream Station to be ready
    max_retries = 30
    for attempt in range(max_retries):
        if await moondream_client.health_check():
            logger.info("Moondream Station is ready")
            break
        logger.info(f"Waiting for Moondream Station... attempt {attempt + 1}/{max_retries}")
        await asyncio.sleep(2)
    else:
        logger.error("Moondream Station not ready after maximum retries")
        raise RuntimeError("Moondream Station unavailable")
    
    # Initialize Kafka consumer
    kafka_consumer = KafkaConsumerManager(moondream_client)
    
    # Start background Kafka consumption
    kafka_task = asyncio.create_task(kafka_consumer.start_consuming())
    
    logger.info("Service startup completed")
    
    yield
    
    # Cleanup
    logger.info("Shutting down Moondream Station service")
    if kafka_consumer:
        await kafka_consumer.stop()
    kafka_task.cancel()
    logger.info("Service shutdown completed")


# Create FastAPI app
app = FastAPI(
    title="Moondream Station Service",
    description="Vision AI service using Moondream Station for Loom v2",
    version="0.1.0",
    lifespan=lifespan
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
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    REQUEST_DURATION.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)
    
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
    
    # Check Moondream Station
    if moondream_client:
        checks["moondream_station"] = await moondream_client.health_check()
        if not checks["moondream_station"]:
            overall_status = "unhealthy"
    else:
        checks["moondream_station"] = False
        overall_status = "unhealthy"
    
    # Check Kafka
    if kafka_consumer:
        checks["kafka"] = kafka_consumer.is_healthy()
        if not checks["kafka"]:
            overall_status = "unhealthy"
    else:
        checks["kafka"] = False
        overall_status = "unhealthy"
    
    status_code = 200 if overall_status == "healthy" else 503
    
    return Response(
        content=HealthStatus(
            status=overall_status,
            checks=checks
        ).model_dump_json(),
        status_code=status_code,
        media_type="application/json"
    )


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type="text/plain"
    )


@app.get("/status")
async def service_status():
    """Service status and metrics."""
    if not moondream_client:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    return {
        "service": "moondream-station",
        "version": "0.1.0",
        "status": "running",
        "moondream_endpoint": settings.moondream_host,
        "processing_metrics": processing_metrics.model_dump(),
        "kafka_topics": settings.kafka_input_topics,
        "output_topic": settings.kafka_output_topic,
    }


@app.post("/analyze/image")
async def analyze_image(request: ImageAnalysisRequest):
    """Analyze an image using Moondream Station."""
    if not moondream_client:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    start_time = time.time()
    
    try:
        with PROCESSING_TIME.labels(analysis_type="full_analysis").time():
            result = await moondream_client.full_analysis(
                image_data=request.image_data,
                query=request.query,
                enable_objects=request.enable_object_detection or settings.enable_object_detection,
                enable_ocr=request.enable_ocr or settings.enable_ocr,
            )
        
        processing_time = (time.time() - start_time) * 1000
        
        # Update metrics
        processing_metrics.images_processed += 1
        processing_metrics.total_processing_time += processing_time
        processing_metrics.average_processing_time = (
            processing_metrics.total_processing_time / processing_metrics.images_processed
        )
        processing_metrics.last_processed = datetime.utcnow()
        
        if result.caption:
            processing_metrics.caption_count += 1
        if result.query_response:
            processing_metrics.query_count += 1
        if result.objects:
            processing_metrics.objects_detected_total += len(result.objects)
        if result.text_blocks:
            processing_metrics.ocr_blocks_total += len(result.text_blocks)
        
        return {
            "result": result.model_dump(),
            "processing_time_ms": processing_time,
            "model": "moondream-station"
        }
        
    except Exception as e:
        processing_metrics.errors_count += 1
        logger.error("Image analysis failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/caption")
async def caption_image(
    image: UploadFile = File(..., description="Image file to caption")
):
    """Generate caption for an uploaded image."""
    if not moondream_client:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    start_time = time.time()
    
    try:
        # Read image data
        image_data = await image.read()
        image_base64 = base64.b64encode(image_data).decode()
        
        with PROCESSING_TIME.labels(analysis_type="caption").time():
            caption = await moondream_client.caption_image(image_base64)
        
        processing_time = (time.time() - start_time) * 1000
        
        # Update metrics
        processing_metrics.images_processed += 1
        processing_metrics.caption_count += 1
        processing_metrics.last_processed = datetime.utcnow()
        
        return {
            "caption": caption,
            "processing_time_ms": processing_time,
            "filename": image.filename
        }
        
    except Exception as e:
        processing_metrics.errors_count += 1
        logger.error("Caption generation failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Caption failed: {str(e)}")


@app.post("/query")
async def query_image(
    image: UploadFile = File(..., description="Image file to query"),
    query: str = Form(..., description="Question about the image")
):
    """Query an uploaded image with a specific question."""
    if not moondream_client:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    start_time = time.time()
    
    try:
        # Read image data
        image_data = await image.read()
        image_base64 = base64.b64encode(image_data).decode()
        
        with PROCESSING_TIME.labels(analysis_type="query").time():
            response = await moondream_client.query_image(image_base64, query)
        
        processing_time = (time.time() - start_time) * 1000
        
        # Update metrics
        processing_metrics.images_processed += 1
        processing_metrics.query_count += 1
        processing_metrics.last_processed = datetime.utcnow()
        
        return {
            "query": query,
            "response": response,
            "processing_time_ms": processing_time,
            "filename": image.filename
        }
        
    except Exception as e:
        processing_metrics.errors_count += 1
        logger.error("Query processing failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=settings.environment == "development"
    )