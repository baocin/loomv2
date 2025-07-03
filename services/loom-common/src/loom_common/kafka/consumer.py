"""
Base Kafka consumer with common functionality
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set

import orjson
import structlog
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer, ConsumerRecord
from aiokafka.errors import CommitFailedError

from loom_common.config import BaseSettings

logger = structlog.get_logger(__name__)


class BaseKafkaConsumer(ABC):
    """Base async Kafka consumer with standard configuration and error handling"""

    def __init__(
        self,
        settings: BaseSettings,
        topics: List[str],
        group_id: str,
        enable_auto_commit: bool = False,
        max_poll_records: int = 100,
    ):
        self.settings = settings
        self.topics = [settings.get_kafka_topic(t) for t in topics]
        self.group_id = settings.get_consumer_group(group_id)
        self.enable_auto_commit = enable_auto_commit
        self.max_poll_records = max_poll_records

        self.consumer: Optional[AIOKafkaConsumer] = None
        self.producer: Optional[AIOKafkaProducer] = None
        self._running = False
        self._tasks: Set[asyncio.Task] = set()
        self._messages_processed = 0
        self._last_commit_time = 0.0
        self._commit_interval = 5.0  # Commit every 5 seconds
        self._commit_batch_size = 100  # Or every 100 messages

    async def start(self) -> None:
        """Start the consumer and producer"""
        # Start consumer
        self.consumer = AIOKafkaConsumer(
            *self.topics,
            bootstrap_servers=self.settings.kafka_bootstrap_servers,
            group_id=self.group_id,
            enable_auto_commit=self.enable_auto_commit,
            auto_offset_reset="earliest",
            value_deserializer=lambda v: orjson.loads(v) if v else None,
            key_deserializer=lambda k: k.decode("utf-8") if k else None,
            max_poll_records=self.max_poll_records,
            session_timeout_ms=30000,  # 30 seconds
            heartbeat_interval_ms=3000,  # 3 seconds
            max_poll_interval_ms=300000,  # 5 minutes for slow processing
            consumer_timeout_ms=5000,  # 5 seconds
        )

        # Start producer for output messages
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.settings.kafka_bootstrap_servers,
            value_serializer=lambda v: orjson.dumps(v, default=str),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
            acks="all",
            enable_idempotence=True,
            compression_type="lz4",
        )

        await self.consumer.start()
        await self.producer.start()
        
        # Initialize commit tracking
        import time
        self._last_commit_time = time.time()

        logger.info(
            "Kafka consumer started",
            topics=self.topics,
            group_id=self.group_id,
            bootstrap_servers=self.settings.kafka_bootstrap_servers,
        )

    async def stop(self) -> None:
        """Stop the consumer and producer"""
        self._running = False

        # Cancel all tasks
        for task in self._tasks:
            task.cancel()

        # Wait for tasks to complete
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        # Commit any pending offsets before stopping
        if self.consumer and not self.enable_auto_commit and self._messages_processed > 0:
            try:
                await self.consumer.commit()
                logger.info("Final commit before shutdown", messages_processed=self._messages_processed)
            except Exception as e:
                logger.error("Failed to commit final offsets", error=str(e))

        # Stop consumer and producer
        if self.consumer:
            await self.consumer.stop()
        if self.producer:
            await self.producer.stop()

        logger.info("Kafka consumer stopped")

    async def run(self) -> None:
        """Main consumer loop"""
        if not self.consumer:
            raise RuntimeError("Consumer not started")

        self._running = True

        try:
            async for message in self.consumer:
                if not self._running:
                    break

                # Create task for concurrent processing
                task = asyncio.create_task(self._process_message_wrapper(message))
                self._tasks.add(task)
                task.add_done_callback(self._tasks.discard)

                # Limit concurrent tasks
                if len(self._tasks) >= self.max_poll_records:
                    # Wait for some tasks to complete
                    await asyncio.gather(*self._tasks, return_exceptions=True)
                
                # Check if we need to commit based on time (for low-volume topics)
                if not self.enable_auto_commit:
                    await self._maybe_commit()

        except Exception as e:
            logger.error("Error in consumer loop", error=str(e), exc_info=True)
            raise

    async def _process_message_wrapper(self, message: ConsumerRecord) -> None:
        """Wrapper to handle message processing with error handling"""
        try:
            await self.process_message(message)

            # Track successful processing
            if not self.enable_auto_commit:
                self._messages_processed += 1
                await self._maybe_commit()

        except Exception as e:
            logger.error(
                "Error processing message",
                topic=message.topic,
                partition=message.partition,
                offset=message.offset,
                key=message.key,
                error=str(e),
                exc_info=True,
            )

            # Send to DLQ if configured
            await self._send_to_dlq(message, e)

            # Still commit offset to avoid reprocessing
            if not self.enable_auto_commit:
                # Force commit for failed messages to skip them
                await self._commit_offset(message)

    async def _maybe_commit(self) -> None:
        """Commit offsets if batch size or time interval is reached."""
        import time
        current_time = time.time()
        time_since_last_commit = current_time - self._last_commit_time
        
        if (self._messages_processed >= self._commit_batch_size or 
            time_since_last_commit >= self._commit_interval):
            try:
                await self.consumer.commit()
                logger.info(
                    "Batch commit completed",
                    messages_processed=self._messages_processed,
                    time_since_last_commit=round(time_since_last_commit, 2)
                )
                self._messages_processed = 0
                self._last_commit_time = current_time
            except Exception as e:
                logger.error("Failed to commit offsets", error=str(e))

    async def _commit_offset(self, message: ConsumerRecord) -> None:
        """Commit offset for a processed message"""
        try:
            await self.consumer.commit(
                {message.topic: {message.partition: message.offset + 1}}
            )
        except CommitFailedError as e:
            logger.warning(
                "Failed to commit offset",
                topic=message.topic,
                partition=message.partition,
                offset=message.offset,
                error=str(e),
            )

    async def _send_to_dlq(self, message: ConsumerRecord, error: Exception) -> None:
        """Send failed message to dead letter queue"""
        dlq_topic = f"{message.topic}.dlq"

        dlq_message = {
            "original_topic": message.topic,
            "original_partition": message.partition,
            "original_offset": message.offset,
            "original_key": message.key,
            "original_value": message.value,
            "error": str(error),
            "error_type": type(error).__name__,
            "timestamp": message.timestamp,
            "consumer_group": self.group_id,
        }

        try:
            await self.producer.send(dlq_topic, value=dlq_message, key=message.key)
            logger.info(
                "Message sent to DLQ",
                dlq_topic=dlq_topic,
                original_topic=message.topic,
                original_offset=message.offset,
            )
        except Exception as dlq_error:
            logger.error(
                "Failed to send message to DLQ",
                dlq_topic=dlq_topic,
                error=str(dlq_error),
                exc_info=True,
            )

    async def send_to_topic(
        self,
        topic: str,
        value: Dict[str, Any],
        key: Optional[str] = None,
        headers: Optional[Dict[str, bytes]] = None,
    ) -> None:
        """Send a message to an output topic"""
        if not self.producer:
            raise RuntimeError("Producer not started")

        full_topic = self.settings.get_kafka_topic(topic)

        await self.producer.send(
            full_topic,
            value=value,
            key=key,
            headers=list(headers.items()) if headers else None,
        )

    @abstractmethod
    async def process_message(self, message: ConsumerRecord) -> None:
        """
        Process a single message from Kafka.

        This method must be implemented by subclasses.

        Args:
            message: The Kafka message to process
        """
        pass
