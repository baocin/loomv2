"""Main entry point for VAD Processor Service."""

import asyncio
import signal
import sys

import structlog
from prometheus_client import start_http_server

from .config import settings
from .processor import VADProcessor

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


class VADService:
    """Main VAD service class."""

    def __init__(self):
        self.processor = VADProcessor()
        self._shutdown_event = asyncio.Event()

    async def start(self):
        """Start the VAD service."""
        logger.info(
            "Starting VAD service",
            service_name=settings.service_name,
            version=settings.service_version,
        )

        # Start Prometheus metrics server
        if settings.enable_metrics:
            start_http_server(settings.metrics_port)
            logger.info(f"Metrics server started on port {settings.metrics_port}")

        # Start processor
        await self.processor.start()

        # Run message processing
        try:
            await self.processor.process_messages()
        except Exception as e:
            logger.error("Error in message processing", error=str(e))
            raise

    async def stop(self):
        """Stop the VAD service."""
        logger.info("Stopping VAD service...")
        await self.processor.stop()
        self._shutdown_event.set()

    def handle_signal(self, sig, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {sig}")
        asyncio.create_task(self.stop())


async def main():
    """Main entry point."""
    service = VADService()

    # Set up signal handlers
    signal.signal(signal.SIGINT, service.handle_signal)
    signal.signal(signal.SIGTERM, service.handle_signal)

    try:
        await service.start()
        await service._shutdown_event.wait()
    except Exception as e:
        logger.error("Fatal error", error=str(e))
        sys.exit(1)

    logger.info("VAD service shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
