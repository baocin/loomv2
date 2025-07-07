"""Kafka consumer for processing VAD-filtered audio."""

import asyncio
import json
import time
from collections import defaultdict

import asyncpg
import psutil
import structlog
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.errors import KafkaError
from loom_common.kafka.activity_logger import ConsumerActivityLogger
from loom_common.kafka.consumer_config_loader import KafkaConsumerConfigLoader

from app.config import settings
from app.kyutai_streaming_processor import KyutaiStreamingProcessor
from app.models import AudioChunk, TranscribedText

logger = structlog.get_logger()


class KafkaConsumer(ConsumerActivityLogger):
    """Consumes VAD-filtered audio from Kafka and produces transcripts."""

    def __init__(self):
        # Initialize activity logger
        super().__init__(service_name="kyutai-stt")

        self.consumer: AIOKafkaConsumer | None = None
        self.producer: AIOKafkaProducer | None = None
        self.asr_processor = KyutaiStreamingProcessor()
        self.db_pool: asyncpg.Pool | None = None
        self.config_loader: KafkaConsumerConfigLoader | None = None
        self.running = False
        self._consumer_task = None
        self._messages_processed = 0
        self._last_metrics_time = time.time()
        self._metrics_interval = 60.0  # Record metrics every minute

        # Audio accumulation buffers
        self._audio_buffers: dict[str, list[AudioChunk]] = defaultdict(list)
        self._buffer_timestamps: dict[str, float] = {}
        self._min_chunks_for_processing = settings.min_chunks_for_processing
        self._max_buffer_duration_ms = settings.max_buffer_duration_ms
        self._buffer_timeout_seconds = settings.buffer_timeout_seconds

    async def start(self):
        """Start the Kafka consumer and producer."""
        try:
            # ASR processor will lazy-load on first use

            # Create database pool
            self.db_pool = await asyncpg.create_pool(
                settings.database_url,
                min_size=settings.database_pool_min_size,
                max_size=settings.database_pool_max_size,
            )

            # Create config loader
            self.config_loader = KafkaConsumerConfigLoader(self.db_pool)

            # Create consumer with basic configuration (avoiding config loader issue)
            self.consumer = AIOKafkaConsumer(
                settings.kafka_input_topic,
                bootstrap_servers=settings.kafka_bootstrap_servers,
                group_id=settings.kafka_consumer_group,
                auto_offset_reset="latest",
                enable_auto_commit=False,
                max_poll_records=settings.kafka_max_poll_records,
                session_timeout_ms=settings.kafka_session_timeout_ms,
                heartbeat_interval_ms=settings.kafka_heartbeat_interval_ms,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            )

            # Create producer
            self.producer = AIOKafkaProducer(
                bootstrap_servers=settings.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                compression_type="gzip",  # Changed from lz4 to gzip to avoid dependency issues
                acks="all",
            )

            # Start consumer and producer
            await self.consumer.start()
            await self.producer.start()

            # Initialize activity logger
            await self.init_activity_logger()

            logger.info(
                "Kafka consumer and producer started",
                input_topic=settings.kafka_input_topic,
                output_topic=settings.kafka_output_topic,
                consumer_group=settings.kafka_consumer_group,
            )

            # Start consuming
            self.running = True
            self._consumer_task = asyncio.create_task(self._consume())
            self._buffer_processor_task = asyncio.create_task(self._process_buffers_periodically())

        except Exception as e:
            logger.error("Failed to start Kafka consumer", error=str(e))
            raise

    async def stop(self):
        """Stop the Kafka consumer and producer."""
        self.running = False

        # Process any remaining buffers before shutting down
        await self._process_all_buffers()

        if self._consumer_task:
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass

        if hasattr(self, "_buffer_processor_task") and self._buffer_processor_task:
            self._buffer_processor_task.cancel()
            try:
                await self._buffer_processor_task
            except asyncio.CancelledError:
                pass

        if self.consumer:
            await self.consumer.stop()
            logger.info("Kafka consumer stopped")

        if self.producer:
            await self.producer.stop()
            logger.info("Kafka producer stopped")

        if self.db_pool:
            await self.db_pool.close()
            logger.info("Database pool closed")

        # Close activity logger
        await self.close_activity_logger()

    async def _consume(self):
        """Main consumer loop."""
        logger.info("Starting consumer loop")

        while self.running:
            try:
                # Fetch messages
                async for msg in self.consumer:
                    if not self.running:
                        break

                    try:
                        # Log consumption
                        await self.log_consumption(msg)

                        # Parse message
                        audio_chunk = AudioChunk(**msg.value)

                        logger.info(
                            "Received raw audio chunk for accumulation",
                            chunk_id=audio_chunk.get_chunk_id(),
                            device_id=audio_chunk.device_id,
                            sequence_number=getattr(audio_chunk, "sequence_number", None),
                            duration_ms=audio_chunk.get_duration_ms(),
                            sample_rate=getattr(audio_chunk, "sample_rate", None),
                            file_id=getattr(audio_chunk, "file_id", None),
                            topic=msg.topic,
                            partition=msg.partition,
                            offset=msg.offset,
                        )

                        # Add chunk to buffer for this device
                        device_id = audio_chunk.device_id
                        self._audio_buffers[device_id].append(audio_chunk)
                        self._buffer_timestamps[device_id] = time.time()

                        # Check if we should process this buffer
                        buffer_duration_ms = sum(chunk.get_duration_ms() for chunk in self._audio_buffers[device_id])
                        buffer_size = len(self._audio_buffers[device_id])

                        logger.debug(
                            "Audio buffer status",
                            device_id=device_id,
                            buffer_size=buffer_size,
                            total_duration_ms=buffer_duration_ms,
                            min_chunks_required=self._min_chunks_for_processing,
                            max_duration_ms=self._max_buffer_duration_ms,
                        )

                        # Process if we have enough chunks or reached max duration
                        if (
                            buffer_size >= self._min_chunks_for_processing
                            or buffer_duration_ms >= self._max_buffer_duration_ms
                        ):
                            await self._process_device_buffer(device_id)

                        # Commit offset after adding to buffer
                        await self.consumer.commit()

                    except Exception as e:
                        logger.error(
                            "Failed to process STT message",
                            error=str(e),
                            error_type=type(e).__name__,
                            topic=msg.topic,
                            partition=msg.partition,
                            offset=msg.offset,
                            message_size=len(str(msg.value)) if msg.value else 0,
                        )
                        continue

            except asyncio.CancelledError:
                logger.info("Consumer loop cancelled")
                break
            except KafkaError as e:
                logger.error("Kafka error in consumer loop", error=str(e))
                await asyncio.sleep(5)  # Wait before retrying
            except Exception as e:
                logger.error("Unexpected error in consumer loop", error=str(e))
                await asyncio.sleep(5)  # Wait before retrying

    async def _send_transcript(self, transcript: TranscribedText):
        """Send transcript to output topic."""
        try:
            # Convert to dict and send
            message_dict = transcript.model_dump(mode="json")

            await self.producer.send_and_wait(
                settings.kafka_output_topic,
                key=transcript.device_id.encode("utf-8"),
                value=message_dict,
            )

            # Log production
            await self.log_production(settings.kafka_output_topic, message_dict, transcript.device_id)

            logger.info(
                "Transcript sent to Kafka",
                chunk_id=getattr(transcript, "chunk_id", None),
                device_id=transcript.device_id,
                word_count=len(transcript.words) if hasattr(transcript, "words") else 0,
                text_preview=(
                    transcript.text[:100] + "..."
                    if hasattr(transcript, "text") and len(transcript.text) > 100
                    else getattr(transcript, "text", "")
                ),
                confidence=getattr(transcript, "confidence", None),
                topic=settings.kafka_output_topic,
            )

        except Exception as e:
            logger.error(
                "Failed to send transcript to Kafka",
                chunk_id=getattr(transcript, "chunk_id", None),
                device_id=transcript.device_id,
                error=str(e),
                error_type=type(e).__name__,
                topic=settings.kafka_output_topic,
            )
            raise

    async def _maybe_record_metrics(self):
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
                    service_name=settings.service_name,
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
                                service_name=settings.service_name,
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

    async def _process_buffers_periodically(self):
        """Periodically check and process buffers that have timed out."""
        while self.running:
            try:
                await asyncio.sleep(1.0)  # Check every second

                current_time = time.time()
                devices_to_process = []

                # Check which buffers have timed out
                for device_id, last_update in list(self._buffer_timestamps.items()):
                    if current_time - last_update > self._buffer_timeout_seconds:
                        if self._audio_buffers[device_id]:
                            devices_to_process.append(device_id)

                # Process timed out buffers
                for device_id in devices_to_process:
                    logger.info(
                        "Processing timed out buffer",
                        device_id=device_id,
                        buffer_size=len(self._audio_buffers[device_id]),
                        timeout_seconds=self._buffer_timeout_seconds,
                    )
                    await self._process_device_buffer(device_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in buffer processor", error=str(e))
                await asyncio.sleep(1.0)

    async def _process_all_buffers(self):
        """Process all remaining buffers (used during shutdown)."""
        for device_id in list(self._audio_buffers.keys()):
            if self._audio_buffers[device_id]:
                await self._process_device_buffer(device_id)

    async def _process_device_buffer(self, device_id: str):
        """Process accumulated audio chunks for a device."""
        chunks = self._audio_buffers[device_id]
        if not chunks:
            return

        try:
            # Clear the buffer first
            self._audio_buffers[device_id] = []
            del self._buffer_timestamps[device_id]

            # Combine chunks into a single AudioChunk
            combined_chunk = self._combine_audio_chunks(chunks)

            logger.info(
                "Processing combined audio buffer",
                device_id=device_id,
                chunk_count=len(chunks),
                total_duration_ms=combined_chunk.get_duration_ms(),
                combined_chunk_id=combined_chunk.get_chunk_id(),
            )

            # Process the combined audio
            asr_start = time.time()
            words = await asyncio.get_event_loop().run_in_executor(
                None, self.asr_processor.process_audio_chunk, combined_chunk
            )
            asr_duration = time.time() - asr_start

            # Create TranscribedText from words
            if words:
                transcribed = TranscribedText(
                    chunk_id=combined_chunk.get_chunk_id(),
                    device_id=combined_chunk.device_id,
                    recorded_at=combined_chunk.recorded_at,
                    timestamp=combined_chunk.timestamp,
                    words=words,
                    text=" ".join(w.word for w in words),
                    processing_time_ms=asr_duration * 1000,
                    model_version="openai/whisper-large-v3",
                )

                logger.info(
                    "ASR processing completed for combined chunks",
                    device_id=device_id,
                    chunk_count=len(chunks),
                    word_count=len(words),
                    text_length=len(transcribed.text),
                    asr_processing_time_ms=round(asr_duration * 1000, 2),
                    input_duration_ms=combined_chunk.get_duration_ms(),
                )

                # Send to output topic
                await self._send_transcript(transcribed)
                self._messages_processed += len(chunks)

                # Record metrics periodically
                await self._maybe_record_metrics()
            else:
                logger.warning(
                    "ASR processing returned no results for combined chunks",
                    device_id=device_id,
                    chunk_count=len(chunks),
                    asr_processing_time_ms=round(asr_duration * 1000, 2),
                )

        except Exception as e:
            logger.error(
                "Failed to process audio buffer",
                device_id=device_id,
                chunk_count=len(chunks),
                error=str(e),
                error_type=type(e).__name__,
            )

    def _combine_audio_chunks(self, chunks: list[AudioChunk]) -> AudioChunk:
        """Combine multiple audio chunks into a single chunk."""
        if not chunks:
            raise ValueError("No chunks to combine")

        if len(chunks) == 1:
            return chunks[0]

        # Use the first chunk as template
        first_chunk = chunks[0]

        # Decode all audio data
        import base64

        import numpy as np

        audio_arrays = []
        total_duration_ms = 0

        for chunk in chunks:
            audio_base64 = chunk.get_audio_data()
            audio_bytes = base64.b64decode(audio_base64)

            # Convert to numpy array based on format
            if chunk.format == "wav":
                import io

                import soundfile as sf

                audio_np, _ = sf.read(io.BytesIO(audio_bytes))
            else:
                # Assume raw PCM data
                audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0

            audio_arrays.append(audio_np)
            total_duration_ms += chunk.get_duration_ms()

        # Concatenate all audio
        combined_audio = np.concatenate(audio_arrays)

        # Convert back to PCM bytes
        combined_bytes = (combined_audio * 32768.0).astype(np.int16).tobytes()
        combined_base64 = base64.b64encode(combined_bytes).decode("utf-8")

        # Create combined chunk
        combined_chunk = AudioChunk(
            device_id=first_chunk.device_id,
            recorded_at=first_chunk.recorded_at,
            timestamp=first_chunk.timestamp,
            data=combined_base64,
            sample_rate=first_chunk.sample_rate,
            channels=first_chunk.channels,
            format="pcm",  # We're outputting raw PCM
            duration_ms=total_duration_ms,
            chunk_id=f"combined_{first_chunk.get_chunk_id()}_{len(chunks)}",
        )

        return combined_chunk
