"""Kafka producer for embedding results."""

import json
from typing import Dict, Any

import structlog
from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError

from .config import settings

logger = structlog.get_logger(__name__)


class EmbeddingKafkaProducer:
    """Kafka producer for sending embedding results."""

    def __init__(self):
        """Initialize the Kafka producer."""
        self.producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        """Start the Kafka producer."""
        logger.info("Starting embedding Kafka producer")

        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=settings.kafka_bootstrap_servers,
                value_serializer=self._serialize_message,
                key_serializer=lambda x: x.encode("utf-8") if x else None,
                compression_type="lz4",  # Use compression for large embedding vectors
                acks="all",  # Wait for all replicas to acknowledge
                retries=3,
                max_in_flight_requests_per_connection=1,  # Ensure ordering
            )

            await self.producer.start()
            logger.info("Kafka producer started successfully")

        except Exception as e:
            logger.error(f"Failed to start Kafka producer: {e}")
            raise

    async def stop(self) -> None:
        """Stop the Kafka producer."""
        if self.producer:
            logger.info("Stopping embedding Kafka producer")
            await self.producer.stop()
            self.producer = None
            logger.info("Kafka producer stopped")

    async def send_text_embedding(self, embedding_data: Dict[str, Any]) -> None:
        """Send text embedding to Kafka topic."""
        if not self.producer:
            raise RuntimeError("Producer not started")

        try:
            # Use device_id as the message key for partitioning
            key = embedding_data.get("device_id")

            await self.producer.send(
                topic=settings.text_embedding_topic,
                value=embedding_data,
                key=key,
            )

            logger.debug(
                f"Text embedding sent to {settings.text_embedding_topic}",
                device_id=key,
                source_topic=embedding_data.get("source_topic"),
                embedding_dimension=embedding_data.get("embedding_dimension"),
            )

        except KafkaError as e:
            logger.error(f"Kafka error sending text embedding: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to send text embedding: {e}")
            raise

    async def send_image_embedding(self, embedding_data: Dict[str, Any]) -> None:
        """Send image embedding to Kafka topic."""
        if not self.producer:
            raise RuntimeError("Producer not started")

        try:
            # Use device_id as the message key for partitioning
            key = embedding_data.get("device_id")

            await self.producer.send(
                topic=settings.image_embedding_topic,
                value=embedding_data,
                key=key,
            )

            logger.debug(
                f"Image embedding sent to {settings.image_embedding_topic}",
                device_id=key,
                source_topic=embedding_data.get("source_topic"),
                embedding_dimension=embedding_data.get("embedding_dimension"),
                image_size=f"{embedding_data.get('image_width')}x{embedding_data.get('image_height')}",
            )

        except KafkaError as e:
            logger.error(f"Kafka error sending image embedding: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to send image embedding: {e}")
            raise

    async def send_batch_embeddings(
        self, text_embeddings: list[Dict[str, Any]], image_embeddings: list[Dict[str, Any]]
    ) -> None:
        """Send batch of embeddings."""
        try:
            # Send text embeddings
            for embedding in text_embeddings:
                await self.send_text_embedding(embedding)

            # Send image embeddings
            for embedding in image_embeddings:
                await self.send_image_embedding(embedding)

            logger.info(
                f"Batch embeddings sent",
                text_count=len(text_embeddings),
                image_count=len(image_embeddings),
            )

        except Exception as e:
            logger.error(f"Failed to send batch embeddings: {e}")
            raise

    def _serialize_message(self, data: Dict[str, Any]) -> bytes:
        """Serialize message to JSON bytes."""
        try:
            return json.dumps(data, default=str).encode("utf-8")
        except Exception as e:
            logger.error(f"Failed to serialize message: {e}")
            raise