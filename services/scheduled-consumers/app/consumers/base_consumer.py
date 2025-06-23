"""Base consumer class for scheduled data collection."""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List

import structlog

from ..config import settings
from ..kafka_producer import kafka_producer
from ..models import BaseMessage, ScheduledJobStatus

logger = structlog.get_logger(__name__)


class BaseConsumer(ABC):
    """Base class for all scheduled consumers."""

    def __init__(self, job_type: str, interval_minutes: int = 60):
        """Initialize the base consumer.

        Args:
        ----
            job_type: Type identifier for this consumer job
            interval_minutes: How often to run this consumer
        """
        self.job_type = job_type
        self.interval_minutes = interval_minutes
        self.job_id = f"{job_type}_{settings.device_id}"
        self._running = False
        self._last_run: datetime | None = None
        self._items_processed = 0

    @abstractmethod
    async def collect_data(self) -> List[BaseMessage]:
        """Collect data from the external source.

        Returns:
        -------
            List of messages to send to Kafka
        """
        pass

    @abstractmethod
    def get_kafka_topic(self) -> str:
        """Get the Kafka topic for this consumer's data.

        Returns:
        -------
            Kafka topic name
        """
        pass

    async def run_once(self) -> ScheduledJobStatus:
        """Execute the consumer once and return status.

        Returns:
        -------
            Job status with execution details
        """
        start_time = datetime.utcnow()
        status = "running"
        error_message = None
        items_processed = 0

        try:
            logger.info(
                "Starting scheduled consumer job",
                job_type=self.job_type,
                job_id=self.job_id,
            )

            # Collect data from external source
            messages = await self.collect_data()
            items_processed = len(messages)

            # Send messages to Kafka
            topic = self.get_kafka_topic()
            for message in messages:
                await kafka_producer.send_message(topic, message)

            status = "completed"
            self._items_processed += items_processed
            self._last_run = start_time

            logger.info(
                "Scheduled consumer job completed",
                job_type=self.job_type,
                job_id=self.job_id,
                items_processed=items_processed,
                duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
            )

        except Exception as e:
            status = "failed"
            error_message = str(e)
            logger.error(
                "Scheduled consumer job failed",
                job_type=self.job_type,
                job_id=self.job_id,
                error=error_message,
                exc_info=True,
            )

        # Create job status
        duration = (datetime.utcnow() - start_time).total_seconds()

        return ScheduledJobStatus(
            device_id=settings.device_id,
            job_id=self.job_id,
            job_type=self.job_type,
            last_run=start_time,
            next_run=self._calculate_next_run(start_time),
            status=status,
            error_message=error_message,
            items_processed=items_processed,
            execution_duration=duration,
        )

    async def start_scheduled(self) -> None:
        """Start the consumer on a schedule."""
        self._running = True

        logger.info(
            "Starting scheduled consumer",
            job_type=self.job_type,
            interval_minutes=self.interval_minutes,
        )

        while self._running:
            try:
                # Run the consumer
                job_status = await self.run_once()

                # Send job status to monitoring topic
                await self._send_job_status(job_status)

                # Wait for next interval
                await asyncio.sleep(self.interval_minutes * 60)

            except Exception as e:
                logger.error(
                    "Error in scheduled consumer loop",
                    job_type=self.job_type,
                    error=str(e),
                    exc_info=True,
                )
                # Wait a bit before retrying to avoid tight error loops
                await asyncio.sleep(60)

    def stop(self) -> None:
        """Stop the scheduled consumer."""
        self._running = False
        logger.info("Stopping scheduled consumer", job_type=self.job_type)

    def _calculate_next_run(self, last_run: datetime) -> datetime:
        """Calculate next run time based on interval."""
        import datetime as dt

        return last_run + dt.timedelta(minutes=self.interval_minutes)

    async def _send_job_status(self, status: ScheduledJobStatus) -> None:
        """Send job status to monitoring topic."""
        try:
            await kafka_producer.send_message(
                "internal.scheduled.jobs.status",
                status,
                key=self.job_id,
            )
        except Exception as e:
            logger.error(
                "Failed to send job status",
                job_id=self.job_id,
                error=str(e),
            )

    @property
    def is_running(self) -> bool:
        """Check if consumer is currently running."""
        return self._running

    @property
    def last_run(self) -> datetime | None:
        """Get last run timestamp."""
        return self._last_run

    @property
    def total_items_processed(self) -> int:
        """Get total items processed since start."""
        return self._items_processed
