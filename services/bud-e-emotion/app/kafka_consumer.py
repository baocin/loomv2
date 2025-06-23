"""Kafka consumer for processing VAD-filtered audio through emotion analysis."""

import asyncio
import json
from typing import Any, Dict, Optional

import structlog
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from app.config import settings
from app.emotion_processor import EmotionProcessor
from app.models import VADFilteredAudio

logger = structlog.get_logger(__name__)


class KafkaEmotionConsumer:
    """Kafka consumer that processes VAD-filtered audio through emotion analysis."""

    def __init__(self):
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.producer: Optional[AIOKafkaProducer] = None
        self.emotion_processor = EmotionProcessor()
        self._running = False
        self._tasks: set[asyncio.Task] = set()

    async def start(self) -> None:
        """Start the Kafka consumer and producer."""
        try:
            # Initialize emotion processor
            await self.emotion_processor.initialize()

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
                "Kafka emotion consumer started",
                input_topic=settings.kafka_input_topic,
                output_topic=settings.kafka_output_topic,
                consumer_group=settings.kafka_consumer_group,
            )

        except Exception as e:
            logger.error("Failed to start Kafka emotion consumer", error=str(e))
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

        # Cleanup emotion processor
        await self.emotion_processor.cleanup()

        logger.info("Kafka emotion consumer stopped")

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
                logger.error("Error in emotion consumer loop", error=str(e))
                await asyncio.sleep(1)  # Brief pause before retry

    async def _process_message(self, message) -> None:
        """Process a single message."""
        try:
            # Parse the VAD-filtered audio message
            vad_audio = VADFilteredAudio(**message.value)

            logger.debug(
                "Processing VAD audio for emotion",
                device_id=vad_audio.device_id,
                duration_ms=vad_audio.duration_ms,
                vad_confidence=vad_audio.vad_confidence,
            )

            # Process through emotion analysis
            emotion_analysis = await self.emotion_processor.process_audio(vad_audio)

            if emotion_analysis is None:
                logger.warning(
                    "No emotion analysis result",
                    device_id=vad_audio.device_id,
                )
                return

            # Send to output topic
            await self.producer.send(
                settings.kafka_output_topic,
                value=emotion_analysis.model_dump(mode="json"),
                key=vad_audio.device_id.encode("utf-8"),
            )

            logger.info(
                "Sent emotion analysis result",
                device_id=vad_audio.device_id,
                predicted_emotion=emotion_analysis.predicted_emotion,
                confidence=emotion_analysis.confidence_score,
                valence=emotion_analysis.valence_score,
                arousal=emotion_analysis.arousal_score,
            )

            # Commit the offset after successful processing
            await self.consumer.commit()

        except Exception as e:
            logger.error(
                "Error processing emotion message",
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
            "emotion_processor_initialized": self.emotion_processor._initialized,
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
