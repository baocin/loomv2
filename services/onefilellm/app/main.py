"""Main application for OneFileLLM service."""

import asyncio
import signal
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .config import settings
from .database import DatabaseManager
from .document_processor import DocumentProcessor
from .github_processor import GitHubProcessor
from .kafka_consumer import KafkaConsumerManager
from .kafka_producer import KafkaProducerManager
from .models import HealthCheck

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

# Global managers
kafka_consumer: KafkaConsumerManager
kafka_producer: KafkaProducerManager
database: DatabaseManager
github_processor: GitHubProcessor
document_processor: DocumentProcessor


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup and shutdown."""
    global \
        kafka_consumer, \
        kafka_producer, \
        database, \
        github_processor, \
        document_processor

    # Startup
    logger.info("Starting OneFileLLM service", version="0.1.0")

    try:
        # Initialize database manager
        database = DatabaseManager()
        await database.start()
        logger.info("Database manager started")

        # Initialize Kafka producer
        kafka_producer = KafkaProducerManager()
        await kafka_producer.start()
        logger.info("Kafka producer started")

        # Initialize processors
        github_processor = GitHubProcessor(kafka_producer, database)
        document_processor = DocumentProcessor(kafka_producer, database)
        logger.info("Processors initialized")

        # Initialize and start Kafka consumer
        kafka_consumer = KafkaConsumerManager(github_processor, document_processor)
        await kafka_consumer.start()
        logger.info("Kafka consumer started")

        logger.info("OneFileLLM service started successfully")

    except Exception as e:
        logger.error("Failed to start OneFileLLM service", error=str(e))
        raise

    yield

    # Shutdown
    logger.info("Shutting down OneFileLLM service")

    try:
        if kafka_consumer:
            await kafka_consumer.stop()
            logger.info("Kafka consumer stopped")

        if kafka_producer:
            await kafka_producer.stop()
            logger.info("Kafka producer stopped")

        if database:
            await database.stop()
            logger.info("Database manager stopped")

    except Exception as e:
        logger.error("Error during shutdown", error=str(e))


# Create FastAPI application
app = FastAPI(
    title="OneFileLLM Service",
    description="GitHub and document processing service using OneFileLLM",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check() -> HealthCheck:
    """Health check endpoint."""
    try:
        kafka_connected = kafka_producer.is_connected if kafka_producer else False
        database_connected = database.is_connected if database else False

        # Check OneFileLLM availability
        onefilellm_available = True
        try:
            import onefilellm
        except ImportError:
            onefilellm_available = False

        return HealthCheck(
            status="healthy" if kafka_connected and database_connected else "unhealthy",
            kafka_connected=kafka_connected,
            database_connected=database_connected,
            onefilellm_available=onefilellm_available,
        )
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return HealthCheck(
            status="unhealthy",
            kafka_connected=False,
            database_connected=False,
            onefilellm_available=False,
        )


@app.get("/")
async def root() -> JSONResponse:
    """Root endpoint with service information."""
    return JSONResponse(
        content={
            "service": "onefilellm",
            "version": "0.1.0",
            "description": "GitHub and document processing service using OneFileLLM",
            "endpoints": {
                "health": "/health",
            },
            "topics": {
                "consumes": [
                    settings.topic_github_ingest,
                    settings.topic_document_ingest,
                ],
                "produces": [
                    settings.topic_github_parsed,
                    settings.topic_document_parsed,
                ],
            },
        }
    )


async def main():
    """Main application entry point."""

    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal", signal=signum)
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    import uvicorn

    # Run the FastAPI app
    config = uvicorn.Config(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        access_log=False,  # We handle logging ourselves
    )

    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
