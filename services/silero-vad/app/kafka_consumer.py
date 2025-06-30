"""Kafka consumer for processing audio chunks."""

import asyncio
import json
from typing import Any

import structlog
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from app.config import settings
from app.dlq_handler import DLQHandler
from app.models import AudioChunk, VADFilteredAudio
from app.vad_processor import VADProcessor

logger = structlog.get_logger(__name__)


class KafkaVADConsumer:
    """Kafka consumer that processes audio chunks through VAD."""

    def __init__(self):
        self.consumer: AIOKafkaConsumer | None = None
        self.producer: AIOKafkaProducer | None = None
        self.vad_processor = VADProcessor()
        self.dlq_handler: DLQHandler | None = None
        self._running = False
        self._tasks: set[asyncio.Task] = set()
        self._message_retry_counts: dict[str, int] = {}

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

            # Initialize DLQ handler
            self.dlq_handler = DLQHandler(self.producer, "silero-vad")

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
                        # Create task for processing with retry logic
                        task = asyncio.create_task(
                            self._process_message_with_retry(msg)
                        )
                        self._tasks.add(task)
                        task.add_done_callback(self._tasks.discard)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in consumer loop", error=str(e))
                await asyncio.sleep(1)  # Brief pause before retry

    async def _process_message_with_retry(self, message) -> None:
        """Process a message with retry logic and DLQ handling."""
        message_key = f"{message.topic}:{message.partition}:{message.offset}"
        retry_count = self._message_retry_counts.get(message_key, 0)

        try:
            await self._process_message(message)

            # Success - remove from retry tracking and commit
            self._message_retry_counts.pop(message_key, None)
            await self.consumer.commit()

        except Exception as e:
            logger.error(
                "Message processing failed",
                error=str(e),
                topic=message.topic,
                partition=message.partition,
                offset=message.offset,
                retry_count=retry_count,
            )

            # Check if we should retry or send to DLQ
            if self.dlq_handler and await self.dlq_handler.should_retry(e, retry_count):
                # Increment retry count and retry after delay
                self._message_retry_counts[message_key] = retry_count + 1
                delay = self.dlq_handler.get_retry_delay(retry_count)

                logger.info(
                    "Scheduling message retry",
                    retry_count=retry_count + 1,
                    delay_seconds=delay,
                    topic=message.topic,
                    offset=message.offset,
                )

                await asyncio.sleep(delay)
                # Retry the message
                await self._process_message_with_retry(message)

            else:
                # Send to DLQ and commit the offset to skip this message
                if self.dlq_handler:
                    await self.dlq_handler.send_to_dlq(
                        original_message=message.value,
                        source_topic=message.topic,
                        error=e,
                        dlq_topic="dlq.audio.processing",
                        retry_count=retry_count,
                    )

                # Clean up retry tracking and commit to skip the problematic message
                self._message_retry_counts.pop(message_key, None)
                await self.consumer.commit()

    async def _process_message(self, message) -> None:
        """Process a single message."""
        try:
            # Parse the message
            audio_chunk = AudioChunk(**message.value)

            logger.debug(
                "Processing audio chunk",
                device_id=audio_chunk.device_id,
                sample_rate=audio_chunk.data.sample_rate,
                channels=audio_chunk.data.channels,
                duration_ms=audio_chunk.data.duration_ms,
            )

            # Decode audio data
            audio_bytes = audio_chunk.decode_audio()

            # Process through VAD
            segments = await self.vad_processor.process_audio(
                audio_bytes, audio_chunk.data.sample_rate, audio_chunk.data.channels
            )

            # Send each speech segment to output topic
            for idx, segment in enumerate(segments):
                filtered_audio = VADFilteredAudio(
                    timestamp=audio_chunk.timestamp,
                    device_id=audio_chunk.device_id,
                    file_id=audio_chunk.trace_id,  # Use trace_id as file_id
                    chunk_index=idx,
                    audio_data="",  # Will be set below
                    sample_rate=segment["sample_rate"],
                    channels=1,  # Always mono after processing
                    duration_ms=int(segment["duration_ms"]),
                    vad_confidence=segment["confidence"],
                    speech_probability=segment.get("speech_probability", segment["confidence"]),
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

        except Exception as e:
            logger.error(
                "Error processing message",
                error=str(e),
                topic=message.topic,
                partition=message.partition,
                offset=message.offset,
            )
            # Re-raise the exception to be handled by retry logic
            raise

    async def health_check(self) -> dict[str, Any]:
        """Check consumer health."""
        health = {
            "status": "healthy",
            "consumer_running": self._running,
            "active_tasks": len(self._tasks),
        }

        if self.consumer:
            try:
                # Check if consumer is subscribed and has assignment
                health["consumer_subscribed"] = bool(self.consumer.subscription())
                health["consumer_assigned"] = bool(self.consumer.assignment())
            except Exception as e:
                health["status"] = "degraded"
                health["consumer_error"] = str(e)

        if self.producer:
            try:
                # Check if producer is started
                health["producer_started"] = (
                    hasattr(self.producer, "_sender")
                    and self.producer._sender is not None
                )
            except Exception as e:
                health["status"] = "degraded"
                health["producer_error"] = str(e)

        return health
