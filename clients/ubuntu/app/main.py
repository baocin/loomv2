"""Main pino-proxy application for Ubuntu/Linux."""

import asyncio
import signal
import sys
from typing import Any

import structlog

from app.api_client import LoomAPIClient
from app.collectors.apps import AppsCollector
from app.collectors.audio import AudioCollector
from app.collectors.clipboard import ClipboardCollector
from app.collectors.location import LocationCollector
from app.collectors.screen import ScreenCollector
from app.collectors.system import SystemCollector
from app.config import Config
from app.utils.device_id import DeviceIDManager

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

logger = structlog.get_logger(__name__)


class PinoProxyUbuntu:
    """Main pino-proxy application for Ubuntu/Linux."""

    def __init__(self):
        """Initialize the pino-proxy application."""
        self.config = Config()
        self.device_id_manager = DeviceIDManager()
        self.device_id = self.device_id_manager.get_device_id()
        self.api_client = LoomAPIClient(self.config.api_base_url, self.device_id)

        # Initialize collectors
        self.collectors: dict[str, Any] = {}
        self._running = False
        self._tasks = []

        logger.info(
            "Pino-proxy Ubuntu initialized",
            device_id=self.device_id,
            api_url=self.config.api_base_url,
        )

    async def initialize_collectors(self) -> None:
        """Initialize all data collectors."""
        try:
            # System metrics collector
            self.collectors["system"] = SystemCollector(
                self.api_client,
                self.config.system_poll_interval,
                self.config.system_send_interval,
            )

            # Audio collector
            self.collectors["audio"] = AudioCollector(
                self.api_client,
                self.config.audio_poll_interval,
                self.config.audio_send_interval,
                sample_rate=self.config.audio_sample_rate,
                channels=self.config.audio_channels,
            )

            # Screen capture collector
            self.collectors["screen"] = ScreenCollector(
                self.api_client,
                self.config.screen_poll_interval,
                self.config.screen_send_interval,
                quality=self.config.screen_quality,
                max_width=self.config.screen_max_width,
                max_height=self.config.screen_max_height,
            )

            # Apps monitoring collector
            self.collectors["apps"] = AppsCollector(
                self.api_client,
                self.config.apps_poll_interval,
                self.config.apps_send_interval,
            )

            # Location collector
            self.collectors["location"] = LocationCollector(
                self.api_client,
                self.config.location_poll_interval,
                self.config.location_send_interval,
            )

            # Clipboard collector
            self.collectors["clipboard"] = ClipboardCollector(
                self.api_client,
                self.config.clipboard_poll_interval,
                self.config.clipboard_send_interval,
                max_content_length=self.config.clipboard_max_length,
            )

            # Initialize each collector
            for name, collector in self.collectors.items():
                try:
                    await collector.initialize()
                    logger.info(f"Initialized {name} collector")
                except Exception as e:
                    logger.error(f"Failed to initialize {name} collector", error=str(e))
                    # Continue with other collectors

            logger.info(
                "All collectors initialized",
                active_collectors=list(self.collectors.keys()),
            )

        except Exception as e:
            logger.error("Error initializing collectors", error=str(e))
            raise

    async def start_collectors(self) -> None:
        """Start all initialized collectors."""
        self._running = True

        for name, collector in self.collectors.items():
            if collector._initialized:
                try:
                    task = asyncio.create_task(
                        collector.start_duty_cycle(), name=f"collector_{name}"
                    )
                    self._tasks.append(task)
                    logger.info(f"Started {name} collector")
                except Exception as e:
                    logger.error(f"Failed to start {name} collector", error=str(e))

        logger.info("All collectors started", active_tasks=len(self._tasks))

    async def stop_collectors(self) -> None:
        """Stop all running collectors."""
        logger.info("Stopping collectors...")
        self._running = False

        # Stop all collector tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()

        # Wait for tasks to complete with timeout
        if self._tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._tasks, return_exceptions=True), timeout=10.0
                )
            except TimeoutError:
                logger.warning("Some collector tasks did not stop within timeout")

        # Cleanup collectors
        for name, collector in self.collectors.items():
            try:
                await collector.stop_duty_cycle()
                await collector.cleanup()
                logger.info(f"Cleaned up {name} collector")
            except Exception as e:
                logger.error(f"Error cleaning up {name} collector", error=str(e))

        self._tasks.clear()
        logger.info("All collectors stopped")

    async def get_status(self) -> dict[str, Any]:
        """Get overall application status."""
        status = {
            "device_id": self.device_id,
            "running": self._running,
            "api_url": self.config.api_base_url,
            "collectors": {},
        }

        for name, collector in self.collectors.items():
            try:
                collector_status = await collector.get_status()
                status["collectors"][name] = collector_status
            except Exception as e:
                status["collectors"][name] = {"error": str(e)}

        return status

    async def run(self) -> None:
        """Run the main application loop."""
        try:
            logger.info("Starting pino-proxy Ubuntu...")

            # Initialize collectors
            await self.initialize_collectors()

            # Start collectors
            await self.start_collectors()

            # Run indefinitely
            logger.info("Pino-proxy Ubuntu running. Press Ctrl+C to stop.")

            # Wait for termination signal
            stop_event = asyncio.Event()

            def signal_handler():
                logger.info("Received termination signal")
                stop_event.set()

            # Register signal handlers
            if sys.platform != "win32":
                loop = asyncio.get_running_loop()
                for sig in (signal.SIGTERM, signal.SIGINT):
                    loop.add_signal_handler(sig, signal_handler)

            # Wait for stop signal
            await stop_event.wait()

        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.error("Error in main application", error=str(e))
            raise
        finally:
            # Always cleanup
            await self.stop_collectors()
            logger.info("Pino-proxy Ubuntu stopped")


async def main():
    """Main entry point."""
    try:
        app = PinoProxyUbuntu()
        await app.run()
    except Exception as e:
        logger.error("Fatal error in main", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
