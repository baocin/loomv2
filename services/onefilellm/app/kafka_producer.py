"""Kafka producer manager for OneFileLLM service."""

import json
from typing import Any

import structlog
from aiokafka import AIOKafkaProducer

from .config import settings
from .models import ProcessedDocument, ProcessedGitHub, ProcessingError

logger = structlog.get_logger(__name__)


class KafkaProducerManager:
    """Manages Kafka producer for sending processed results."""

    def __init__(self):
        """Initialize producer manager."""
        self.producer: AIOKafkaProducer | None = None
        self.is_connected = False

    async def start(self) -> None:
        """Start the Kafka producer."""
        logger.info("Starting Kafka producer")

        self.producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            value_serializer=self._serialize_message,
            compression_type="lz4",
            acks="all",
            retries=3,
        )

        await self.producer.start()
        self.is_connected = True

        logger.info("Kafka producer started successfully")

    async def stop(self) -> None:
        """Stop the Kafka producer."""
        logger.info("Stopping Kafka producer")

        if self.producer:
            await self.producer.stop()

        self.is_connected = False
        logger.info("Kafka producer stopped")

    async def send_processed_github(self, result: ProcessedGitHub) -> None:
        """Send processed GitHub result to Kafka.

        Args:
            result: Processed GitHub content
        """
        await self._send_message(
            topic=settings.topic_github_parsed,
            key=result.device_id,
            value=result.dict(),
        )

        logger.info(
            "Sent processed GitHub result",
            message_id=result.message_id,
            repository_name=result.repository_name,
            file_count=result.file_count,
        )

    async def send_processed_document(self, result: ProcessedDocument) -> None:
        """Send processed document result to Kafka.

        Args:
            result: Processed document content
        """
        await self._send_message(
            topic=settings.topic_document_parsed,
            key=result.device_id,
            value=result.dict(),
        )

        logger.info(
            "Sent processed document result",
            message_id=result.message_id,
            filename=result.original_filename,
            word_count=result.word_count,
        )

    async def send_processing_error(self, error: ProcessingError, topic: str) -> None:
        """Send processing error to appropriate error topic.

        Args:
            error: Processing error details
            topic: Base topic name (will append .errors)
        """
        error_topic = f"{topic}.errors"

        await self._send_message(
            topic=error_topic,
            key=error.device_id,
            value=error.dict(),
        )

        logger.warning(
            "Sent processing error",
            message_id=error.message_id,
            error_type=error.error_type,
            topic=error_topic,
        )

    async def _send_message(self, topic: str, key: str, value: Any) -> None:
        """Send a message to Kafka.

        Args:
            topic: Kafka topic
            key: Message key
            value: Message value
        """
        if not self.producer:
            raise RuntimeError("Kafka producer not started")

        try:
            await self.producer.send(topic, value=value, key=key.encode("utf-8"))
            logger.debug("Message sent successfully", topic=topic, key=key)

        except Exception as e:
            logger.error(
                "Failed to send message to Kafka",
                topic=topic,
                key=key,
                error=str(e),
            )
            raise

    def _serialize_message(self, message: Any) -> bytes:
        """Serialize message to JSON bytes.

        Args:
            message: Message to serialize

        Returns:
            Serialized message bytes
        """
        try:
            return json.dumps(message, default=str).encode("utf-8")
        except Exception as e:
            logger.error("Failed to serialize message", error=str(e))
            raise
