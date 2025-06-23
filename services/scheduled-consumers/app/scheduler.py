"""Scheduler for managing multiple consumers."""

import asyncio
from typing import Dict, List

import structlog

from .consumers.base_consumer import BaseConsumer
from .consumers.email_consumer import EmailConsumer
from .consumers.hackernews_consumer import HackerNewsConsumer
from .consumers.twitter_consumer import TwitterConsumer
from .consumers.web_consumer import WebConsumer
from .kafka_producer import kafka_producer

logger = structlog.get_logger(__name__)


class ConsumerScheduler:
    """Manages and schedules multiple data consumers."""

    def __init__(self):
        """Initialize the scheduler."""
        self.consumers: Dict[str, BaseConsumer] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self._shutdown_event = asyncio.Event()

        # Initialize consumers
        self._setup_consumers()

    def _setup_consumers(self) -> None:
        """Set up all available consumers."""
        consumers = [
            EmailConsumer(),
            TwitterConsumer(),
            HackerNewsConsumer(),
            WebConsumer(),
        ]

        for consumer in consumers:
            self.consumers[consumer.job_type] = consumer
            logger.info(
                "Registered consumer",
                job_type=consumer.job_type,
                interval_minutes=consumer.interval_minutes,
            )

    async def start(self) -> None:
        """Start all consumers."""
        logger.info("Starting consumer scheduler")

        # Start Kafka producer
        await kafka_producer.start()

        # Start all consumers
        for job_type, consumer in self.consumers.items():
            try:
                task = asyncio.create_task(consumer.start_scheduled())
                self.running_tasks[job_type] = task
                logger.info(f"Started consumer: {job_type}")
            except Exception as e:
                logger.error(
                    "Failed to start consumer", job_type=job_type, error=str(e)
                )

        logger.info(f"Started {len(self.running_tasks)} consumers")

        # Wait for shutdown signal
        await self._shutdown_event.wait()

    async def stop(self) -> None:
        """Stop all consumers."""
        logger.info("Stopping consumer scheduler")

        # Stop all consumers
        for consumer in self.consumers.values():
            consumer.stop()

        # Cancel running tasks
        for job_type, task in self.running_tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    logger.info(f"Cancelled consumer task: {job_type}")

        # Stop Kafka producer
        await kafka_producer.stop()

        # Signal shutdown complete
        self._shutdown_event.set()

        logger.info("Consumer scheduler stopped")

    async def run_consumer_once(self, job_type: str) -> bool:
        """Run a specific consumer once.

        Args:
        ----
            job_type: Type of consumer to run

        Returns:
        -------
            True if successful, False otherwise
        """
        if job_type not in self.consumers:
            logger.error(f"Unknown consumer type: {job_type}")
            return False

        try:
            consumer = self.consumers[job_type]
            job_status = await consumer.run_once()

            logger.info(
                "Manual consumer execution completed",
                job_type=job_type,
                status=job_status.status,
                items_processed=job_status.items_processed,
                duration=job_status.execution_duration,
            )

            return job_status.status == "completed"

        except Exception as e:
            logger.error(
                "Failed to run consumer manually", job_type=job_type, error=str(e)
            )
            return False

    def get_consumer_status(self) -> Dict[str, Dict]:
        """Get status of all consumers.

        Returns:
        -------
            Dictionary with consumer status information
        """
        status = {}

        for job_type, consumer in self.consumers.items():
            task = self.running_tasks.get(job_type)

            status[job_type] = {
                "is_running": consumer.is_running,
                "last_run": (
                    consumer.last_run.isoformat() if consumer.last_run else None
                ),
                "total_items_processed": consumer.total_items_processed,
                "interval_minutes": consumer.interval_minutes,
                "task_status": "running" if task and not task.done() else "stopped",
            }

        return status

    def list_available_consumers(self) -> List[str]:
        """Get list of available consumer types.

        Returns:
        -------
            List of consumer job types
        """
        return list(self.consumers.keys())


# Global scheduler instance
scheduler = ConsumerScheduler()
