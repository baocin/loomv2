"""Main VAD processor logic."""

import json
import time
from datetime import datetime

import asyncpg
import structlog
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.errors import KafkaError
from prometheus_client import Counter, Gauge, Histogram

from .config import settings
from .models import AudioChunk, VADResult
from .vad_model import SileroVAD

logger = structlog.get_logger(__name__)

# Prometheus metrics
audio_chunks_processed = Counter(
    "vad_audio_chunks_processed_total",
    "Total number of audio chunks processed",
    ["status"],
)
speech_segments_found = Counter(
    "vad_speech_segments_found_total", "Total number of speech segments found"
)
processing_duration = Histogram(
    "vad_processing_duration_seconds", "Time spent processing audio chunks"
)
kafka_lag = Gauge("vad_kafka_consumer_lag", "Kafka consumer lag in messages")


class VADProcessor:
    """Voice Activity Detection processor."""

    def __init__(self):
        self.consumer: AIOKafkaConsumer | None = None
        self.producer: AIOKafkaProducer | None = None
        self.db_pool: asyncpg.Pool | None = None
        self.vad_model: SileroVAD | None = None
        self._running = False

    async def start(self):
        """Start the VAD processor."""
        logger.info("Starting VAD processor...")

        # Initialize VAD model
        self.vad_model = SileroVAD(threshold=settings.vad_threshold)

        # Initialize database connection pool
        self.db_pool = await asyncpg.create_pool(
            settings.database_url, min_size=2, max_size=10
        )

        # Initialize Kafka consumer
        self.consumer = AIOKafkaConsumer(
            settings.kafka_input_topic,
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id=settings.kafka_consumer_group,
            auto_offset_reset="latest",
            enable_auto_commit=False,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )

        # Initialize Kafka producer
        self.producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            compression_type="lz4",
        )

        await self.consumer.start()
        await self.producer.start()

        self._running = True
        logger.info("VAD processor started successfully")

    async def stop(self):
        """Stop the VAD processor."""
        logger.info("Stopping VAD processor...")
        self._running = False

        if self.consumer:
            await self.consumer.stop()
        if self.producer:
            await self.producer.stop()
        if self.db_pool:
            await self.db_pool.close()

        logger.info("VAD processor stopped")

    async def process_messages(self):
        """Main message processing loop."""
        try:
            async for msg in self.consumer:
                if not self._running:
                    break

                start_time = time.time()

                try:
                    # Parse audio chunk
                    audio_chunk = AudioChunk(**msg.value)

                    # Process with VAD
                    segments = await self._process_audio_chunk(audio_chunk)

                    # Send results to Kafka and database
                    for vad_result in segments:
                        await self._send_result(vad_result)
                        await self._save_to_database(vad_result)

                    # Commit offset
                    await self.consumer.commit()

                    # Update metrics
                    audio_chunks_processed.labels(status="success").inc()
                    speech_segments_found.inc(len(segments))
                    processing_duration.observe(time.time() - start_time)

                    logger.info(
                        "Processed audio chunk",
                        device_id=audio_chunk.device_id,
                        chunk_number=audio_chunk.chunk_number,
                        segments_found=len(segments),
                    )

                except Exception as e:
                    logger.error("Error processing message", error=str(e))
                    audio_chunks_processed.labels(status="error").inc()

        except Exception as e:
            logger.error("Fatal error in processing loop", error=str(e))
            raise

    async def _process_audio_chunk(self, audio_chunk: AudioChunk) -> list[VADResult]:
        """Process audio chunk with VAD model."""
        try:
            # Decode audio
            audio_bytes = audio_chunk.decode_audio()

            # Run VAD
            segments = self.vad_model.process_audio(
                audio_bytes,
                audio_chunk.sample_rate,
                min_speech_duration_ms=settings.vad_min_speech_duration_ms,
                max_speech_duration_ms=settings.vad_max_speech_duration_ms,
                padding_ms=settings.vad_padding_duration_ms,
            )

            # Create VAD results
            results = []
            for vad_segment, segment_audio in segments:
                result = VADResult(
                    device_id=audio_chunk.device_id,
                    timestamp=datetime.utcnow(),
                    source_timestamp=audio_chunk.timestamp,
                    has_speech=True,
                    confidence=vad_segment.confidence,
                    audio_segment="",  # Will be set by encode_audio
                    segment_start_ms=vad_segment.start_ms,
                    segment_duration_ms=vad_segment.end_ms - vad_segment.start_ms,
                    processing_version=settings.service_version,
                    metadata={
                        "source_chunk_number": audio_chunk.chunk_number,
                        "source_format": audio_chunk.format,
                        "source_sample_rate": audio_chunk.sample_rate,
                    },
                )
                result.encode_audio(segment_audio)
                results.append(result)

            return results

        except Exception as e:
            logger.error("Error in VAD processing", error=str(e))
            raise

    async def _send_result(self, vad_result: VADResult):
        """Send VAD result to Kafka."""
        try:
            await self.producer.send_and_wait(
                settings.kafka_output_topic,
                value=vad_result.model_dump(),
                key=vad_result.device_id.encode("utf-8"),
            )
        except KafkaError as e:
            logger.error("Error sending to Kafka", error=str(e))
            raise

    async def _save_to_database(self, vad_result: VADResult):
        """Save VAD result to TimescaleDB."""
        query = """
            INSERT INTO media_audio_vad_filtered (
                device_id, timestamp, schema_version, source_timestamp,
                has_speech, confidence, audio_segment, segment_start_ms,
                segment_duration_ms, processing_model, processing_version, metadata
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        """

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                query,
                vad_result.device_id,
                vad_result.timestamp,
                vad_result.schema_version,
                vad_result.source_timestamp,
                vad_result.has_speech,
                vad_result.confidence,
                vad_result.audio_segment,
                vad_result.segment_start_ms,
                vad_result.segment_duration_ms,
                vad_result.processing_model,
                vad_result.processing_version,
                json.dumps(vad_result.metadata) if vad_result.metadata else None,
            )
