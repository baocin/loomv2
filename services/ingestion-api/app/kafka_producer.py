"""Kafka producer service for sending messages to topics."""

import json
from typing import Any

import structlog
from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError

from .config import settings
from .models import BaseMessage

logger = structlog.get_logger(__name__)


class KafkaProducerService:
    """Async Kafka producer for sending messages to topics."""

    def __init__(self) -> None:
        """Initialize the Kafka producer service."""
        self._producer: AIOKafkaProducer | None = None
        self._is_connected = False

    async def start(self) -> None:
        """Start the Kafka producer connection."""
        try:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=settings.kafka_bootstrap_servers,
                client_id=settings.kafka_client_id,
                value_serializer=self._serialize_message,
                key_serializer=self._serialize_key,
                # Basic configuration only - remove problematic parameters
                request_timeout_ms=30000,
            )

            await self._producer.start()
            self._is_connected = True

            logger.info(
                "Kafka producer started",
                bootstrap_servers=settings.kafka_bootstrap_servers,
                client_id=settings.kafka_client_id,
            )

        except Exception as e:
            logger.error("Failed to start Kafka producer", error=str(e))
            self._is_connected = False
            raise

    async def stop(self) -> None:
        """Stop the Kafka producer connection."""
        if self._producer:
            try:
                await self._producer.stop()
                self._is_connected = False
                logger.info("Kafka producer stopped")
            except Exception as e:
                logger.error("Error stopping Kafka producer", error=str(e))

    async def send_message(
        self,
        topic: str,
        message: BaseMessage,
        key: str | None = None,
    ) -> None:
        """Send a message to a Kafka topic.

        Args:
        ----
            topic: Kafka topic name
            message: Message to send (will be serialized to JSON)
            key: Optional message key (defaults to device_id)

        """
        if not self._is_connected or not self._producer:
            raise RuntimeError("Kafka producer not connected")

        try:
            # Use device_id as key if no key provided
            message_key = key or message.device_id

            # Send message
            record_metadata = await self._producer.send(
                topic=topic,
                value=message,
                key=message_key,
            )

            logger.debug(
                "Message sent to Kafka",
                topic=topic,
                partition=record_metadata.partition,
                offset=record_metadata.offset,
                device_id=message.device_id,
                message_id=message.message_id,
            )

        except KafkaError as e:
            logger.error(
                "Failed to send message to Kafka",
                topic=topic,
                device_id=message.device_id,
                error=str(e),
            )
            raise
        except Exception as e:
            logger.error(
                "Unexpected error sending message",
                topic=topic,
                device_id=message.device_id,
                error=str(e),
            )
            raise

    async def send_audio_chunk(self, audio_chunk: Any) -> None:
        """Send audio chunk to the audio topic."""
        await self.send_message(
            topic=settings.topic_device_audio_raw,
            message=audio_chunk,
        )

    async def send_sensor_data(self, sensor_data: Any, sensor_type: str) -> None:
        """Send sensor data to the appropriate sensor topic."""
        topic = settings.topic_device_sensor_raw.format(sensor_type=sensor_type)
        await self.send_message(
            topic=topic,
            message=sensor_data,
        )

    async def send_image_data(self, image_data: Any) -> None:
        """Send image data to the image topic."""
        await self.send_message(
            topic=settings.topic_device_image_raw,
            message=image_data,
        )

    @property
    def is_connected(self) -> bool:
        """Check if producer is connected to Kafka."""
        return self._is_connected

    @staticmethod
    def _serialize_message(message: BaseMessage) -> bytes:
        """Serialize message to JSON bytes."""
        if isinstance(message, BaseMessage):
            # Convert pydantic model to dict, handling datetime and bytes
            message_dict = message.model_dump(mode="json")
            return json.dumps(message_dict).encode("utf-8")
        else:
            return json.dumps(message).encode("utf-8")

    @staticmethod
    def _serialize_key(key: str | None) -> bytes | None:
        """Serialize message key to bytes."""
        if key is None:
            return None
        return key.encode("utf-8")


# Global producer instance
kafka_producer = KafkaProducerService()
