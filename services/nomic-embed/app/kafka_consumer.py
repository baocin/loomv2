"""Kafka consumer for embedding processing."""

import asyncio
import json
from typing import Any

import structlog
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError

from .config import settings
from .embedding_processor import NomicEmbeddingProcessor
from .kafka_producer import EmbeddingKafkaProducer

logger = structlog.get_logger(__name__)


class EmbeddingKafkaConsumer:
    """Kafka consumer for processing text and image data for embeddings."""

    def __init__(self):
        """Initialize the Kafka consumer."""
        self.consumer: AIOKafkaConsumer | None = None
        self.producer: EmbeddingKafkaProducer | None = None
        self.processor: NomicEmbeddingProcessor | None = None
        self.running = False
        self.processing_queue: asyncio.Queue = asyncio.Queue(
            maxsize=settings.max_queue_size
        )
        self.workers: list[asyncio.Task] = []

    async def start(self) -> None:
        """Start the Kafka consumer and processing workers."""
        logger.info("Starting embedding Kafka consumer")

        try:
            # Initialize components
            self.processor = NomicEmbeddingProcessor()
            await self.processor.initialize()

            self.producer = EmbeddingKafkaProducer()
            await self.producer.start()

            # Get all input topics
            all_topics = settings.text_input_topics + settings.image_input_topics
            logger.info(f"Subscribing to topics: {all_topics}")

            # Create Kafka consumer
            self.consumer = AIOKafkaConsumer(
                *all_topics,
                bootstrap_servers=settings.kafka_bootstrap_servers,
                group_id=settings.kafka_group_id,
                auto_offset_reset=settings.kafka_auto_offset_reset,
                enable_auto_commit=settings.kafka_enable_auto_commit,
                value_deserializer=self._deserialize_message,
                key_deserializer=lambda x: x.decode("utf-8") if x else None,
            )

            await self.consumer.start()
            logger.info("Kafka consumer started successfully")

            # Start processing workers
            self.running = True
            for i in range(settings.worker_concurrency):
                worker = asyncio.create_task(self._processing_worker(f"worker-{i}"))
                self.workers.append(worker)

            logger.info(f"Started {len(self.workers)} processing workers")

            # Start consuming messages
            await self._consume_messages()

        except Exception as e:
            logger.error(f"Failed to start Kafka consumer: {e}")
            await self.stop()
            raise

    async def stop(self) -> None:
        """Stop the Kafka consumer and workers."""
        logger.info("Stopping embedding Kafka consumer")

        self.running = False

        # Stop workers
        if self.workers:
            for worker in self.workers:
                worker.cancel()
            await asyncio.gather(*self.workers, return_exceptions=True)
            self.workers.clear()

        # Stop Kafka consumer
        if self.consumer:
            await self.consumer.stop()
            self.consumer = None

        # Stop producer
        if self.producer:
            await self.producer.stop()
            self.producer = None

        # Cleanup processor
        if self.processor:
            await self.processor.cleanup()
            self.processor = None

        logger.info("Embedding Kafka consumer stopped")

    async def _consume_messages(self) -> None:
        """Consume messages from Kafka topics."""
        try:
            async for message in self.consumer:
                if not self.running:
                    break

                try:
                    # Add message to processing queue
                    await asyncio.wait_for(
                        self.processing_queue.put((message.topic, message.value)),
                        timeout=settings.batch_timeout_seconds,
                    )

                    logger.debug(
                        f"Queued message from topic {message.topic}",
                        queue_size=self.processing_queue.qsize(),
                    )

                except TimeoutError:
                    logger.warning(
                        f"Processing queue full, dropping message from {message.topic}"
                    )
                except Exception as e:
                    logger.error(f"Error queuing message: {e}")

        except KafkaError as e:
            logger.error(f"Kafka error while consuming: {e}")
        except Exception as e:
            logger.error(f"Unexpected error while consuming: {e}")

    async def _processing_worker(self, worker_id: str) -> None:
        """Worker coroutine for processing messages."""
        logger.info(f"Starting processing worker: {worker_id}")

        while self.running:
            try:
                # Get message from queue with timeout
                topic, message_data = await asyncio.wait_for(
                    self.processing_queue.get(),
                    timeout=settings.batch_timeout_seconds,
                )

                # Process the message
                await self._process_single_message(topic, message_data, worker_id)

                # Mark task as done
                self.processing_queue.task_done()

            except TimeoutError:
                # Timeout is normal - just continue
                continue
            except Exception as e:
                logger.error(f"Error in processing worker {worker_id}: {e}")
                await asyncio.sleep(1)

        logger.info(f"Processing worker {worker_id} stopped")

    async def _process_single_message(
        self, topic: str, message_data: dict[str, Any], worker_id: str
    ) -> None:
        """Process a single message and produce embeddings."""
        try:
            start_time = asyncio.get_event_loop().time()

            # Process message with embedding processor
            results = await self.processor.process_message(message_data, topic)

            if not results:
                logger.debug(f"No embeddings generated for message from {topic}")
                return

            # Send results to appropriate output topics
            for embedding_type, result in results:
                if embedding_type == "text":
                    await self.producer.send_text_embedding(result)
                elif embedding_type == "image":
                    await self.producer.send_image_embedding(result)

            processing_time = (asyncio.get_event_loop().time() - start_time) * 1000

            logger.info(
                f"Processed message from {topic}",
                worker_id=worker_id,
                embeddings_generated=len(results),
                processing_time_ms=f"{processing_time:.2f}",
            )

        except Exception as e:
            logger.error(
                f"Failed to process message from {topic}",
                worker_id=worker_id,
                error=str(e),
            )

    def _deserialize_message(self, data: bytes) -> dict[str, Any]:
        """Deserialize Kafka message."""
        try:
            return json.loads(data.decode("utf-8"))
        except Exception as e:
            logger.error(f"Failed to deserialize message: {e}")
            return {}

    def get_status(self) -> dict[str, Any]:
        """Get consumer status."""
        stats = {}
        if self.processor:
            stats.update(self.processor.get_stats())

        return {
            "running": self.running,
            "queue_size": self.processing_queue.qsize(),
            "active_workers": len(self.workers),
            "subscribed_topics": settings.text_input_topics
            + settings.image_input_topics,
            **stats,
        }
