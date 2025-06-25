"""Mock VAD Processor Service for testing deployment."""

import asyncio
from datetime import datetime
from prometheus_client import Counter, start_http_server
import structlog

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Metrics
processed_chunks = Counter("vad_mock_processed_total", "Mock VAD chunks processed")


class MockVADProcessor:
    """Mock VAD processor that simulates processing without heavy dependencies."""

    def __init__(self):
        self._running = False

    async def start(self):
        """Start the mock processor."""
        logger.info("Starting Mock VAD processor...")
        self._running = True

        # Start metrics server
        start_http_server(8001)
        logger.info("Metrics server started on port 8001")

    async def run(self):
        """Main processing loop - just log and increment metrics."""
        while self._running:
            try:
                # Simulate processing
                processed_chunks.inc()
                logger.info(
                    "Mock VAD processing", timestamp=datetime.utcnow().isoformat()
                )
                await asyncio.sleep(10)  # Process every 10 seconds

            except Exception as e:
                logger.error("Error in mock processing", error=str(e))
                await asyncio.sleep(5)

    async def stop(self):
        """Stop the processor."""
        logger.info("Stopping Mock VAD processor...")
        self._running = False


async def main():
    """Main entry point."""
    processor = MockVADProcessor()

    try:
        await processor.start()
        await processor.run()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        await processor.stop()


if __name__ == "__main__":
    asyncio.run(main())
