"""Main FastAPI application for Nomic Embed Vision service."""

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Dict, Any

import structlog
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from .config import settings
from .embedding_processor import NomicEmbeddingProcessor
from .kafka_consumer import EmbeddingKafkaConsumer
from .models import (
    EmbeddingRequest,
    EmbeddingResponse,
    BatchEmbeddingRequest,
    BatchEmbeddingResponse,
    HealthCheck,
    ProcessingStats,
)

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        getattr(structlog.stdlib, settings.log_level.upper(), 20)
    ),
    logger_factory=structlog.PrintLoggerFactory(),
    context_class=dict,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Global components
kafka_consumer: EmbeddingKafkaConsumer | None = None
api_processor: NomicEmbeddingProcessor | None = None
app_start_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global kafka_consumer, api_processor
    
    logger.info("Starting Nomic Embed Vision service")
    
    try:
        # Initialize API processor (separate from Kafka consumer processor)
        api_processor = NomicEmbeddingProcessor()
        await api_processor.initialize()
        
        # Start Kafka consumer
        kafka_consumer = EmbeddingKafkaConsumer()
        consumer_task = asyncio.create_task(kafka_consumer.start())
        
        logger.info("Service initialization completed")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to initialize service: {e}")
        raise
    finally:
        # Cleanup
        logger.info("Shutting down service")
        
        if kafka_consumer:
            await kafka_consumer.stop()
        
        if api_processor:
            await api_processor.cleanup()
        
        logger.info("Service shutdown completed")


