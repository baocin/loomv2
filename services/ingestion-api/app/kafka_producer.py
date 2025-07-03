"""Kafka producer service for sending messages to topics."""

import json
from typing import Any

import structlog
from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError

from .config import settings
from .models import BaseMessage
from .tracing import add_service_to_trace, get_trace_context

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
            logger.exception("Failed to start Kafka producer", error=str(e))
            self._is_connected = False
            raise

    async def stop(self) -> None:
        """Stop the Kafka producer connection."""
        if self._producer:
            try:
                await self._producer.stop()
                logger.info("Kafka producer stopped")
            except Exception as e:
                logger.exception("Error stopping Kafka producer", error=str(e))
            finally:
                self._is_connected = False
                self._producer = None

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
            # Add kafka-producer to services encountered
            add_service_to_trace("kafka-producer")

            # Get trace context for headers and message payload
            trace_context = get_trace_context()

            # Use device_id as key if no key provided
            message_key = key or (
                message.device_id if hasattr(message, "device_id") else "unknown"
            )

            # Add trace context to message if it's a BaseMessage
            if isinstance(message, BaseMessage):
                # Update the message with trace information
                if hasattr(message, "__dict__"):
                    message.__dict__.update(
                        {
                            "trace_id": trace_context.get("trace_id"),
                            "services_encountered": trace_context.get(
                                "services_encountered",
                                [],
                            ),
                        },
                    )

            # Create headers with trace information (Kafka expects list of tuples)
            headers = [
                ("trace_id", trace_context.get("trace_id", "").encode("utf-8")),
                (
                    "services_encountered",
                    ",".join(
                        trace_context.get("services_encountered", []),
                    ).encode("utf-8"),
                ),
                ("producer_service", b"ingestion-api"),
            ]

            # Send message and wait for confirmation
            await self._producer.send(
                topic=topic,
                value=message,
                key=message_key,
                headers=headers,
            )

            # Log without accessing future attributes
            device_id_for_log = (
                message.device_id if hasattr(message, "device_id") else "unknown"
            )
            logger.info(
                "Message sent to Kafka successfully",
                topic=topic,
                device_id=device_id_for_log,
            )

        except KafkaError as e:
            device_id_for_log = (
                message.device_id if hasattr(message, "device_id") else "unknown"
            )
            logger.exception(
                "Failed to send message to Kafka",
                topic=topic,
                device_id=device_id_for_log,
                error=str(e),
            )
            raise
        except Exception as e:
            # Don't log complex objects that might cause issues
            error_msg = str(e)
            logger.exception(
                "Unexpected error sending message",
                topic=topic,
                device_id=getattr(message, "device_id", "unknown"),
                error=error_msg,
                error_type=type(e).__name__,
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

    async def send_health_data(self, health_data: Any, health_type: str) -> None:
        """Send health data to the appropriate health topic."""
        topic = f"device.health.{health_type}.raw"
        await self.send_message(
            topic=topic,
            message=health_data,
        )

    async def send_network_data(self, network_data: Any, network_type: str) -> None:
        """Send network data to the appropriate network topic."""
        topic = f"device.network.{network_type}.raw"
        await self.send_message(
            topic=topic,
            message=network_data,
        )

    async def send_state_data(self, state_data: Any, state_type: str) -> None:
        """Send state data to the appropriate state topic."""
        topic = f"device.state.{state_type}.raw"
        await self.send_message(
            topic=topic,
            message=state_data,
        )

    async def send_digital_data(self, digital_data: Any, data_type: str) -> None:
        """Send digital data to the appropriate digital topic."""
        topic = f"digital.{data_type}.raw"
        await self.send_message(
            topic=topic,
            message=digital_data,
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
        return json.dumps(message).encode("utf-8")

    @staticmethod
    def _serialize_key(key: str | None) -> bytes | None:
        """Serialize message key to bytes."""
        if key is None:
            return None
        return key.encode("utf-8")


# Global producer instance
kafka_producer = KafkaProducerService()
