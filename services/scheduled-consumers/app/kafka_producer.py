"""Kafka producer for scheduled consumers."""

import json
from typing import Any
import structlog
from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError

from .config import settings
from .models import BaseMessage

logger = structlog.get_logger(__name__)


class KafkaProducerService:
    """Async Kafka producer for sending scheduled consumer messages."""
    
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
            
            # Send message and wait for confirmation
            future = self._producer.send(
                topic=topic,
                value=message,
                key=message_key,
            )
            record_metadata = await future
            
            logger.info(
                "Message sent to Kafka successfully",
                topic=topic,
                device_id=message.device_id,
                message_id=getattr(message, 'message_id', 'unknown'),
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