# Create FastAPI app
app = FastAPI(
    title="Nomic Embed Vision Service",
    description="Text and image embedding service using Nomic Embed Vision v1.5",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/healthz", response_model=HealthCheck)
async def health_check() -> HealthCheck:
    """Health check endpoint."""
    model_loaded = api_processor is not None and api_processor.model_loaded
    consumer_running = kafka_consumer is not None and kafka_consumer.running
    
    queue_size = 0
    total_processed = 0
    
    if kafka_consumer:
        status = kafka_consumer.get_status()
        queue_size = status.get("queue_size", 0)
        total_processed = (
            status.get("total_text_processed", 0) + 
            status.get("total_images_processed", 0)
        )
    
    status = "healthy" if (model_loaded and consumer_running) else "degraded"
    
    return HealthCheck(
        status=status,
        model_loaded=model_loaded,
        model_name=settings.model_name,
        device=api_processor.device if api_processor else "unknown",
        total_processed=total_processed,
        queue_size=queue_size,
    )


@app.get("/stats", response_model=ProcessingStats)
async def get_stats() -> ProcessingStats:
    """Get processing statistics."""
    if not api_processor or not kafka_consumer:
        raise HTTPException(status_code=503, detail="Service not fully initialized")
    
    consumer_stats = kafka_consumer.get_status()
    processor_stats = api_processor.get_stats()
    
    uptime = time.time() - app_start_time
    
    return ProcessingStats(
        total_text_processed=consumer_stats.get("total_text_processed", 0),
        total_images_processed=consumer_stats.get("total_images_processed", 0),
        average_text_processing_time_ms=processor_stats.get("average_processing_time_ms", 0.0),
        average_image_processing_time_ms=processor_stats.get("average_processing_time_ms", 0.0),
        queue_size=consumer_stats.get("queue_size", 0),
        model_memory_usage_mb=processor_stats.get("model_memory_usage_mb", 0.0),
        uptime_seconds=uptime,
    )


@app.post("/embed", response_model=EmbeddingResponse)
async def create_embedding(request: EmbeddingRequest) -> EmbeddingResponse:
    """Create embeddings for text and/or image."""
    if not api_processor or not api_processor.model_loaded:
        raise HTTPException(status_code=503, detail="Embedding model not loaded")
    
    if not request.text and not request.image_data:
        raise HTTPException(status_code=400, detail="Either text or image_data must be provided")
    
    start_time = time.time()
    
    try:
        text_embedding = None
        image_embedding = None
        image_description = None
        
        # Generate text embedding
        if request.text:
            text_embedding = await api_processor._embed_text(request.text)
        
        # Generate image embedding
        if request.image_data:
            image_embedding, image_description = await api_processor._embed_image(
                request.image_data, request.include_description
            )
        
        processing_time = (time.time() - start_time) * 1000
        
        # Use the first available embedding dimension
        embedding_dimension = settings.embedding_dimension
        if text_embedding:
            embedding_dimension = len(text_embedding)
        elif image_embedding:
            embedding_dimension = len(image_embedding)
        
        return EmbeddingResponse(
            text_embedding=text_embedding,
            image_embedding=image_embedding,
            image_description=image_description,
            embedding_model=settings.model_name,
            embedding_dimension=embedding_dimension,
            processing_time_ms=processing_time,
        )
        
    except Exception as e:
        logger.error(f"Failed to create embedding: {e}")
        raise HTTPException(status_code=500, detail=f"Embedding generation failed: {str(e)}")


@app.post("/embed/batch", response_model=BatchEmbeddingResponse)
async def create_batch_embeddings(request: BatchEmbeddingRequest) -> BatchEmbeddingResponse:
    """Create embeddings for batch of texts and/or images."""
    if not api_processor or not api_processor.model_loaded:
        raise HTTPException(status_code=503, detail="Embedding model not loaded")
    
    if not request.texts and not request.images:
        raise HTTPException(status_code=400, detail="Either texts or images must be provided")
    
    start_time = time.time()
    
    try:
        text_embeddings = []
        image_embeddings = []
        image_descriptions = []
        
        # Generate text embeddings
        if request.texts:
            text_embeddings = await api_processor.embed_batch_text(request.texts)
        
        # Generate image embeddings
        if request.images:
            for image_data in request.images:
                image_embedding, description = await api_processor._embed_image(
                    image_data, request.include_descriptions
                )
                image_embeddings.append(image_embedding)
                image_descriptions.append(description)
        
        processing_time = (time.time() - start_time) * 1000
        total_processed = len(request.texts) + len(request.images)
        
        # Get embedding dimension
        embedding_dimension = settings.embedding_dimension
        if text_embeddings:
            embedding_dimension = len(text_embeddings[0])
        elif image_embeddings:
            embedding_dimension = len(image_embeddings[0])
        
        return BatchEmbeddingResponse(
            text_embeddings=text_embeddings,
            image_embeddings=image_embeddings,
            image_descriptions=image_descriptions,
            batch_id=request.batch_id,
            total_processed=total_processed,
            total_processing_time_ms=processing_time,
            embedding_model=settings.model_name,
            embedding_dimension=embedding_dimension,
        )
        
    except Exception as e:
        logger.error(f"Failed to create batch embeddings: {e}")
        raise HTTPException(status_code=500, detail=f"Batch embedding generation failed: {str(e)}")


@app.get("/model/info")
async def get_model_info() -> Dict[str, Any]:
    """Get information about the loaded model."""
    if not api_processor:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    return {
        "model_name": settings.model_name,
        "model_loaded": api_processor.model_loaded,
        "device": api_processor.device,
        "embedding_dimension": settings.embedding_dimension,
        "max_text_length": settings.max_text_length,
        "max_image_size": settings.max_image_size,
        "max_batch_size": settings.max_batch_size,
    }


@app.post("/model/reload")
async def reload_model(background_tasks: BackgroundTasks) -> Dict[str, str]:
    """Reload the embedding model."""
    if not api_processor:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    async def reload_task():
        try:
            logger.info("Reloading embedding model")
            await api_processor.cleanup()
            await api_processor.initialize()
            logger.info("Model reloaded successfully")
        except Exception as e:
            logger.error(f"Failed to reload model: {e}")
    
    background_tasks.add_task(reload_task)
    return {"status": "Model reload initiated"}


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", request_url=str(request.url))
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=settings.environment == "development",
    )