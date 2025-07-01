"""Kafka consumer for processing VAD-filtered audio."""

import asyncio
import json
import time

import structlog
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.errors import KafkaError

from app.simple_kyutai_processor import SimpleKyutaiProcessor
from app.config import settings
from app.models import AudioChunk, TranscribedText

logger = structlog.get_logger()


class KafkaConsumer:
    """Consumes VAD-filtered audio from Kafka and produces transcripts."""

    def __init__(self):
        self.consumer: AIOKafkaConsumer | None = None
        self.producer: AIOKafkaProducer | None = None
        self.asr_processor = SimpleKyutaiProcessor()
        self.running = False
        self._consumer_task = None

    async def start(self):
        """Start the Kafka consumer and producer."""
        try:
            # Initialize ASR processor
            await self.asr_processor.initialize()

            # Create consumer
            self.consumer = AIOKafkaConsumer(
                settings.kafka_input_topic,
                bootstrap_servers=settings.kafka_bootstrap_servers,
                group_id=settings.kafka_consumer_group,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                auto_offset_reset="latest",
                enable_auto_commit=False,  # Manual commit for better reliability
                session_timeout_ms=settings.kafka_session_timeout_ms,
                heartbeat_interval_ms=settings.kafka_heartbeat_interval_ms,
                max_poll_records=settings.kafka_max_poll_records,
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

            logger.info(
                "Kafka consumer and producer started",
                input_topic=settings.kafka_input_topic,
                output_topic=settings.kafka_output_topic,
                consumer_group=settings.kafka_consumer_group,
            )

            # Start consuming
            self.running = True
            self._consumer_task = asyncio.create_task(self._consume())

        except Exception as e:
            logger.error("Failed to start Kafka consumer", error=str(e))
            raise

    async def stop(self):
        """Stop the Kafka consumer and producer."""
        self.running = False

        if self._consumer_task:
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass

        if self.consumer:
            await self.consumer.stop()
            logger.info("Kafka consumer stopped")

        if self.producer:
            await self.producer.stop()
            logger.info("Kafka producer stopped")

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
                        # Parse message
                        audio_chunk = AudioChunk(**msg.value)

                        logger.info(
                            "Received raw audio chunk for transcription",
                            chunk_id=audio_chunk.get_chunk_id(),
                            device_id=audio_chunk.device_id,
                            sequence_number=getattr(audio_chunk, 'sequence_number', None),
                            duration_ms=audio_chunk.get_duration_ms(),
                            sample_rate=getattr(audio_chunk, 'sample_rate', None),
                            file_id=getattr(audio_chunk, 'file_id', None),
                            topic=msg.topic,
                            partition=msg.partition,
                            offset=msg.offset,
                        )

                        # Process audio
                        asr_start = time.time()
                        transcribed = await self.asr_processor.process_audio_chunk(
                            audio_chunk
                        )
                        asr_duration = time.time() - asr_start

                        if transcribed:
                            logger.info(
                                "ASR processing completed",
                                chunk_id=audio_chunk.get_chunk_id(),
                                device_id=audio_chunk.device_id,
                                word_count=len(transcribed.words) if hasattr(transcribed, 'words') else 0,
                                text_length=len(transcribed.text) if hasattr(transcribed, 'text') else 0,
                                confidence=getattr(transcribed, 'confidence', None),
                                asr_processing_time_ms=round(asr_duration * 1000, 2),
                                input_duration_ms=audio_chunk.get_duration_ms(),
                            )
                            
                            # Send to output topic
                            await self._send_transcript(transcribed)

                            # Commit offset after successful processing
                            await self.consumer.commit()

                            logger.info(
                                "STT processing completed successfully",
                                chunk_id=audio_chunk.get_chunk_id(),
                                topic=msg.topic,
                                partition=msg.partition,
                                offset=msg.offset,
                                total_processing_time_ms=round((time.time() - asr_start + asr_duration) * 1000, 2),
                            )
                        else:
                            logger.warning(
                                "ASR processing returned no results",
                                chunk_id=audio_chunk.get_chunk_id(),
                                device_id=audio_chunk.device_id,
                                asr_processing_time_ms=round(asr_duration * 1000, 2),
                                topic=msg.topic,
                                partition=msg.partition,
                                offset=msg.offset,
                            )

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

            logger.info(
                "Transcript sent to Kafka",
                chunk_id=getattr(transcript, 'chunk_id', None),
                device_id=transcript.device_id,
                word_count=len(transcript.words) if hasattr(transcript, 'words') else 0,
                text_preview=transcript.text[:100] + '...' if hasattr(transcript, 'text') and len(transcript.text) > 100 else getattr(transcript, 'text', ''),
                confidence=getattr(transcript, 'confidence', None),
                topic=settings.kafka_output_topic,
            )

        except Exception as e:
            logger.error(
                "Failed to send transcript to Kafka",
                chunk_id=getattr(transcript, 'chunk_id', None),
                device_id=transcript.device_id,
                error=str(e),
                error_type=type(e).__name__,
                topic=settings.kafka_output_topic,
            )
            raise
