"""Kafka consumer for processing image messages."""

import json
from typing import List, Optional

import structlog
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.errors import KafkaError

from app.models import ImageMessage, VisionAnalysisResult
from app.vision_processor import VisionProcessor

logger = structlog.get_logger()


class KafkaImageConsumer:
    """Consumes image messages from Kafka and processes them."""

    def __init__(
        self,
        bootstrap_servers: str,
        input_topics: List[str],
        output_topic: str,
        consumer_group: str = "minicpm-vision-consumer",
        device: Optional[str] = None,
    ):
        """Initialize Kafka consumer.

        Args:
            bootstrap_servers: Kafka bootstrap servers
            input_topics: List of topics to consume from
            output_topic: Topic to produce results to
            consumer_group: Consumer group ID
            device: Device for model inference ('cuda', 'cpu', or None)
        """
        self.bootstrap_servers = bootstrap_servers
        self.input_topics = input_topics
        self.output_topic = output_topic
        self.consumer_group = consumer_group

        self.consumer: Optional[AIOKafkaConsumer] = None
        self.producer: Optional[AIOKafkaProducer] = None
        self.vision_processor = VisionProcessor(device=device)
        self.running = False

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
            # Initialize consumer
            self.consumer = AIOKafkaConsumer(
                *self.input_topics,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.consumer_group,
                auto_offset_reset="latest",
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

                # Process the message
                result = await self.process_message(msg.value)

                if result:
                    # Send result to output topic
                    await self.producer.send_and_wait(
                        self.output_topic,
                        value=result.model_dump(mode="json"),
                        key=result.device_id.encode("utf-8"),
                    )

                    logger.info(
                        "Sent analysis result",
                        device_id=result.device_id,
                        output_topic=self.output_topic,
                        num_objects=len(result.detected_objects),
                        has_text=bool(result.full_text),
                    )

                    # Commit offset after successful processing
                    await self.consumer.commit()
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


async def create_and_run_consumer(
    bootstrap_servers: str,
    input_topics: List[str],
    output_topic: str,
    consumer_group: str = "minicpm-vision-consumer",
    device: Optional[str] = None,
) -> None:
    """Create and run a Kafka image consumer.

    Args:
        bootstrap_servers: Kafka bootstrap servers
        input_topics: List of topics to consume from
        output_topic: Topic to produce results to
        consumer_group: Consumer group ID
        device: Device for model inference
    """
    consumer = KafkaImageConsumer(
        bootstrap_servers=bootstrap_servers,
        input_topics=input_topics,
        output_topic=output_topic,
        consumer_group=consumer_group,
        device=device,
    )

    await consumer.run()
