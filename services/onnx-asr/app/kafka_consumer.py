"""Kafka consumer for ONNX-ASR service."""

import asyncio
import json
import time
from typing import List, Optional

import structlog
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from prometheus_client import Counter

from app.config import settings
from app.models import AudioChunk, Transcript
from app.onnx_processor import ONNXASRProcessor

logger = structlog.get_logger()

# Metrics
chunks_consumed = Counter(
    "onnx_asr_chunks_consumed_total", "Total number of audio chunks consumed from Kafka"
)
chunks_processed = Counter(
    "onnx_asr_chunks_processed_total",
    "Total number of audio chunks successfully processed",
)
chunks_failed = Counter(
    "onnx_asr_chunks_failed_total",
    "Total number of audio chunks that failed processing",
)
transcripts_produced = Counter(
    "onnx_asr_transcripts_produced_total", "Total number of transcripts sent to Kafka"
)


class KafkaConsumer:
    """Kafka consumer that processes audio chunks through ONNX ASR."""

    def __init__(self):
        """Initialize consumer."""
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.producer: Optional[AIOKafkaProducer] = None
        self.processor: Optional[ONNXASRProcessor] = None
        self.running = False
        self.consumer_task: Optional[asyncio.Task] = None

        # Batching
        self.batch_queue: List[tuple] = []  # (message, audio_chunk)
        self.batch_lock = asyncio.Lock()
        self.last_batch_time = time.time()

    async def start(self):
        """Start the Kafka consumer and producer."""
        try:
            logger.info(
                "Starting Kafka consumer",
                bootstrap_servers=settings.kafka_bootstrap_servers,
                input_topic=settings.kafka_input_topic,
                output_topic=settings.kafka_output_topic,
                consumer_group=settings.kafka_consumer_group,
            )

            # Initialize processor
            self.processor = ONNXASRProcessor()
            await self.processor.initialize()

            # Create consumer
            self.consumer = AIOKafkaConsumer(
                settings.kafka_input_topic,
                bootstrap_servers=settings.kafka_bootstrap_servers,
                group_id=settings.kafka_consumer_group,
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                auto_offset_reset="earliest",
                enable_auto_commit=False,
                max_poll_records=settings.kafka_max_batch_size,
            )

            # Create producer
            self.producer = AIOKafkaProducer(
                bootstrap_servers=settings.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                compression_type="lz4",
                max_batch_size=16384,
                linger_ms=100,
            )

            # Start consumer and producer
            await self.consumer.start()
            await self.producer.start()

            # Start processing
            self.running = True
            self.consumer_task = asyncio.create_task(self._consume_loop())

            # Start batch processor if batching is enabled
            if settings.enable_batching:
                asyncio.create_task(self._batch_processor())

            logger.info("Kafka consumer started successfully")

        except Exception as e:
            logger.error("Failed to start Kafka consumer", error=str(e))
            await self.stop()
            raise

    async def stop(self):
        """Stop the Kafka consumer and producer."""
        logger.info("Stopping Kafka consumer")
        self.running = False

        # Cancel consumer task
        if self.consumer_task:
            self.consumer_task.cancel()
            try:
                await self.consumer_task
            except asyncio.CancelledError:
                pass

        # Process remaining batch
        if self.batch_queue:
            await self._process_batch()

        # Stop consumer and producer
        if self.consumer:
            await self.consumer.stop()
        if self.producer:
            await self.producer.stop()

        logger.info("Kafka consumer stopped")

    async def _consume_loop(self):
        """Main consumer loop."""
        logger.info("Starting consumer loop")

        try:
            async for msg in self.consumer:
                try:
                    chunks_consumed.inc()

                    # Parse message
                    try:
                        chunk = AudioChunk(**msg.value)
                    except Exception as e:
                        logger.error(
                            "Failed to parse audio chunk",
                            error=str(e),
                            topic=msg.topic,
                            partition=msg.partition,
                            offset=msg.offset,
                        )
                        chunks_failed.inc()
                        await self.consumer.commit()
                        continue

                    # Process based on batching settings
                    if settings.enable_batching:
                        async with self.batch_lock:
                            self.batch_queue.append((msg, chunk))

                            # Check if batch is ready
                            if len(self.batch_queue) >= settings.max_batch_size:
                                await self._process_batch()
                    else:
                        # Process immediately
                        await self._process_single(msg, chunk)

                except Exception as e:
                    logger.error(
                        "Error processing message",
                        error=str(e),
                        topic=msg.topic,
                        partition=msg.partition,
                        offset=msg.offset,
                    )
                    chunks_failed.inc()
                    # Commit to avoid reprocessing
                    await self.consumer.commit()

        except asyncio.CancelledError:
            logger.info("Consumer loop cancelled")
            raise
        except Exception as e:
            logger.error("Consumer loop failed", error=str(e))
            raise

    async def _batch_processor(self):
        """Process batches periodically based on timeout."""
        logger.info(
            "Starting batch processor",
            batch_timeout=settings.batch_timeout_seconds,
        )

        while self.running:
            try:
                await asyncio.sleep(1.0)  # Check every second

                async with self.batch_lock:
                    if self.batch_queue:
                        time_since_last = time.time() - self.last_batch_time
                        if time_since_last >= settings.batch_timeout_seconds:
                            await self._process_batch()

            except Exception as e:
                logger.error("Batch processor error", error=str(e))

    async def _process_batch(self):
        """Process a batch of audio chunks."""
        if not self.batch_queue:
            return

        batch_size = len(self.batch_queue)
        logger.info(f"Processing batch of {batch_size} audio chunks")

        # Extract chunks
        batch = self.batch_queue.copy()
        self.batch_queue.clear()
        self.last_batch_time = time.time()

        # Process chunks
        chunks = [item[1] for item in batch]
        transcripts = await self.processor.process_batch(chunks)

        # Send results and commit offsets
        for i, (msg, chunk) in enumerate(batch):
            transcript = transcripts[i] if i < len(transcripts) else None

            if transcript:
                await self._send_transcript(transcript)
                chunks_processed.inc()
            else:
                chunks_failed.inc()

            # Commit offset
            await self.consumer.commit({msg.topic_partition: msg.offset + 1})

    async def _process_single(self, msg, chunk: AudioChunk):
        """Process a single audio chunk."""
        # Process audio
        transcript = await self.processor.process_audio_chunk(chunk)

        if transcript:
            # Send to output topic
            await self._send_transcript(transcript)
            chunks_processed.inc()
        else:
            chunks_failed.inc()

        # Commit offset
        await self.consumer.commit()

    async def _send_transcript(self, transcript: Transcript):
        """Send transcript to Kafka output topic."""
        try:
            # Convert to dict
            transcript_dict = transcript.model_dump()

            # Send to Kafka
            await self.producer.send_and_wait(
                settings.kafka_output_topic,
                value=transcript_dict,
                key=(
                    transcript.device_id.encode("utf-8")
                    if transcript.device_id
                    else None
                ),
            )

            transcripts_produced.inc()

            logger.debug(
                "Sent transcript to Kafka",
                device_id=transcript.device_id,
                text_length=len(transcript.text),
                num_words=len(transcript.words),
            )

        except Exception as e:
            logger.error(
                "Failed to send transcript to Kafka",
                error=str(e),
                device_id=transcript.device_id,
            )
            raise
