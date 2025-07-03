"""Kafka consumer for processing emails and tweets."""

import json
from typing import Dict, Any, Optional
import uuid
from datetime import datetime

import structlog
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from app.embedder import TextEmbedder
from app.db_handler import DatabaseHandler

logger = structlog.get_logger()


class TextEmbeddingConsumer:
    """Consumes emails and tweets from Kafka, embeds them, and stores in DB."""

    def __init__(
        self,
        bootstrap_servers: str,
        email_topic: str,
        twitter_topic: str,
        embedded_email_topic: str,
        embedded_twitter_topic: str,
        consumer_group: str,
        database_url: str,
        embedder: TextEmbedder,
    ):
        self.bootstrap_servers = bootstrap_servers
        self.email_topic = email_topic
        self.twitter_topic = twitter_topic
        self.embedded_email_topic = embedded_email_topic
        self.embedded_twitter_topic = embedded_twitter_topic
        self.consumer_group = consumer_group
        self.database_url = database_url
        self.embedder = embedder

        self.consumer: Optional[AIOKafkaConsumer] = None
        self.producer: Optional[AIOKafkaProducer] = None
        self.db_handler = DatabaseHandler(database_url)
        self.running = False

    async def start(self):
        """Start the consumer and producer."""
        try:
            # Initialize consumer
            self.consumer = AIOKafkaConsumer(
                self.email_topic,
                self.twitter_topic,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.consumer_group,
                auto_offset_reset="earliest",
                enable_auto_commit=False,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            )

            # Initialize producer
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )

            await self.consumer.start()
            await self.producer.start()
            await self.db_handler.connect()
            await self.embedder.load_model()

            self.running = True
            logger.info("Text embedding consumer started successfully")

        except Exception as e:
            logger.error("Failed to start consumer", error=str(e))
            raise

    async def stop(self):
        """Stop the consumer and producer."""
        self.running = False

        if self.consumer:
            await self.consumer.stop()
        if self.producer:
            await self.producer.stop()
        await self.db_handler.disconnect()

        logger.info("Text embedding consumer stopped")

    async def process_email(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process an email message."""
        try:
            # Generate trace ID if not present
            trace_id = message.get("trace_id", str(uuid.uuid4()))

            # Prepare text for embedding
            text = self.embedder.prepare_email_text(message)

            # Generate embedding
            embedding = self.embedder.embed_text(text)

            # Store in database
            email_id = await self.db_handler.store_email_with_embedding(
                message, embedding, trace_id
            )

            # Prepare embedded message with full original content
            embedded_message = {
                **message,  # Include all original fields
                "trace_id": trace_id,
                "email_id": email_id,
                "embedding": embedding,
                "embedding_model": self.embedder.model_name,
                "embedding_timestamp": datetime.utcnow().isoformat(),
                "text_length": len(text),
            }

            return embedded_message

        except Exception as e:
            logger.error(
                "Failed to process email",
                error=str(e),
                message_id=message.get("message_id"),
            )
            return None

    async def process_twitter(
        self, message: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Process a Twitter message."""
        try:
            # Generate trace ID if not present
            trace_id = message.get("trace_id", str(uuid.uuid4()))

            # Extract the data payload (support both nested and flat structures)
            data = message.get("data", message)
            
            # Extract tweet ID from URL or use the provided tweet_id
            tweet_url = data.get("url", data.get("tweetLink", ""))
            tweet_id = data.get("tweet_id") or (tweet_url.split("/")[-1] if tweet_url else str(uuid.uuid4()))
            
            # Extract author username from profile_link if not provided
            if not data.get("author") and data.get("profile_link"):
                data["author"] = data["profile_link"].rstrip("/").split("/")[-1]

            # Prepare text for embedding
            text = self.embedder.prepare_twitter_text(data)

            # Generate embedding
            embedding = self.embedder.embed_text(text)

            # Store in database - pass the flattened data structure
            stored_id = await self.db_handler.store_twitter_with_embedding(
                {
                    **data,  # Use the extracted data
                    "device_id": message.get("device_id"),
                    "timestamp": message.get("timestamp"),
                    "trace_id": trace_id,
                }, 
                embedding, 
                trace_id, 
                tweet_id
            )

            # Send to X URL processor for screenshot/extraction
            if self.producer:
                await self.producer.send_and_wait(
                    "task.url.ingest",
                    value={
                        "url": tweet_url,
                        "source": "twitter_likes",
                        "trace_id": trace_id,
                        "tweet_id": tweet_id,
                        "priority": "normal",
                        "metadata": {
                            "author": data.get("author", data.get("author_username")),
                            "text": data.get("text"),
                        },
                    },
                )

            # Prepare embedded message with full original content
            embedded_message = {
                **message,  # Include all original fields
                "trace_id": trace_id,
                "tweet_id": tweet_id,
                "tweet_url": tweet_url,
                "embedding": embedding,
                "embedding_model": self.embedder.model_name,
                "embedding_timestamp": datetime.utcnow().isoformat(),
                "text_length": len(text),
            }

            return embedded_message

        except Exception as e:
            logger.error(
                "Failed to process Twitter message",
                error=str(e),
                url=message.get("tweetLink"),
            )
            return None

    async def consume_messages(self):
        """Main consumption loop."""
        logger.info("Starting message consumption")

        async for msg in self.consumer:
            if not self.running:
                break

            try:
                topic = msg.topic
                message = msg.value

                if topic == self.email_topic:
                    result = await self.process_email(message)
                    if result and self.producer:
                        await self.producer.send_and_wait(
                            self.embedded_email_topic,
                            value=result,
                        )

                elif topic == self.twitter_topic:
                    result = await self.process_twitter(message)
                    if result and self.producer:
                        await self.producer.send_and_wait(
                            self.embedded_twitter_topic,
                            value=result,
                        )

                # Commit offset after successful processing
                await self.consumer.commit()

                logger.info(
                    "Processed message",
                    topic=topic,
                    partition=msg.partition,
                    offset=msg.offset,
                )

            except Exception as e:
                logger.error(
                    "Error processing message",
                    error=str(e),
                    topic=msg.topic,
                    partition=msg.partition,
                    offset=msg.offset,
                )

    async def run(self):
        """Run the consumer."""
        await self.start()
        try:
            await self.consume_messages()
        finally:
            await self.stop()
