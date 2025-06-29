"""
Base Kafka producer with common functionality
"""

import json
from typing import Any, Dict, Optional

import orjson
import structlog
from aiokafka import AIOKafkaProducer
from kafka import KafkaProducer as SyncKafkaProducer

from loom_common.config import BaseSettings

logger = structlog.get_logger(__name__)


class BaseKafkaProducer:
    """Base async Kafka producer with standard configuration"""

    def __init__(self, settings: BaseSettings):
        self.settings = settings
        self.producer: Optional[AIOKafkaProducer] = None

    async def start(self) -> None:
        """Start the Kafka producer"""
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.settings.kafka_bootstrap_servers,
            value_serializer=lambda v: orjson.dumps(v, default=str),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
            acks="all",
            enable_idempotence=True,
            max_in_flight_requests_per_connection=5,
            compression_type="lz4",
        )
        await self.producer.start()
        logger.info(
            "Kafka producer started",
            bootstrap_servers=self.settings.kafka_bootstrap_servers,
        )

    async def stop(self) -> None:
        """Stop the Kafka producer"""
        if self.producer:
            await self.producer.stop()
            logger.info("Kafka producer stopped")

    async def send_message(
        self,
        topic: str,
        value: Dict[str, Any],
        key: Optional[str] = None,
        headers: Optional[Dict[str, bytes]] = None,
    ) -> None:
        """Send a message to a Kafka topic"""
        if not self.producer:
            raise RuntimeError("Producer not started")

        full_topic = self.settings.get_kafka_topic(topic)

        try:
            await self.producer.send(
                full_topic,
                value=value,
                key=key,
                headers=list(headers.items()) if headers else None,
            )

            logger.debug(
                "Message sent to Kafka",
                topic=full_topic,
                key=key,
                value_size=len(orjson.dumps(value, default=str)),
            )
        except Exception as e:
            logger.error(
                "Failed to send message to Kafka",
                topic=full_topic,
                key=key,
                error=str(e),
                exc_info=True,
            )
            raise

    async def send_batch(
        self, topic: str, messages: list[tuple[Optional[str], Dict[str, Any]]]
    ) -> None:
        """Send a batch of messages to a Kafka topic"""
        if not self.producer:
            raise RuntimeError("Producer not started")

        full_topic = self.settings.get_kafka_topic(topic)
        batch = self.producer.create_batch()

        for key, value in messages:
            metadata = batch.append(
                key=key.encode("utf-8") if key else None,
                value=orjson.dumps(value, default=str),
                timestamp=None,
            )
            if metadata is None:
                # Batch is full, send it
                await self.producer.send_batch(batch, full_topic)
                batch = self.producer.create_batch()
                # Retry adding the message
                batch.append(
                    key=key.encode("utf-8") if key else None,
                    value=orjson.dumps(value, default=str),
                    timestamp=None,
                )

        # Send any remaining messages
        if batch.record_count() > 0:
            await self.producer.send_batch(batch, full_topic)

        logger.info(
            "Batch sent to Kafka", topic=full_topic, message_count=len(messages)
        )


class BaseSyncKafkaProducer:
    """Base synchronous Kafka producer for non-async contexts"""

    def __init__(self, settings: BaseSettings):
        self.settings = settings
        self.producer = SyncKafkaProducer(
            bootstrap_servers=self.settings.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
            acks="all",
            retries=3,
            max_in_flight_requests_per_connection=5,
            compression_type="lz4",
        )
        logger.info(
            "Sync Kafka producer initialized",
            bootstrap_servers=self.settings.kafka_bootstrap_servers,
        )

    def send_message(
        self, topic: str, value: Dict[str, Any], key: Optional[str] = None
    ) -> None:
        """Send a message to a Kafka topic synchronously"""
        full_topic = self.settings.get_kafka_topic(topic)

        try:
            future = self.producer.send(full_topic, value=value, key=key)
            # Wait for send to complete
            record_metadata = future.get(timeout=10)

            logger.debug(
                "Message sent to Kafka",
                topic=full_topic,
                partition=record_metadata.partition,
                offset=record_metadata.offset,
                key=key,
            )
        except Exception as e:
            logger.error(
                "Failed to send message to Kafka",
                topic=full_topic,
                key=key,
                error=str(e),
                exc_info=True,
            )
            raise

    def close(self) -> None:
        """Close the producer"""
        self.producer.flush()
        self.producer.close()
        logger.info("Sync Kafka producer closed")
