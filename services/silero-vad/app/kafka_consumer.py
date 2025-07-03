"""Kafka consumer for processing audio chunks."""

import asyncio
import json
import time
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
        self._messages_processed = 0
        self._last_commit_time = time.time()
        self._commit_interval = 5.0  # Commit every 5 seconds
        self._commit_batch_size = 100  # Or every 100 messages

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
                session_timeout_ms=settings.kafka_session_timeout_ms,
                heartbeat_interval_ms=settings.kafka_heartbeat_interval_ms,
                max_poll_interval_ms=settings.kafka_max_poll_interval_ms,
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

        # Commit any pending offsets before stopping
        if self.consumer and self._messages_processed > 0:
            try:
                await self.consumer.commit()
                logger.info("Final commit before shutdown", messages_processed=self._messages_processed)
            except Exception as e:
                logger.error("Failed to commit final offsets", error=str(e))

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
                
                # Check if we need to commit based on time
                await self._maybe_commit()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in consumer loop", error=str(e))
                await asyncio.sleep(1)  # Brief pause before retry

    async def _maybe_commit(self) -> None:
        """Commit offsets if batch size or time interval is reached."""
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

    async def _process_message_with_retry(self, message) -> None:
        """Process a message with retry logic and DLQ handling."""
        message_key = f"{message.topic}:{message.partition}:{message.offset}"
        retry_count = self._message_retry_counts.get(message_key, 0)
        max_retries = 3  # Maximum number of retries

        # Use a loop instead of recursion to avoid stack overflow
        while retry_count <= max_retries:
            try:
                await self._process_message(message)

                # Success - remove from retry tracking
                self._message_retry_counts.pop(message_key, None)
                self._messages_processed += 1
                
                # Batch commit logic
                await self._maybe_commit()
                return  # Exit the loop on success

            except Exception as e:
                logger.error(
                    "Message processing failed",
                    error=str(e),
                    error_type=type(e).__name__,
                    topic=message.topic,
                    partition=message.partition,
                    offset=message.offset,
                    retry_count=retry_count,
                    message_key=message_key,
                )

                # Check if we should retry or send to DLQ
                if self.dlq_handler and await self.dlq_handler.should_retry(e, retry_count) and retry_count < max_retries:
                    # Increment retry count and retry after delay
                    retry_count += 1
                    self._message_retry_counts[message_key] = retry_count
                    delay = self.dlq_handler.get_retry_delay(retry_count - 1)

                    logger.info(
                        "Scheduling message retry",
                        retry_count=retry_count,
                        max_retries=max_retries,
                        delay_seconds=delay,
                        topic=message.topic,
                        offset=message.offset,
                    )

                    await asyncio.sleep(delay)
                    # Continue to next iteration of the loop

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

                    # Clean up retry tracking and force commit to skip the problematic message
                    self._message_retry_counts.pop(message_key, None)
                    await self.consumer.commit()  # Force commit for DLQ messages
                    return  # Exit the loop after sending to DLQ

    async def _process_message(self, message) -> None:
        """Process a single message."""
        try:
            # Parse the message
            audio_chunk = AudioChunk(**message.value)

            logger.info(
                "Processing audio chunk",
                device_id=audio_chunk.device_id,
                sample_rate=audio_chunk.sample_rate,
                channels=audio_chunk.channels,
                duration_ms=audio_chunk.duration_ms,
                message_id=audio_chunk.message_id,
                trace_id=audio_chunk.trace_id,
                audio_data_size=len(audio_chunk.data),
                topic=message.topic,
                partition=message.partition,
                offset=message.offset,
            )

            # Decode audio data
            audio_bytes = audio_chunk.decode_audio()

            # Process through VAD
            vad_start = time.time()
            segments = await self.vad_processor.process_audio(
                audio_bytes, audio_chunk.sample_rate, audio_chunk.channels
            )
            vad_duration = time.time() - vad_start
            
            logger.info(
                "VAD processing completed",
                device_id=audio_chunk.device_id,
                segments_found=len(segments),
                vad_processing_time_ms=round(vad_duration * 1000, 2),
                input_duration_ms=audio_chunk.duration_ms,
                vad_threshold=settings.vad_threshold,
            )

            # Send each speech segment to output topic
            for idx, segment in enumerate(segments):
                filtered_audio = VADFilteredAudio(
                    device_id=audio_chunk.device_id,
                    recorded_at=audio_chunk.recorded_at,
                    timestamp=audio_chunk.timestamp,
                    message_id=f"{audio_chunk.message_id or 'vad'}_segment_{idx}",
                    trace_id=audio_chunk.trace_id,
                    services_encountered=(audio_chunk.services_encountered or []) + ["silero-vad"],
                    content_hash=audio_chunk.content_hash,
                    data="",  # Will be set below
                    sample_rate=segment["sample_rate"],
                    channels=1,  # Always mono after processing
                    format="wav",
                    duration_ms=int(segment["duration_ms"]),
                    file_id=audio_chunk.file_id,
                    start_ms=segment["start_ms"],
                    end_ms=segment["end_ms"],
                    confidence=segment["confidence"],
                    vad_threshold=settings.vad_threshold,
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
                    "VAD segment sent to Kafka",
                    device_id=audio_chunk.device_id,
                    segment_index=idx,
                    duration_ms=segment["duration_ms"],
                    confidence=segment["confidence"],
                    start_ms=segment["start_ms"],
                    end_ms=segment["end_ms"],
                    output_topic=settings.kafka_output_topic,
                    message_id=filtered_audio.message_id,
                    trace_id=audio_chunk.trace_id,
                )

        except Exception as e:
            logger.error(
                "Error processing message",
                error=str(e),
                error_type=type(e).__name__,
                topic=message.topic,
                partition=message.partition,
                offset=message.offset,
                message_size=len(str(message.value)) if message.value else 0,
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
