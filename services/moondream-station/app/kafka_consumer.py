"""Kafka consumer for processing image messages."""

import json
import time
from datetime import datetime
from typing import Dict, Optional

import structlog
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.errors import KafkaError

from .config import settings
from .models import (
    DetectedObject,
    ImageMessage,
    MoondreamAnalysisResult,
    OCRBlock,
)
from .moondream_client import MoondreamClient

logger = structlog.get_logger()


class KafkaConsumerManager:
    """Manages Kafka consumption for image processing."""

    def __init__(self, moondream_client: MoondreamClient):
        """Initialize Kafka consumer manager.

        Args:
            moondream_client: Initialized Moondream client
        """
        self.moondream_client = moondream_client
        self.bootstrap_servers = settings.kafka_bootstrap_servers
        self.input_topics = settings.kafka_input_topics
        self.output_topic = settings.kafka_output_topic
        self.consumer_group = settings.kafka_consumer_group

        self.consumer: Optional[AIOKafkaConsumer] = None
        self.producer: Optional[AIOKafkaProducer] = None
        self.running = False

        logger.info(
            "Initializing KafkaConsumerManager",
            bootstrap_servers=self.bootstrap_servers,
            input_topics=self.input_topics,
            output_topic=self.output_topic,
            consumer_group=self.consumer_group,
        )

    async def start(self) -> None:
        """Start the Kafka consumer and producer."""
        try:
            # Initialize consumer
            self.consumer = AIOKafkaConsumer(
                *self.input_topics,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.consumer_group,
                auto_offset_reset=settings.kafka_auto_offset_reset,
                enable_auto_commit=False,  # Manual commit for better reliability
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                max_poll_records=1,  # Process one message at a time
            )

            # Initialize producer
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                compression_type=settings.kafka_compression_type,
            )

            # Start both
            await self.consumer.start()
            await self.producer.start()

            self.running = True
            logger.info("Kafka consumer and producer started successfully")

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

    def is_healthy(self) -> bool:
        """Check if Kafka consumer/producer are healthy."""
        return self.running and self.consumer is not None and self.producer is not None

    async def process_image_message(
        self, message: Dict, topic: str
    ) -> Optional[MoondreamAnalysisResult]:
        """Process an image message."""
        try:
            image_msg = ImageMessage(**message)

            # Determine query based on topic
            query = None
            if "task.image.analyze" in topic:
                # Extract query from metadata if available
                query = image_msg.metadata.get("query") if image_msg.metadata else None

            start_time = time.time()

            # Perform full analysis
            response = await self.moondream_client.full_analysis(
                image_data=image_msg.data,
                query=query,
                enable_objects=settings.enable_object_detection,
                enable_ocr=settings.enable_ocr,
            )

            processing_time = (time.time() - start_time) * 1000

            # Convert response to analysis result
            detected_objects = []
            if response.objects:
                for obj in response.objects:
                    detected_objects.append(
                        DetectedObject(
                            label=obj.get("label", "unknown"),
                            confidence=obj.get("confidence", 0.5),
                            bbox=obj.get("bbox", [0, 0, 100, 100]),
                            attributes=obj.get("attributes"),
                        )
                    )

            ocr_blocks = []
            full_text = ""
            if response.text_blocks:
                text_parts = []
                for block in response.text_blocks:
                    ocr_block = OCRBlock(
                        text=block.get("text", ""),
                        confidence=block.get("confidence", 0.5),
                        bbox=block.get("bbox", [0, 0, 100, 100]),
                        language=block.get("language"),
                    )
                    ocr_blocks.append(ocr_block)
                    text_parts.append(ocr_block.text)
                full_text = " ".join(text_parts)

            # Extract visual features
            visual_features = await self.moondream_client.analyze_visual_features(
                image_msg.data
            )

            # Determine scene type from caption
            scene_type = None
            scene_attributes = []
            if response.caption:
                caption_lower = response.caption.lower()
                if "indoor" in caption_lower:
                    scene_type = "indoor"
                elif "outdoor" in caption_lower:
                    scene_type = "outdoor"
                elif "portrait" in caption_lower:
                    scene_type = "portrait"
                elif "landscape" in caption_lower:
                    scene_type = "landscape"

                # Extract attributes
                for attr in [
                    "nature",
                    "urban",
                    "people",
                    "animals",
                    "food",
                    "technology",
                ]:
                    if attr in caption_lower:
                        scene_attributes.append(attr)

            # Create object count
            object_count = {}
            for obj in detected_objects:
                label = obj.label
                object_count[label] = object_count.get(label, 0) + 1

            return MoondreamAnalysisResult(
                device_id=image_msg.device_id,
                recorded_at=image_msg.recorded_at,
                caption=response.caption or "",
                query_response=response.query_response,
                detected_objects=detected_objects,
                object_count=object_count,
                ocr_blocks=ocr_blocks,
                full_text=full_text if full_text else None,
                visual_features=visual_features,
                scene_type=scene_type,
                scene_attributes=scene_attributes if scene_attributes else None,
                image_quality_score=0.8,  # Mock quality score
                processing_time_ms=processing_time,
                model_version="moondream-latest",
            )

        except Exception as e:
            logger.error("Failed to process image message", error=str(e), topic=topic)
            # Return result with error
            return MoondreamAnalysisResult(
                device_id=message.get("device_id", "unknown"),
                recorded_at=datetime.utcnow(),
                caption="",
                detected_objects=[],
                object_count={},
                ocr_blocks=[],
                processing_time_ms=0,
                error=str(e),
                warnings=["Processing failed"],
            )

    async def consume_messages(self) -> None:
        """Main consumer loop."""
        logger.info("Starting image message consumption loop")

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

                # Process the image message
                result = await self.process_image_message(msg.value, msg.topic)

                if result and not result.error:
                    # Send result to output topic
                    await self.producer.send_and_wait(
                        self.output_topic,
                        value=result.model_dump(mode="json"),
                        key=result.device_id.encode("utf-8"),
                    )

                    logger.info(
                        "Sent image analysis result",
                        device_id=result.device_id,
                        output_topic=self.output_topic,
                        has_caption=bool(result.caption),
                        objects_count=len(result.detected_objects),
                        ocr_blocks_count=len(result.ocr_blocks),
                        processing_time_ms=result.processing_time_ms,
                    )

                    # Commit offset after successful processing
                    await self.consumer.commit()
                else:
                    logger.warning(
                        "Message processing failed",
                        topic=msg.topic,
                        partition=msg.partition,
                        offset=msg.offset,
                        error=result.error if result else "Unknown error",
                    )

                    # Still send error result to output topic for tracking
                    if result:
                        await self.producer.send_and_wait(
                            self.output_topic,
                            value=result.model_dump(mode="json"),
                            key=result.device_id.encode("utf-8"),
                        )

                    # Commit offset to avoid reprocessing
                    await self.consumer.commit()

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

    async def start_consuming(self) -> None:
        """Start consuming messages."""
        await self.start()

        try:
            await self.consume_messages()
        finally:
            await self.stop()
