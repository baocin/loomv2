"""Kafka consumer service for processing messages and storing to database."""

import json
import asyncio
from typing import Dict, Any

import structlog
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError

from .config import settings
from .storage import database_storage

logger = structlog.get_logger(__name__)


class KafkaConsumerService:
    """Async Kafka consumer for processing messages and storing to database."""

    def __init__(self) -> None:
        """Initialize the Kafka consumer service."""
        self._consumers: Dict[str, AIOKafkaConsumer] = {}
        self._running = False
        self._tasks = []

    async def start(self) -> None:
        """Start Kafka consumers for all state topics."""
        try:
            # Initialize database storage
            await database_storage.start()

            # Define topic handlers
            topic_handlers = {
                settings.topic_device_state_lock: self._handle_lock_state_message,
                "device.state.power.raw": self._handle_power_state_message,
            }

            # Create consumers for each topic
            for topic, handler in topic_handlers.items():
                consumer = AIOKafkaConsumer(
                    topic,
                    bootstrap_servers=settings.kafka_bootstrap_servers,
                    group_id=f"{settings.kafka_client_id}-consumer",
                    auto_offset_reset='latest',  # Start from latest messages
                    enable_auto_commit=True,
                    auto_commit_interval_ms=5000,
                    value_deserializer=self._deserialize_message,
                )

                await consumer.start()
                self._consumers[topic] = consumer

                # Start consumer task
                task = asyncio.create_task(self._consume_messages(topic, consumer, handler))
                self._tasks.append(task)

                logger.info(
                    "Kafka consumer started",
                    topic=topic,
                    bootstrap_servers=settings.kafka_bootstrap_servers,
                )

            self._running = True

        except Exception as e:
            logger.error("Failed to start Kafka consumers", error=str(e))
            await self.stop()
            raise

    async def stop(self) -> None:
        """Stop all Kafka consumers."""
        self._running = False

        # Cancel all consumer tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()

        # Wait for tasks to complete
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        # Stop consumers
        for topic, consumer in self._consumers.items():
            try:
                await consumer.stop()
                logger.info("Kafka consumer stopped", topic=topic)
            except Exception as e:
                logger.error("Error stopping Kafka consumer", topic=topic, error=str(e))

        # Stop database storage
        await database_storage.stop()

        self._consumers.clear()
        self._tasks.clear()

    async def _consume_messages(
        self, 
        topic: str, 
        consumer: AIOKafkaConsumer, 
        handler: callable
    ) -> None:
        """Consume messages from a specific topic."""
        try:
            async for message in consumer:
                if not self._running:
                    break

                try:
                    # Process the message
                    await handler(message.value)

                    logger.debug(
                        "Message processed successfully",
                        topic=topic,
                        partition=message.partition,
                        offset=message.offset,
                    )

                except Exception as e:
                    logger.error(
                        "Error processing message",
                        topic=topic,
                        partition=message.partition,
                        offset=message.offset,
                        error=str(e),
                    )
                    # Continue processing other messages

        except Exception as e:
            if self._running:  # Only log if not shutting down
                logger.error("Error in consumer loop", topic=topic, error=str(e))

    async def _handle_lock_state_message(self, message_data: Dict[str, Any]) -> None:
        """Handle lock state messages."""
        try:
            success = await database_storage.store_lock_state(message_data)
            if success:
                logger.info(
                    "Lock state message processed",
                    device_id=message_data.get("device_id"),
                    is_locked=message_data.get("is_locked"),
                )
        except Exception as e:
            logger.error("Error handling lock state message", error=str(e))
            raise

    async def _handle_power_state_message(self, message_data: Dict[str, Any]) -> None:
        """Handle power state messages."""
        try:
            success = await database_storage.store_power_state(message_data)
            if success:
                logger.info(
                    "Power state message processed",
                    device_id=message_data.get("device_id"),
                    battery_level=message_data.get("battery_level"),
                )
        except Exception as e:
            logger.error("Error handling power state message", error=str(e))
            raise

    @staticmethod
    def _deserialize_message(message_bytes: bytes) -> Dict[str, Any]:
        """Deserialize JSON message from bytes."""
        try:
            return json.loads(message_bytes.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error("Failed to deserialize message", error=str(e))
            raise

    @property
    def is_running(self) -> bool:
        """Check if consumers are running."""
        return self._running


# Global consumer instance
kafka_consumer = KafkaConsumerService()