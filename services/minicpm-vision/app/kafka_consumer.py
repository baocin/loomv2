"""Kafka consumer for processing image messages."""

import json
import time
from typing import List, Optional

import asyncpg
import psutil
import structlog
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.errors import KafkaError
from loom_common.kafka.activity_logger import ConsumerActivityLogger
from loom_common.kafka.consumer_config_loader import KafkaConsumerConfigLoader

from app.models import ImageMessage, VisionAnalysisResult
from app.vision_processor import VisionProcessor

logger = structlog.get_logger()


class KafkaImageConsumer(ConsumerActivityLogger):
    """Consumes image messages from Kafka and processes them."""

    def __init__(
        self,
        bootstrap_servers: str,
        input_topics: List[str],
        output_topic: str,
        consumer_group: str = "minicpm-vision-consumer",
        device: Optional[str] = None,
        service_name: str = "minicpm-vision",
        database_url: Optional[str] = None,
    ):
        """Initialize Kafka consumer.

        Args:
            bootstrap_servers: Kafka bootstrap servers
            input_topics: List of topics to consume from
            output_topic: Topic to produce results to
            consumer_group: Consumer group ID
            device: Device for model inference ('cuda', 'cpu', or None)
            service_name: Service name for configuration
            database_url: Database URL for config loader
        """
        # Initialize activity logger
        super().__init__(service_name=service_name)

        self.bootstrap_servers = bootstrap_servers
        self.input_topics = input_topics
        self.output_topic = output_topic
        self.consumer_group = consumer_group
        self.service_name = service_name
        self.database_url = database_url

        self.consumer: Optional[AIOKafkaConsumer] = None
        self.producer: Optional[AIOKafkaProducer] = None
        self.vision_processor = VisionProcessor(device=device)
        self.db_pool: Optional[asyncpg.Pool] = None
        self.config_loader: Optional[KafkaConsumerConfigLoader] = None
        self.running = False
        self._messages_processed = 0
        self._last_metrics_time = time.time()
        self._metrics_interval = 60.0  # Record metrics every minute

        logger.info(
            "Initializing KafkaImageConsumer",
            bootstrap_servers=bootstrap_servers,
            input_topics=input_topics,
            output_topic=output_topic,
            consumer_group=consumer_group,
        )

    async def start(self) -> None:
        """Start the Kafka consumer and producer."""
        try:
            # Create database pool if database URL is provided
            if self.database_url:
                self.db_pool = await asyncpg.create_pool(
                    self.database_url,
                    min_size=2,
                    max_size=10,
                )
                self.config_loader = KafkaConsumerConfigLoader(self.db_pool)

                # Create optimized consumer using config loader
                self.consumer = await self.config_loader.create_consumer(
                    service_name=self.service_name,
                    topics=self.input_topics,
                    kafka_bootstrap_servers=self.bootstrap_servers,
                    group_id=self.consumer_group,
                )
            else:
                # Fallback to regular consumer
                self.consumer = AIOKafkaConsumer(
                    *self.input_topics,
                    bootstrap_servers=self.bootstrap_servers,
                    group_id=self.consumer_group,
                    auto_offset_reset="earliest",
                    enable_auto_commit=False,  # Manual commit for better reliability
                    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                )

            # Initialize producer
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                compression_type=None,  # Disabled lz4 compression temporarily
            )

            # Start both
            await self.consumer.start()
            await self.producer.start()

            # Initialize activity logger
            await self.init_activity_logger()

            # Load the vision model
            await self.vision_processor.load_model()

            # Update global model_loaded flag
            import app.main

            app.main.model_loaded = True

            self.running = True
            logger.info(
                "Kafka consumer and producer started successfully, model loaded"
            )

        except Exception as e:
            logger.error("Failed to start Kafka consumer/producer", error=str(e))
            raise

    async def stop(self) -> None:
        """Stop the Kafka consumer and producer."""
        self.running = False

        if self.consumer:
            await self.consumer.stop()

        if self.producer:
            await self.producer.stop()

        if self.db_pool:
            await self.db_pool.close()

        # Close activity logger
        await self.close_activity_logger()

        logger.info("Kafka consumer and producer stopped")

    async def process_message(self, message: dict) -> Optional[VisionAnalysisResult]:
        """Process a single image message.

        Args:
            message: Raw message from Kafka

        Returns:
            VisionAnalysisResult or None if processing failed
        """
        try:
            # Parse and validate message
            image_msg = ImageMessage(**message)

            logger.info(
                "Processing image message",
                device_id=image_msg.device_id,
                recorded_at=image_msg.recorded_at,
                format=image_msg.format,
            )

            # Analyze the image
            result = await self.vision_processor.analyze_image(
                base64_image=image_msg.data,
                device_id=image_msg.device_id,
                recorded_at=image_msg.recorded_at.isoformat(),
            )

            return result

        except Exception as e:
            logger.error(
                "Failed to process image message",
                error=str(e),
                error_type=type(e).__name__,
                device_id=message.get("device_id"),
            )
            return None

    async def consume_messages(self) -> None:
        """Main consumer loop."""
        logger.info("Starting message consumption loop")

        async for msg in self.consumer:
            if not self.running:
                break

            try:
                logger.debug(
                    "Received message",
                    topic=msg.topic,
                    partition=msg.partition,
                    offset=msg.offset,
                )

                # Log consumption
                await self.log_consumption(msg)

                # Process the message
                start_time = time.time()
                result = await self.process_message(msg.value)
                processing_time_ms = (time.time() - start_time) * 1000

                if result:
                    # Send result to output topic
                    result_data = result.model_dump(mode="json")
                    await self.producer.send_and_wait(
                        self.output_topic,
                        value=result_data,
                        key=result.device_id.encode("utf-8"),
                    )

                    # Log production
                    await self.log_production(
                        self.output_topic, result_data, result.device_id
                    )

                    logger.info(
                        "Sent analysis result",
                        device_id=result.device_id,
                        output_topic=self.output_topic,
                        num_objects=len(result.detected_objects),
                        has_text=bool(result.full_text),
                        processing_time_ms=round(processing_time_ms, 2),
                    )

                    # Commit offset after successful processing
                    await self.consumer.commit()
                    self._messages_processed += 1

                    # Record metrics periodically
                    await self._maybe_record_metrics()
                else:
                    logger.warning(
                        "Message processing failed, not committing offset",
                        topic=msg.topic,
                        partition=msg.partition,
                        offset=msg.offset,
                    )

            except KafkaError as e:
                logger.error(
                    "Kafka error while processing message",
                    error=str(e),
                    error_type=type(e).__name__,
                )

            except Exception as e:
                logger.error(
                    "Unexpected error while processing message",
                    error=str(e),
                    error_type=type(e).__name__,
                )

    async def run(self) -> None:
        """Run the consumer until stopped."""
        await self.start()

        try:
            await self.consume_messages()
        finally:
            await self.stop()

    async def _maybe_record_metrics(self) -> None:
        """Record processing metrics periodically."""
        current_time = time.time()
        time_since_last_metrics = current_time - self._last_metrics_time

        if time_since_last_metrics >= self._metrics_interval and self.config_loader:
            try:
                # Get memory usage
                process = psutil.Process()
                memory_usage_mb = process.memory_info().rss / 1024 / 1024

                # Record processing metrics
                await self.config_loader.record_processing_metrics(
                    service_name=self.service_name,
                    messages_processed=self._messages_processed,
                    processing_time_ms=time_since_last_metrics * 1000,
                    memory_usage_mb=memory_usage_mb,
                )

                # Record consumer lag for each partition
                if self.consumer:
                    partitions = self.consumer.assignment()
                    for tp in partitions:
                        try:
                            # Get current position
                            position = await self.consumer.position(tp)
                            # Get end offset
                            end_offsets = await self.consumer.end_offsets([tp])
                            end_offset = end_offsets.get(tp, position)
                            # Calculate lag
                            lag = end_offset - position

                            await self.config_loader.record_consumer_lag(
                                service_name=self.service_name,
                                topic=tp.topic,
                                partition=tp.partition,
                                lag=lag,
                                offset=position,
                            )
                        except Exception as e:
                            logger.warning(
                                "Failed to record lag for partition",
                                topic=tp.topic,
                                partition=tp.partition,
                                error=str(e),
                            )

                self._last_metrics_time = current_time
                logger.info(
                    "Recorded processing metrics",
                    messages_processed=self._messages_processed,
                    memory_usage_mb=round(memory_usage_mb, 2),
                )

            except Exception as e:
                logger.error("Failed to record metrics", error=str(e))


async def create_and_run_consumer(
    bootstrap_servers: str,
    input_topics: List[str],
    output_topic: str,
    consumer_group: str = "minicpm-vision-consumer",
    device: Optional[str] = None,
    service_name: str = "minicpm-vision",
    database_url: Optional[str] = None,
) -> None:
    """Create and run a Kafka image consumer.

    Args:
        bootstrap_servers: Kafka bootstrap servers
        input_topics: List of topics to consume from
        output_topic: Topic to produce results to
        consumer_group: Consumer group ID
        device: Device for model inference
        service_name: Service name for configuration
        database_url: Database URL for config loader
    """
    consumer = KafkaImageConsumer(
        bootstrap_servers=bootstrap_servers,
        input_topics=input_topics,
        output_topic=output_topic,
        consumer_group=consumer_group,
        device=device,
        service_name=service_name,
        database_url=database_url,
    )

    await consumer.run()
