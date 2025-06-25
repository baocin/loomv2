"""Main entry point for the Loom macOS client."""

import asyncio
import signal
import sys
from typing import Any

import structlog

from app.api.client import LoomAPIClient
from app.api.server import create_server
from app.collectors.apps import AppsCollector

# Import collectors
from app.collectors.audio import AudioCollector
from app.collectors.clipboard import ClipboardCollector
from app.collectors.location import LocationCollector
from app.collectors.screen import ScreenCollector
from app.collectors.system import SystemCollector
from app.config import config
from app.utils.logging import setup_logging
from app.utils.permissions import check_permissions
from app.utils.scheduler import CollectorScheduler

logger = structlog.get_logger(__name__)


class LoomMacOSClient:
    """Main Loom macOS client application."""

    def __init__(self):
        self.scheduler = CollectorScheduler()
        self.api_client = LoomAPIClient(config.api_base_url, config.device_id)
        self.server = None
        self.collectors: dict[str, Any] = {}
        self._running = False

    async def initialize(self) -> None:
        """Initialize the client and all collectors."""
        logger.info("Initializing Loom macOS client", device_id=config.device_id)

        # Check system permissions
        await check_permissions(config)

        # Initialize API client
        await self.api_client.initialize()

        # Initialize collectors based on configuration
        if config.audio_enabled:
            self.collectors["audio"] = AudioCollector(
                self.api_client,
                config.audio_interval,
                config.audio_sample_rate,
                config.audio_channels,
                config.audio_format,
            )

        if config.screen_enabled:
            self.collectors["screen"] = ScreenCollector(
                self.api_client,
                config.screen_interval,
                config.screen_quality,
                config.screen_max_width,
                config.screen_max_height,
            )

        if config.system_enabled:
            self.collectors["system"] = SystemCollector(
                self.api_client, config.system_interval
            )

        if config.location_enabled:
            self.collectors["location"] = LocationCollector(
                self.api_client, config.location_interval
            )

        if config.clipboard_enabled:
            self.collectors["clipboard"] = ClipboardCollector(
                self.api_client, config.clipboard_interval
            )

        if config.apps_enabled:
            self.collectors["apps"] = AppsCollector(
                self.api_client, config.apps_interval
            )

        # Initialize all collectors
        for name, collector in self.collectors.items():
            try:
                await collector.initialize()
                logger.info("Initialized collector", collector=name)
            except Exception as e:
                logger.error(
                    "Failed to initialize collector", collector=name, error=str(e)
                )
                # Continue with other collectors

        # Create local API server
        self.server = create_server(self, config)

        logger.info(
            "Client initialization complete", collectors=list(self.collectors.keys())
        )

    async def start(self) -> None:
        """Start all data collection."""
        if self._running:
            logger.warning("Client already running")
            return

        logger.info("Starting Loom macOS client")
        self._running = True

        # Start all collectors
        for name, collector in self.collectors.items():
            try:
                self.scheduler.add_collector(name, collector)
                logger.info("Started collector", collector=name)
            except Exception as e:
                logger.error("Failed to start collector", collector=name, error=str(e))

        # Start the scheduler
        await self.scheduler.start()

        # Start local API server in background
        if self.server:
            asyncio.create_task(self.server.serve())
            logger.info(
                "Local API server started",
                host=config.server_host,
                port=config.server_port,
            )

        logger.info("Data collection started")

    async def stop(self) -> None:
        """Stop all data collection."""
        if not self._running:
            return

        logger.info("Stopping Loom macOS client")
        self._running = False

        # Stop the scheduler
        await self.scheduler.stop()

        # Cleanup collectors
        for name, collector in self.collectors.items():
            try:
                await collector.cleanup()
                logger.info("Stopped collector", collector=name)
            except Exception as e:
                logger.error("Error stopping collector", collector=name, error=str(e))

        # Cleanup API client
        await self.api_client.cleanup()

        logger.info("Client stopped")

    async def get_status(self) -> dict[str, Any]:
        """Get current client status."""
        collector_status = {}
        for name, collector in self.collectors.items():
            try:
                collector_status[name] = await collector.get_status()
            except Exception as e:
                collector_status[name] = {"status": "error", "error": str(e)}

        return {
            "running": self._running,
            "device_id": config.device_id,
            "api_url": config.api_base_url,
            "collectors": collector_status,
            "scheduler": await self.scheduler.get_status(),
            "api_client": await self.api_client.get_status(),
        }

    @property
    def is_running(self) -> bool:
        """Check if client is running."""
        return self._running


async def signal_handler(client: LoomMacOSClient, signum: int) -> None:
    """Handle shutdown signals."""
    logger.info("Received shutdown signal", signal=signum)
    await client.stop()
    sys.exit(0)


async def main() -> None:
    """Main application entry point."""
    # Setup logging
    setup_logging(config.log_level)

    logger.info("Starting Loom macOS Client", version="0.1.0")

    # Create client
    client = LoomMacOSClient()

    # Setup signal handlers
    loop = asyncio.get_event_loop()
    for sig in [signal.SIGTERM, signal.SIGINT]:
        loop.add_signal_handler(
            sig, lambda s=sig: asyncio.create_task(signal_handler(client, s))
        )

    try:
        # Initialize and start client
        await client.initialize()
        await client.start()

        # Keep running
        while client.is_running:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error("Unexpected error", error=str(e))
        raise
    finally:
        await client.stop()


if __name__ == "__main__":
    asyncio.run(main())
