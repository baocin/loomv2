"""Text embedder service for processing emails and social media content."""

import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.config import settings
from app.embedder import TextEmbedder
from app.kafka_consumer import TextEmbeddingConsumer

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

logger = structlog.get_logger()

# Global instances
embedder = TextEmbedder(model_name=settings.embedding_model, device=settings.device)
consumer = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global consumer
    
    # Startup
    logger.info("Starting text embedder service")
    
    # Create consumer
    consumer = TextEmbeddingConsumer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        email_topic=settings.kafka_email_topic,
        twitter_topic=settings.kafka_twitter_topic,
        embedded_email_topic=settings.kafka_embedded_email_topic,
        embedded_twitter_topic=settings.kafka_embedded_twitter_topic,
        consumer_group=settings.kafka_consumer_group,
        database_url=settings.database_url,
        embedder=embedder,
    )
    
    # Start consumer task
    consumer_task = asyncio.create_task(consumer.run())
    
    yield
    
    # Shutdown
    logger.info("Shutting down text embedder service")
    if consumer:
        consumer.running = False
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass


# Create FastAPI app
app = FastAPI(
    title="Text Embedder Service",
    description="Embeds emails and social media content for semantic search",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/healthz")
async def health_check():
    """Health check endpoint."""
    return JSONResponse(
        content={
            "status": "healthy",
            "service": "text-embedder",
            "model": settings.embedding_model,
            "device": settings.device,
        }
    )


@app.get("/readyz")
async def readiness_check():
    """Readiness check endpoint."""
    ready = consumer is not None and consumer.running
    
    return JSONResponse(
        content={
            "status": "ready" if ready else "not_ready",
            "consumer_running": ready,
        },
        status_code=200 if ready else 503,
    )


@app.post("/embed")
async def embed_text(text: str):
    """Embed a single text (for testing)."""
    try:
        embedding = embedder.embed_text(text)
        return JSONResponse(
            content={
                "text": text,
                "embedding_dim": len(embedding),
                "model": settings.embedding_model,
            }
        )
    except Exception as e:
        return JSONResponse(
            content={"error": str(e)},
            status_code=500,
        )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )