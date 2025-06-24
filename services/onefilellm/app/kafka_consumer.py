"""Kafka consumer manager for OneFileLLM service."""

import asyncio
import json
from typing import Any

import structlog
from aiokafka import AIOKafkaConsumer

from .config import settings
from .models import DocumentTask, GitHubTask

logger = structlog.get_logger(__name__)


class KafkaConsumerManager:
    """Manages Kafka consumers for GitHub and document processing tasks."""

    def __init__(self, github_processor, document_processor):
        """Initialize consumer manager.

        Args:
            github_processor: GitHubProcessor instance
            document_processor: DocumentProcessor instance
        """
        self.github_processor = github_processor
        self.document_processor = document_processor
        self.consumer: AIOKafkaConsumer | None = None
        self.running = False
        self.processing_tasks: set[asyncio.Task] = set()

    async def start(self) -> None:
        """Start the Kafka consumer."""
        logger.info("Starting Kafka consumer")

        self.consumer = AIOKafkaConsumer(
            settings.topic_github_ingest,
            settings.topic_document_ingest,
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id=settings.kafka_group_id,
            auto_offset_reset=settings.kafka_auto_offset_reset,
            value_deserializer=self._deserialize_message,
            enable_auto_commit=True,
            auto_commit_interval_ms=5000,
        )

        await self.consumer.start()
        self.running = True

        # Start the consumer loop
        asyncio.create_task(self._consume_loop())

        logger.info("Kafka consumer started successfully")

    async def stop(self) -> None:
        """Stop the Kafka consumer."""
        logger.info("Stopping Kafka consumer")

        self.running = False

        # Cancel all processing tasks
        for task in self.processing_tasks:
            if not task.done():
                task.cancel()

        # Wait for all tasks to complete
        if self.processing_tasks:
            await asyncio.gather(*self.processing_tasks, return_exceptions=True)

        if self.consumer:
            await self.consumer.stop()

        logger.info("Kafka consumer stopped")

    async def _consume_loop(self) -> None:
        """Main consumer loop."""
        logger.info("Starting consumer loop")

        try:
            async for message in self.consumer:
                if not self.running:
                    break

                # Create a task for processing each message
                task = asyncio.create_task(
                    self._process_message(message.topic, message.value)
                )
                self.processing_tasks.add(task)

                # Clean up completed tasks
                self.processing_tasks = {
                    t for t in self.processing_tasks if not t.done()
                }

        except asyncio.CancelledError:
            logger.info("Consumer loop cancelled")
        except Exception as e:
            logger.error("Error in consumer loop", error=str(e))
        finally:
            logger.info("Consumer loop ended")

    async def _process_message(self, topic: str, message_data: dict[str, Any]) -> None:
        """Process a single message.

        Args:
            topic: The Kafka topic the message came from
            message_data: Deserialized message data
        """
        try:
            if topic == settings.topic_github_ingest:
                task = GitHubTask(**message_data)
                await self.github_processor.process_github_task(task)

            elif topic == settings.topic_document_ingest:
                task = DocumentTask(**message_data)
                await self.document_processor.process_document_task(task)

            else:
                logger.warning("Received message from unknown topic", topic=topic)

        except Exception as e:
            logger.error(
                "Failed to process message",
                topic=topic,
                message_id=message_data.get("message_id"),
                error=str(e),
            )

    def _deserialize_message(self, message_bytes: bytes) -> dict[str, Any]:
        """Deserialize Kafka message.

        Args:
            message_bytes: Raw message bytes

        Returns:
            Deserialized message data
        """
        try:
            return json.loads(message_bytes.decode("utf-8"))
        except Exception as e:
            logger.error("Failed to deserialize message", error=str(e))
            raise
