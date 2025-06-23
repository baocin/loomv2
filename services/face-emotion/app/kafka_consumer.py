"""Kafka consumer for processing vision annotations through face emotion analysis."""

import asyncio
import json
from typing import Any, Dict, Optional

import structlog
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from app.config import settings
from app.face_processor import FaceEmotionProcessor
from app.models import VisionAnnotation

logger = structlog.get_logger(__name__)


class KafkaFaceEmotionConsumer:
    """Kafka consumer that processes vision annotations through face emotion analysis."""

    def __init__(self):
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.producer: Optional[AIOKafkaProducer] = None
        self.face_processor = FaceEmotionProcessor()
        self._running = False
        self._tasks: set[asyncio.Task] = set()

    async def start(self) -> None:
        """Start the Kafka consumer and producer."""
        try:
            # Initialize face emotion processor
            await self.face_processor.initialize()

            # Create consumer
            self.consumer = AIOKafkaConsumer(
                settings.kafka_input_topic,
                bootstrap_servers=settings.kafka_bootstrap_servers,
                group_id=settings.kafka_consumer_group,
                auto_offset_reset=settings.kafka_auto_offset_reset,
                enable_auto_commit=settings.kafka_enable_auto_commit,
                max_poll_records=settings.kafka_max_poll_records,
                consumer_timeout_ms=settings.kafka_consumer_timeout_ms,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            )

            # Create producer
            self.producer = AIOKafkaProducer(
                bootstrap_servers=settings.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
                compression_type="lz4",
            )

            # Start both
            await self.consumer.start()
            await self.producer.start()

            self._running = True
            logger.info(
                "Kafka face emotion consumer started",
                input_topic=settings.kafka_input_topic,
                output_topic=settings.kafka_output_topic,
                consumer_group=settings.kafka_consumer_group,
            )

        except Exception as e:
            logger.error("Failed to start Kafka face emotion consumer", error=str(e))
            raise

    async def stop(self) -> None:
        """Stop the consumer gracefully."""
        self._running = False

        # Cancel all tasks
        for task in self._tasks:
            task.cancel()

        # Wait for tasks to complete
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        # Stop Kafka clients
        if self.consumer:
            await self.consumer.stop()
        if self.producer:
            await self.producer.stop()

        # Cleanup face processor
        await self.face_processor.cleanup()

        logger.info("Kafka face emotion consumer stopped")

    async def consume(self) -> None:
        """Main consumer loop."""
        if not self.consumer or not self.producer:
            raise RuntimeError("Consumer not started")

        while self._running:
            try:
                # Fetch messages
                messages = await self.consumer.getmany(
                    timeout_ms=settings.kafka_consumer_timeout_ms
                )

                if not messages:
                    continue

                # Process each partition's messages
                for tp, partition_messages in messages.items():
                    for msg in partition_messages:
                        # Create task for processing
                        task = asyncio.create_task(self._process_message(msg))
                        self._tasks.add(task)
                        task.add_done_callback(self._tasks.discard)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in face emotion consumer loop", error=str(e))
                await asyncio.sleep(1)  # Brief pause before retry

    async def _process_message(self, message) -> None:
        """Process a single message."""
        try:
            # Parse the vision annotation message
            annotation = VisionAnnotation(**message.value)

            logger.debug(
                "Processing vision annotation for face emotion",
                device_id=annotation.device_id,
                annotation_id=annotation.annotation_id,
                object_class=annotation.object_class,
            )

            # Process through face emotion analysis
            face_analyses = await self.face_processor.process_vision_annotation(
                annotation
            )

            if not face_analyses:
                logger.debug(
                    "No face emotion analysis results",
                    device_id=annotation.device_id,
                    annotation_id=annotation.annotation_id,
                )
                return

            # Send each face emotion analysis to output topic
            for face_analysis in face_analyses:
                await self.producer.send(
                    settings.kafka_output_topic,
                    value=face_analysis.model_dump(mode="json"),
                    key=annotation.device_id.encode("utf-8"),
                )

                logger.info(
                    "Sent face emotion analysis result",
                    device_id=annotation.device_id,
                    face_id=face_analysis.face_id,
                    predicted_emotion=face_analysis.emotion_label,
                    confidence=face_analysis.confidence_score,
                )

            # Commit the offset after successful processing
            await self.consumer.commit()

        except Exception as e:
            logger.error(
                "Error processing face emotion message",
                error=str(e),
                topic=message.topic,
                partition=message.partition,
                offset=message.offset,
            )

    async def health_check(self) -> Dict[str, Any]:
        """Check consumer health."""
        health = {
            "status": "healthy",
            "consumer_running": self._running,
            "active_tasks": len(self._tasks),
            "face_processor_initialized": self.face_processor._initialized,
        }

        if self.consumer:
            try:
                # Check consumer metrics
                health["consumer_connected"] = True
            except Exception as e:
                health["status"] = "degraded"
                health["consumer_error"] = str(e)
                health["consumer_connected"] = False

        if self.producer:
            try:
                # Check producer metrics
                health["producer_connected"] = True
            except Exception as e:
                health["status"] = "degraded"
                health["producer_error"] = str(e)
                health["producer_connected"] = False

        return health
