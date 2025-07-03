"""Kafka to TimescaleDB consumer service for automatic data ingestion."""

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict

import asyncpg
import structlog
from aiokafka import AIOKafkaConsumer
from fastapi import FastAPI
from fastapi.responses import JSONResponse

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Configuration
import os

DATABASE_URL = os.getenv(
    "LOOM_DATABASE_URL", "postgresql://loom:loom@localhost:5432/loom"
)
KAFKA_BOOTSTRAP_SERVERS = os.getenv("LOOM_KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_GROUP_ID = "kafka-to-db-consumer"

# Topic to table mappings
TOPIC_TABLE_MAPPINGS = {
    "media.audio.voice_segments": "media_audio_voice_segments_raw",
    "media.text.word_timestamps": "media_text_word_timestamps_raw",
    "media.image.vision_annotations": "media_image_vision_annotations_raw",
    "analysis.audio.emotion_scores": "analysis_audio_emotion_scores_raw",
    "analysis.image.face_emotions": "analysis_image_face_emotions_raw",
    "analysis.context.reasoning_chains": "analysis_context_reasoning_chains_raw",
    "task.url.processed_content": "task_url_processed_content_raw",
    "task.url.processed.twitter_archived": "twitter_extraction_results",
    "analysis.text.embedded.emails": "emails_with_embeddings",
    "analysis.text.embedded.twitter": "twitter_likes_with_embeddings",
}


class KafkaToDBConsumer:
    """Consumer that reads from Kafka topics and writes to TimescaleDB."""

    def __init__(self):
        self.consumer: AIOKafkaConsumer | None = None
        self.db_pool: asyncpg.Pool | None = None
        self.running = False

    async def start(self):
        """Start the consumer service."""
        logger.info("Starting Kafka to DB consumer service")

        # Initialize database connection pool
        self.db_pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=2,
            max_size=10,
            command_timeout=60,
        )

        # Initialize Kafka consumer
        self.consumer = AIOKafkaConsumer(
            *TOPIC_TABLE_MAPPINGS.keys(),
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id=KAFKA_GROUP_ID,
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )

        await self.consumer.start()
        self.running = True

        logger.info(
            "Kafka to DB consumer started",
            topics=list(TOPIC_TABLE_MAPPINGS.keys()),
            group_id=KAFKA_GROUP_ID,
        )

    async def stop(self):
        """Stop the consumer service."""
        logger.info("Stopping Kafka to DB consumer service")
        self.running = False

        if self.consumer:
            await self.consumer.stop()

        if self.db_pool:
            await self.db_pool.close()

        logger.info("Kafka to DB consumer stopped")

    async def consume_messages(self):
        """Main message consumption loop."""
        if not self.consumer or not self.db_pool:
            raise RuntimeError("Consumer not properly initialized")

        logger.info("Starting message consumption loop")

        try:
            async for message in self.consumer:
                if not self.running:
                    break

                try:
                    await self._process_message(message)
                except Exception as e:
                    logger.error(
                        "Failed to process message",
                        topic=message.topic,
                        partition=message.partition,
                        offset=message.offset,
                        error=str(e),
                        exc_info=True,
                    )

        except Exception as e:
            logger.error("Error in consumption loop", error=str(e), exc_info=True)
            raise

    async def _process_message(self, message):
        """Process a single Kafka message and insert into database."""
        topic = message.topic
        table_name = TOPIC_TABLE_MAPPINGS[topic]
        data = message.value

        logger.debug(
            "Processing message",
            topic=topic,
            table=table_name,
            message_id=data.get("message_id"),
        )

        # Insert data based on topic type
        if topic == "media.audio.voice_segments":
            await self._insert_voice_segments(table_name, data)
        elif topic == "media.text.word_timestamps":
            await self._insert_word_timestamps(table_name, data)
        elif topic == "media.image.vision_annotations":
            await self._insert_vision_annotations(table_name, data)
        elif topic == "analysis.audio.emotion_scores":
            await self._insert_emotion_scores(table_name, data)
        elif topic == "analysis.image.face_emotions":
            await self._insert_face_emotions(table_name, data)
        elif topic == "analysis.context.reasoning_chains":
            await self._insert_reasoning_chains(table_name, data)
        elif topic == "task.url.processed_content":
            await self._insert_processed_content(table_name, data)
        elif topic == "task.url.processed.twitter_archived":
            await self._insert_twitter_extraction(table_name, data)
        elif topic == "analysis.text.embedded.emails":
            await self._insert_embedded_emails(table_name, data)
        elif topic == "analysis.text.embedded.twitter":
            await self._insert_embedded_twitter(table_name, data)

        logger.debug(
            "Message processed successfully",
            topic=topic,
            table=table_name,
            message_id=data.get("message_id"),
        )

    async def _insert_voice_segments(self, table_name: str, data: Dict[str, Any]):
        """Insert voice segment data."""
        query = f"""
        INSERT INTO {table_name} (
            device_id, timestamp, schema_version, message_id,
            segment_start_time, segment_end_time, duration_ms, confidence_score,
            audio_sample_rate, audio_channels, voice_activity_threshold
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        ON CONFLICT (device_id, message_id, timestamp) DO NOTHING
        """

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                query,
                data["device_id"],
                data["timestamp"],
                data.get("schema_version", "v1"),
                data["message_id"],
                data["segment_start_time"],
                data["segment_end_time"],
                data["duration_ms"],
                data["confidence_score"],
                data.get("audio_sample_rate"),
                data.get("audio_channels", 1),
                data.get("voice_activity_threshold"),
            )

    async def _insert_word_timestamps(self, table_name: str, data: Dict[str, Any]):
        """Insert word timestamp data."""
        query = f"""
        INSERT INTO {table_name} (
            device_id, timestamp, schema_version, message_id,
            word_sequence, word_text, start_time_ms, end_time_ms, confidence_score,
            speaker_id, language_code, phonetic_transcription, word_boundaries
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
        ON CONFLICT (device_id, message_id, word_sequence, timestamp) DO NOTHING
        """

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                query,
                data["device_id"],
                data["timestamp"],
                data.get("schema_version", "v1"),
                data["message_id"],
                data["word_sequence"],
                data["word_text"],
                data["start_time_ms"],
                data["end_time_ms"],
                data["confidence_score"],
                data.get("speaker_id"),
                data.get("language_code", "en"),
                data.get("phonetic_transcription"),
                json.dumps(data.get("word_boundaries")),
            )

    async def _insert_vision_annotations(self, table_name: str, data: Dict[str, Any]):
        """Insert vision annotation data."""
        query = f"""
        INSERT INTO {table_name} (
            device_id, timestamp, schema_version, message_id,
            annotation_id, object_class, confidence_score, bounding_box,
            object_attributes, ocr_text, scene_description, image_width, image_height, model_version
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
        ON CONFLICT (device_id, message_id, annotation_id, timestamp) DO NOTHING
        """

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                query,
                data["device_id"],
                data["timestamp"],
                data.get("schema_version", "v1"),
                data["message_id"],
                data["annotation_id"],
                data["object_class"],
                data["confidence_score"],
                json.dumps(data.get("bounding_box")),
                json.dumps(data.get("object_attributes")),
                data.get("ocr_text"),
                data.get("scene_description"),
                data.get("image_width"),
                data.get("image_height"),
                data.get("model_version"),
            )

    async def _insert_emotion_scores(self, table_name: str, data: Dict[str, Any]):
        """Insert emotion score data."""
        query = f"""
        INSERT INTO {table_name} (
            device_id, timestamp, schema_version, message_id,
            segment_id, predicted_emotion, confidence_score, valence_score,
            arousal_score, dominance_score, emotion_probabilities, audio_features, model_version
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
        ON CONFLICT (device_id, message_id, segment_id, timestamp) DO NOTHING
        """

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                query,
                data["device_id"],
                data["timestamp"],
                data.get("schema_version", "v1"),
                data["message_id"],
                data["segment_id"],
                data["predicted_emotion"],
                data["confidence_score"],
                data.get("valence_score"),
                data.get("arousal_score"),
                data.get("dominance_score"),
                json.dumps(data.get("emotion_probabilities")),
                json.dumps(data.get("audio_features")),
                data.get("model_version"),
            )

    async def _insert_face_emotions(self, table_name: str, data: Dict[str, Any]):
        """Insert face emotion data."""
        query = f"""
        INSERT INTO {table_name} (
            device_id, timestamp, schema_version, message_id,
            face_id, emotion_label, confidence_score, face_bounding_box,
            facial_landmarks, age_estimate, gender_estimate, emotion_intensities,
            face_quality_score, model_version
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
        ON CONFLICT (device_id, message_id, face_id, timestamp) DO NOTHING
        """

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                query,
                data["device_id"],
                data["timestamp"],
                data.get("schema_version", "v1"),
                data["message_id"],
                data["face_id"],
                data["emotion_label"],
                data["confidence_score"],
                json.dumps(data.get("face_bounding_box")),
                json.dumps(data.get("facial_landmarks")),
                data.get("age_estimate"),
                data.get("gender_estimate"),
                json.dumps(data.get("emotion_intensities")),
                data.get("face_quality_score"),
                data.get("model_version"),
            )

    async def _insert_reasoning_chains(self, table_name: str, data: Dict[str, Any]):
        """Insert reasoning chain data."""
        query = f"""
        INSERT INTO {table_name} (
            device_id, timestamp, schema_version, message_id,
            reasoning_id, context_type, reasoning_chain, conclusion_text, confidence_score,
            input_sources, key_topics, entities_mentioned, temporal_context,
            spatial_context, model_version
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
        ON CONFLICT (device_id, message_id, reasoning_id, timestamp) DO NOTHING
        """

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                query,
                data["device_id"],
                data["timestamp"],
                data.get("schema_version", "v1"),
                data["message_id"],
                data["reasoning_id"],
                data["context_type"],
                json.dumps(data["reasoning_chain"]),
                data["conclusion_text"],
                data["confidence_score"],
                json.dumps(data.get("input_sources")),
                data.get("key_topics"),
                json.dumps(data.get("entities_mentioned")),
                json.dumps(data.get("temporal_context")),
                json.dumps(data.get("spatial_context")),
                data.get("model_version"),
            )

    async def _insert_processed_content(self, table_name: str, data: Dict[str, Any]):
        """Insert processed URL content data."""
        query = f"""
        INSERT INTO {table_name} (
            device_id, timestamp, schema_version, message_id,
            url_id, original_url, final_url, domain, content_type,
            title, content_text, content_summary, extracted_metadata,
            content_length, language_detected, category, tags,
            processing_duration_ms, processor_version
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19)
        ON CONFLICT (device_id, message_id, url_id, timestamp) DO NOTHING
        """

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                query,
                data["device_id"],
                data["timestamp"],
                data.get("schema_version", "v1"),
                data["message_id"],
                data["url_id"],
                data["original_url"],
                data.get("final_url"),
                data["domain"],
                data["content_type"],
                data.get("title"),
                data.get("content_text"),
                data.get("content_summary"),
                json.dumps(data.get("extracted_metadata")),
                data.get("content_length"),
                data.get("language_detected"),
                data.get("category"),
                data.get("tags"),
                data.get("processing_duration_ms"),
                data.get("processor_version"),
            )

    async def _insert_twitter_extraction(self, table_name: str, data: Dict[str, Any]):
        """Insert Twitter extraction results."""
        query = f"""
        INSERT INTO {table_name} (
            trace_id, tweet_id, url, timestamp,
            screenshot_path, screenshot_size_bytes, screenshot_dimensions,
            extracted_text, extracted_links, extracted_media, extracted_metadata,
            processor_version, processing_duration_ms, error_message
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
        ON CONFLICT (tweet_id) DO UPDATE SET
            screenshot_path = EXCLUDED.screenshot_path,
            extracted_text = EXCLUDED.extracted_text,
            extracted_metadata = EXCLUDED.extracted_metadata,
            timestamp = NOW()
        """

        # Parse timestamp if it's a string
        timestamp = data.get("extraction_timestamp")
        if isinstance(timestamp, str):
            from dateutil import parser

            timestamp = parser.isoparse(timestamp)
        elif timestamp is None:
            timestamp = datetime.utcnow()

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                query,
                data.get("trace_id"),
                data.get("tweet_id"),
                data.get("url"),
                timestamp,
                data.get("screenshot_path"),
                data.get("screenshot_size_bytes"),
                json.dumps(data.get("screenshot_dimensions", {})),
                data.get("extracted_text"),
                json.dumps(data.get("extracted_links", [])),
                json.dumps(data.get("extracted_media", [])),
                json.dumps(data.get("extracted_metadata", {})),
                data.get("processor_version"),
                data.get("processing_duration_ms"),
                data.get("error_message"),
            )

            # Also update the twitter_likes_with_embeddings table if exists
            if data.get("screenshot_path"):
                await conn.execute(
                    """
                    UPDATE twitter_likes_with_embeddings
                    SET screenshot_url = $1,
                        extracted_content = $2,
                        extraction_timestamp = NOW()
                    WHERE tweet_id = $3
                """,
                    data.get("screenshot_path"),
                    json.dumps(
                        {
                            "text": data.get("extracted_text"),
                            "links": data.get("extracted_links", []),
                            "media": data.get("extracted_media", []),
                        }
                    ),
                    data.get("tweet_id"),
                )

    async def _insert_embedded_emails(self, table_name: str, data: Dict[str, Any]):
        """Insert email with embeddings."""
        query = f"""
        INSERT INTO {table_name} (
            trace_id, message_id, device_id, timestamp, received_at,
            subject, sender_name, sender_email, recipient_email,
            body_text, body_html, headers, attachments, folder, email_source,
            embedding, embedding_model, embedding_timestamp, metadata
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19)
        ON CONFLICT (trace_id) DO UPDATE SET
            embedding = EXCLUDED.embedding,
            embedding_model = EXCLUDED.embedding_model,
            embedding_timestamp = NOW()
        """

        # Parse timestamps if they're strings
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            from dateutil import parser

            try:
                timestamp = parser.isoparse(timestamp)
                # Ensure timezone awareness
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                timestamp = datetime.utcnow()
        elif timestamp is None:
            timestamp = datetime.utcnow()

        received_at = data.get("received_at")
        if isinstance(received_at, str):
            from dateutil import parser

            try:
                received_at = parser.isoparse(received_at)
                # Ensure timezone awareness
                if received_at.tzinfo is None:
                    received_at = received_at.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                received_at = datetime.utcnow()
        elif received_at is None:
            received_at = datetime.utcnow()

        embedding_timestamp = data.get("embedding_timestamp")
        if isinstance(embedding_timestamp, str):
            from dateutil import parser

            try:
                embedding_timestamp = parser.isoparse(embedding_timestamp)
                # Ensure timezone awareness
                if embedding_timestamp.tzinfo is None:
                    embedding_timestamp = embedding_timestamp.replace(
                        tzinfo=timezone.utc
                    )
            except (ValueError, TypeError):
                embedding_timestamp = datetime.utcnow()
        elif embedding_timestamp is None:
            embedding_timestamp = datetime.utcnow()

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                query,
                data.get("trace_id"),
                data.get("message_id"),
                data.get("device_id"),
                timestamp,
                received_at,
                data.get("subject"),
                data.get("sender_name"),
                data.get("sender_email"),
                data.get("recipient_email"),
                data.get("body_text"),
                data.get("body_html"),
                json.dumps(data.get("headers", {})),
                json.dumps(data.get("attachments", [])),
                data.get("folder"),
                data.get("email_source"),
                f"[{','.join(map(str, data.get('embedding', [])))}]" if data.get('embedding') else None,  # Convert list to PostgreSQL array format
                data.get("embedding_model"),
                embedding_timestamp,
                json.dumps(data.get("metadata", {})),
            )

    async def _insert_embedded_twitter(self, table_name: str, data: Dict[str, Any]):
        """Insert Twitter like with embeddings."""
        query = f"""
        INSERT INTO {table_name} (
            trace_id, tweet_id, device_id, timestamp, liked_at, received_at,
            tweet_url, tweet_text, author_username, author_name, author_profile_url,
            embedding, embedding_model, embedding_timestamp,
            screenshot_url, extracted_content, extraction_timestamp, metadata
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18)
        ON CONFLICT (tweet_id) DO UPDATE SET
            tweet_text = EXCLUDED.tweet_text,
            embedding = EXCLUDED.embedding,
            embedding_model = EXCLUDED.embedding_model,
            embedding_timestamp = NOW()
        """

        # Parse timestamps if they're strings
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            from dateutil import parser

            try:
                timestamp = parser.isoparse(timestamp)
                # Ensure timezone awareness
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                timestamp = datetime.utcnow()
        elif timestamp is None:
            timestamp = datetime.utcnow()

        liked_at = data.get("liked_at")
        if isinstance(liked_at, str):
            from dateutil import parser

            try:
                liked_at = parser.isoparse(liked_at)
                # Ensure timezone awareness
                if liked_at.tzinfo is None:
                    liked_at = liked_at.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                liked_at = None

        received_at = data.get("received_at")
        if isinstance(received_at, str):
            from dateutil import parser

            try:
                received_at = parser.isoparse(received_at)
                # Ensure timezone awareness
                if received_at.tzinfo is None:
                    received_at = received_at.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                received_at = datetime.utcnow()
        elif received_at is None:
            received_at = datetime.utcnow()

        embedding_timestamp = data.get("embedding_timestamp")
        if isinstance(embedding_timestamp, str):
            from dateutil import parser

            try:
                embedding_timestamp = parser.isoparse(embedding_timestamp)
                # Ensure timezone awareness
                if embedding_timestamp.tzinfo is None:
                    embedding_timestamp = embedding_timestamp.replace(
                        tzinfo=timezone.utc
                    )
            except (ValueError, TypeError):
                embedding_timestamp = datetime.utcnow()
        elif embedding_timestamp is None:
            embedding_timestamp = datetime.utcnow()

        extraction_timestamp = data.get("extraction_timestamp")
        if isinstance(extraction_timestamp, str):
            from dateutil import parser

            try:
                extraction_timestamp = parser.isoparse(extraction_timestamp)
                # Ensure timezone awareness
                if extraction_timestamp.tzinfo is None:
                    extraction_timestamp = extraction_timestamp.replace(
                        tzinfo=timezone.utc
                    )
            except (ValueError, TypeError):
                extraction_timestamp = None

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                query,
                data.get("trace_id"),
                data.get("tweet_id"),
                data.get("device_id"),
                timestamp,
                liked_at,
                received_at,
                data.get("tweet_url"),
                data.get("tweet_text"),
                data.get("author_username"),
                data.get("author_name"),
                data.get("author_profile_url"),
                f"[{','.join(map(str, data.get('embedding', [])))}]" if data.get('embedding') else None,  # Convert list to PostgreSQL array format
                data.get("embedding_model"),
                embedding_timestamp,
                data.get("screenshot_url"),
                json.dumps(data.get("extracted_content", {})),
                extraction_timestamp,
                json.dumps(data.get("metadata", {})),
            )


# Global consumer instance
consumer = KafkaToDBConsumer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    await consumer.start()

    # Start consumption task
    consumption_task = asyncio.create_task(consumer.consume_messages())

    yield

    # Shutdown
    await consumer.stop()
    consumption_task.cancel()

    try:
        await consumption_task
    except asyncio.CancelledError:
        pass


# Create FastAPI app
app = FastAPI(
    title="Kafka to TimescaleDB Consumer",
    description="Automatic data ingestion from Kafka result topics to TimescaleDB",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/healthz")
async def health_check():
    """Health check endpoint."""
    return JSONResponse(
        content={
            "status": "healthy",
            "service": "kafka-to-db-consumer",
            "consumer_running": consumer.running,
        }
    )


@app.get("/status")
async def get_status():
    """Get consumer status."""
    return JSONResponse(
        content={
            "consumer_running": consumer.running,
            "topics": list(TOPIC_TABLE_MAPPINGS.keys()),
            "tables": list(TOPIC_TABLE_MAPPINGS.values()),
            "kafka_servers": KAFKA_BOOTSTRAP_SERVERS,
            "group_id": KAFKA_GROUP_ID,
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        log_level="info",
        reload=False,
    )
