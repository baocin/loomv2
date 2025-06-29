"""Kafka consumer for processing multimodal messages."""

import json
import time
from datetime import datetime
from typing import Dict, List, Optional

import structlog
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.errors import KafkaError

from .config import settings
from .models import (
    TextMessage,
    ImageMessage,
    AudioMessage,
    MultimodalAnalysisResult,
    AnalysisResult,
    MultimodalRequest,
)
from .ollama_client import OllamaClient

logger = structlog.get_logger()


class KafkaConsumerManager:
    """Manages Kafka consumption for multimodal processing."""

    def __init__(self, ollama_client: OllamaClient):
        """Initialize Kafka consumer manager.

        Args:
            ollama_client: Initialized Ollama client
        """
        self.ollama_client = ollama_client
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

    async def process_text_message(
        self, message: Dict
    ) -> Optional[MultimodalAnalysisResult]:
        """Process a text message."""
        try:
            text_msg = TextMessage(**message)

            prompt = f"Analyze this text for sentiment, topics, and key insights: {text_msg.text}"
            if text_msg.context:
                prompt += f"\n\nContext: {text_msg.context}"

            start_time = time.time()
            result = await self.ollama_client.generate_text(prompt)
            processing_time = (time.time() - start_time) * 1000

            return MultimodalAnalysisResult(
                device_id=text_msg.device_id,
                recorded_at=text_msg.recorded_at,
                analysis_type="text_analysis",
                primary_result=result,
                text_analysis=AnalysisResult(
                    type="text", content=result, metadata=text_msg.metadata
                ),
                processing_time_ms=processing_time,
                model_version=settings.ollama_model,
            )

        except Exception as e:
            logger.error("Failed to process text message", error=str(e))
            return None

    async def process_image_message(
        self, message: Dict
    ) -> Optional[MultimodalAnalysisResult]:
        """Process an image message."""
        try:
            image_msg = ImageMessage(**message)

            prompt = "Analyze this image. Describe what you see, identify objects, read any text, and provide insights."

            start_time = time.time()
            result = await self.ollama_client.analyze_image(
                image_data=image_msg.data, prompt=prompt
            )
            processing_time = (time.time() - start_time) * 1000

            return MultimodalAnalysisResult(
                device_id=image_msg.device_id,
                recorded_at=image_msg.recorded_at,
                analysis_type="image_analysis",
                primary_result=result,
                image_analysis=AnalysisResult(
                    type="image",
                    content=result,
                    metadata={"format": image_msg.format, **(image_msg.metadata or {})},
                ),
                processing_time_ms=processing_time,
                model_version=settings.ollama_model,
            )

        except Exception as e:
            logger.error("Failed to process image message", error=str(e))
            return None

    async def process_audio_message(
        self, message: Dict
    ) -> Optional[MultimodalAnalysisResult]:
        """Process an audio message."""
        try:
            audio_msg = AudioMessage(**message)

            # Note: Gemma 3N may not directly support audio processing
            # This is a placeholder for future enhancement
            prompt = f"Analyze audio content. Duration: {audio_msg.duration}s, Format: {audio_msg.format}"

            start_time = time.time()
            result = await self.ollama_client.generate_text(prompt)
            processing_time = (time.time() - start_time) * 1000

            return MultimodalAnalysisResult(
                device_id=audio_msg.device_id,
                recorded_at=audio_msg.recorded_at,
                analysis_type="audio_analysis",
                primary_result=result,
                audio_analysis=AnalysisResult(
                    type="audio",
                    content=result,
                    metadata={
                        "duration": audio_msg.duration,
                        "format": audio_msg.format,
                        **(audio_msg.metadata or {}),
                    },
                ),
                processing_time_ms=processing_time,
                model_version=settings.ollama_model,
            )

        except Exception as e:
            logger.error("Failed to process audio message", error=str(e))
            return None

    async def process_multimodal_message(
        self, message: Dict, topic: str
    ) -> Optional[MultimodalAnalysisResult]:
        """Process a message based on its topic."""
        try:
            if "text" in topic:
                return await self.process_text_message(message)
            elif "image" in topic or "video" in topic:
                return await self.process_image_message(message)
            elif "audio" in topic:
                return await self.process_audio_message(message)
            else:
                logger.warning("Unknown topic type", topic=topic)
                return None

        except Exception as e:
            logger.error(
                "Failed to process multimodal message", error=str(e), topic=topic
            )
            return None

    async def consume_messages(self) -> None:
        """Main consumer loop."""
        logger.info("Starting multimodal message consumption loop")

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

                # Process the message based on topic
                result = await self.process_multimodal_message(msg.value, msg.topic)

                if result:
                    # Send result to output topic
                    await self.producer.send_and_wait(
                        self.output_topic,
                        value=result.model_dump(mode="json"),
                        key=result.device_id.encode("utf-8"),
                    )

                    logger.info(
                        "Sent multimodal analysis result",
                        device_id=result.device_id,
                        analysis_type=result.analysis_type,
                        output_topic=self.output_topic,
                        processing_time_ms=result.processing_time_ms,
                    )

                    # Commit offset after successful processing
                    await self.consumer.commit()
                else:
                    logger.warning(
                        "Message processing failed, not committing offset",
                        topic=msg.topic,
                        partition=msg.partition,
                        offset=msg.offset,
                    )

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
