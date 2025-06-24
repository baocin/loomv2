"""Kafka consumer for processing audio chunks."""

import asyncio
import json
from typing import Any

import structlog
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from app.config import settings
from app.models import AudioChunk, VADFilteredAudio
from app.vad_processor import VADProcessor

logger = structlog.get_logger(__name__)


class KafkaVADConsumer:
    """Kafka consumer that processes audio chunks through VAD."""

    def __init__(self):
        self.consumer: AIOKafkaConsumer | None = None
        self.producer: AIOKafkaProducer | None = None
        self.vad_processor = VADProcessor()
        self._running = False
        self._tasks: set[asyncio.Task] = set()

    async def start(self) -> None:
        """Start the Kafka consumer and producer."""
        try:
            # Initialize VAD processor
            await self.vad_processor.initialize()

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
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                compression_type="gzip",
            )

            # Start both
            await self.consumer.start()
            await self.producer.start()

            self._running = True
            logger.info(
                "Kafka consumer started",
                input_topic=settings.kafka_input_topic,
                output_topic=settings.kafka_output_topic,
                consumer_group=settings.kafka_consumer_group,
            )

        except Exception as e:
            logger.error("Failed to start Kafka consumer", error=str(e))
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

        # Cleanup VAD processor
        await self.vad_processor.cleanup()

        logger.info("Kafka consumer stopped")

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
                logger.error("Error in consumer loop", error=str(e))
                await asyncio.sleep(1)  # Brief pause before retry

    async def _process_message(self, message) -> None:
        """Process a single message."""
        try:
            # Parse the message
            audio_chunk = AudioChunk(**message.value)

            logger.debug(
                "Processing audio chunk",
                device_id=audio_chunk.device_id,
                sample_rate=audio_chunk.sample_rate,
                channels=audio_chunk.channels,
            )

            # Decode audio data
            audio_bytes = audio_chunk.decode_audio()

            # Process through VAD
            segments = await self.vad_processor.process_audio(
                audio_bytes, audio_chunk.sample_rate, audio_chunk.channels
            )

            # Send each speech segment to output topic
            for segment in segments:
                filtered_audio = VADFilteredAudio(
                    device_id=audio_chunk.device_id,
                    recorded_at=audio_chunk.recorded_at,
                    metadata={
                        **audio_chunk.metadata,
                        "original_sample_rate": audio_chunk.sample_rate,
                        "original_channels": audio_chunk.channels,
                    },
                    audio_data="",  # Will be set below
                    sample_rate=segment["sample_rate"],
                    channels=1,  # Always mono after processing
                    duration_ms=segment["duration_ms"],
                    format="pcm",
                    vad_confidence=segment["confidence"],
                    speech_start_ms=segment["start_ms"],
                    speech_end_ms=segment["end_ms"],
                )

                # Encode the audio data
                filtered_audio.encode_audio(segment["audio_data"])

                # Send to output topic
                await self.producer.send(
                    settings.kafka_output_topic,
                    value=filtered_audio.model_dump(mode="json"),
                    key=audio_chunk.device_id.encode("utf-8"),
                )

                logger.info(
                    "Sent filtered audio segment",
                    device_id=audio_chunk.device_id,
                    duration_ms=segment["duration_ms"],
                    confidence=segment["confidence"],
                )

            # Commit the offset after successful processing
            await self.consumer.commit()

        except Exception as e:
            logger.error(
                "Error processing message",
                error=str(e),
                topic=message.topic,
                partition=message.partition,
                offset=message.offset,
            )

    async def health_check(self) -> dict[str, Any]:
        """Check consumer health."""
        health = {
            "status": "healthy",
            "consumer_running": self._running,
            "active_tasks": len(self._tasks),
        }

        if self.consumer:
            try:
                # Check consumer metrics
                metrics = await self.consumer.metrics()
                health["consumer_metrics"] = {
                    "records_consumed": metrics.get("records-consumed-total", 0),
                    "bytes_consumed": metrics.get("bytes-consumed-total", 0),
                }
            except Exception as e:
                health["status"] = "degraded"
                health["consumer_error"] = str(e)

        if self.producer:
            try:
                # Check producer metrics
                metrics = await self.producer.metrics()
                health["producer_metrics"] = {
                    "record_sends": metrics.get("record-send-total", 0),
                    "bytes_sent": metrics.get("bytes-sent-total", 0),
                }
            except Exception as e:
                health["status"] = "degraded"
                health["producer_error"] = str(e)

        return health
