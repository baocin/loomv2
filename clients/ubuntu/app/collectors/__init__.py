"""Data collection modules with duty cycle support for Ubuntu."""

import asyncio
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class BaseCollector(ABC):
    """Base class for all data collectors with duty cycle support."""

    def __init__(self, api_client, poll_interval: float, send_interval: float):
        """Initialize collector with polling and sending intervals.

        Args:
            api_client: API client for sending data
            poll_interval: How often to poll/collect data (seconds)
            send_interval: How often to send batched data (seconds)
        """
        self.api_client = api_client
        self.poll_interval = poll_interval
        self.send_interval = send_interval

        # Validation
        if send_interval < poll_interval:
            raise ValueError("Send interval must be >= poll interval")

        # State tracking
        self._initialized = False
        self._last_collection = None
        self._last_send = None
        self._collection_count = 0
        self._send_count = 0
        self._error_count = 0

        # Data buffering for duty cycle
        self._data_buffer: list[dict[str, Any]] = []
        self._buffer_lock = asyncio.Lock()
        self._running = False

        # Calculate how many polls per send
        self._polls_per_send = max(1, int(send_interval / poll_interval))

        logger.info(
            "Collector initialized with duty cycle",
            collector=self.__class__.__name__,
            poll_interval=poll_interval,
            send_interval=send_interval,
            polls_per_send=self._polls_per_send,
        )

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the collector."""
        pass

    @abstractmethod
    async def poll_data(self) -> dict[str, Any] | None:
        """Poll/collect a single data point. Return None if no data available."""
        pass

    @abstractmethod
    async def send_data_batch(self, data_batch: list[dict[str, Any]]) -> bool:
        """Send a batch of collected data points. Return True if successful."""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup resources."""
        pass

    async def start_duty_cycle(self) -> None:
        """Start the duty cycle collection and sending."""
        if self._running:
            logger.warning(
                "Collector already running", collector=self.__class__.__name__
            )
            return

        if not self._initialized:
            logger.error("Collector not initialized", collector=self.__class__.__name__)
            return

        self._running = True
        logger.info("Starting duty cycle", collector=self.__class__.__name__)

        # Start polling and sending tasks
        poll_task = asyncio.create_task(self._poll_loop())
        send_task = asyncio.create_task(self._send_loop())

        try:
            await asyncio.gather(poll_task, send_task)
        except asyncio.CancelledError:
            logger.info("Duty cycle cancelled", collector=self.__class__.__name__)
        finally:
            self._running = False

    async def stop_duty_cycle(self) -> None:
        """Stop the duty cycle."""
        self._running = False

        # Send any remaining buffered data
        await self._flush_buffer()

        logger.info("Stopped duty cycle", collector=self.__class__.__name__)

    async def _poll_loop(self) -> None:
        """Main polling loop."""
        logger.info("Starting poll loop", collector=self.__class__.__name__)

        while self._running:
            try:
                # Poll for data
                data = await self.poll_data()

                if data is not None:
                    # Add timestamp and metadata
                    data["recorded_at"] = datetime.now(UTC).isoformat()
                    data["poll_sequence"] = self._collection_count

                    # Add to buffer
                    async with self._buffer_lock:
                        self._data_buffer.append(data)

                    self._collection_count += 1
                    self._last_collection = data["recorded_at"]

                    logger.debug(
                        "Data polled and buffered",
                        collector=self.__class__.__name__,
                        buffer_size=len(self._data_buffer),
                    )

                # Wait for next poll
                await asyncio.sleep(self.poll_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self._error_count += 1
                logger.error(
                    "Error in poll loop",
                    collector=self.__class__.__name__,
                    error=str(e),
                )
                # Brief pause before retrying
                await asyncio.sleep(min(self.poll_interval, 5.0))

    async def _send_loop(self) -> None:
        """Main sending loop."""
        logger.info("Starting send loop", collector=self.__class__.__name__)

        while self._running:
            try:
                # Wait for send interval
                await asyncio.sleep(self.send_interval)

                # Send buffered data
                await self._send_buffered_data()

            except asyncio.CancelledError:
                break
            except Exception as e:
                self._error_count += 1
                logger.error(
                    "Error in send loop",
                    collector=self.__class__.__name__,
                    error=str(e),
                )

    async def _send_buffered_data(self) -> None:
        """Send all buffered data."""
        async with self._buffer_lock:
            if not self._data_buffer:
                logger.debug("No data to send", collector=self.__class__.__name__)
                return

            # Copy and clear buffer
            data_to_send = self._data_buffer.copy()
            self._data_buffer.clear()

        if data_to_send:
            try:
                success = await self.send_data_batch(data_to_send)

                if success:
                    self._send_count += 1
                    self._last_send = datetime.now(UTC).isoformat()
                    logger.info(
                        "Data batch sent successfully",
                        collector=self.__class__.__name__,
                        batch_size=len(data_to_send),
                    )
                else:
                    self._error_count += 1
                    logger.error(
                        "Failed to send data batch",
                        collector=self.__class__.__name__,
                        batch_size=len(data_to_send),
                    )

                    # Re-add failed data to buffer for retry
                    async with self._buffer_lock:
                        self._data_buffer.extend(data_to_send)

            except Exception as e:
                self._error_count += 1
                logger.error(
                    "Error sending data batch",
                    collector=self.__class__.__name__,
                    error=str(e),
                )

                # Re-add failed data to buffer for retry
                async with self._buffer_lock:
                    self._data_buffer.extend(data_to_send)

    async def _flush_buffer(self) -> None:
        """Flush any remaining buffered data."""
        if self._data_buffer:
            logger.info(
                "Flushing remaining buffered data",
                collector=self.__class__.__name__,
                remaining_items=len(self._data_buffer),
            )
            await self._send_buffered_data()

    async def get_status(self) -> dict[str, Any]:
        """Get collector status."""
        async with self._buffer_lock:
            buffer_size = len(self._data_buffer)

        return {
            "initialized": self._initialized,
            "running": self._running,
            "last_collection": self._last_collection,
            "last_send": self._last_send,
            "collection_count": self._collection_count,
            "send_count": self._send_count,
            "error_count": self._error_count,
            "poll_interval": self.poll_interval,
            "send_interval": self.send_interval,
            "polls_per_send": self._polls_per_send,
            "buffer_size": buffer_size,
        }

    @property
    def is_running(self) -> bool:
        """Check if collector is running."""
        return self._running
