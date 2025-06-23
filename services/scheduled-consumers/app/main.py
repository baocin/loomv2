"""Main entry point for scheduled consumers service."""

import asyncio
import signal
import sys
from typing import Any
import structlog

from .scheduler import scheduler
from .config import settings

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


class ScheduledConsumersService:
    """Main service class for scheduled consumers."""
    
    def __init__(self):
        """Initialize the service."""
        self._shutdown_event = asyncio.Event()
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        def signal_handler(signum: int, frame: Any) -> None:
            logger.info(f"Received signal {signum}, initiating shutdown")
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def start(self) -> None:
        """Start the scheduled consumers service."""
        logger.info(
            "Starting Loom Scheduled Consumers Service",
            version="0.1.0",
            device_id=settings.device_id,
            kafka_servers=settings.kafka_bootstrap_servers,
        )
        
        try:
            # Start the scheduler
            await scheduler.start()
            
        except Exception as e:
            logger.error("Failed to start service", error=str(e), exc_info=True)
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the service gracefully."""
        logger.info("Shutting down scheduled consumers service")
        
        try:
            # Stop the scheduler
            await scheduler.stop()
            
            # Signal shutdown complete
            self._shutdown_event.set()
            
            logger.info("Service shutdown completed")
            
        except Exception as e:
            logger.error("Error during shutdown", error=str(e), exc_info=True)
    
    async def run(self) -> None:
        """Run the service until shutdown."""
        await self.start()
        await self._shutdown_event.wait()


async def main() -> None:
    """Main entry point."""
    service = ScheduledConsumersService()
    
    try:
        await service.run()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error("Service failed", error=str(e), exc_info=True)
        sys.exit(1)
    finally:
        await service.shutdown()


if __name__ == "__main__":
    asyncio.run(main())