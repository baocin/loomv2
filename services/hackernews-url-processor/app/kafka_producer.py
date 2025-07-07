import json
import logging
from kafka import KafkaProducer as KP
from kafka.errors import KafkaError
import os
from typing import Any, Optional
from loom_common.kafka.activity_logger import ConsumerActivityLogger


class KafkaProducer(ConsumerActivityLogger):
    def __init__(self, consumer=None):
        """Initialize Kafka producer"""
        super().__init__(service_name="hackernews-url-processor")
        self.bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.topic_prefix = os.getenv("KAFKA_TOPIC_PREFIX", "")
        self.consumer = consumer  # Reference to consumer for shared activity logger

        self.producer = KP(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
            retries=3,
            acks="all",
        )

        logging.info(
            f"Kafka producer initialized with servers: {self.bootstrap_servers}"
        )

    async def send_message(self, topic: str, value: Any, key: Optional[str] = None):
        """Send message to Kafka topic"""
        try:
            # Add topic prefix if configured
            full_topic = f"{self.topic_prefix}.{topic}" if self.topic_prefix else topic
            full_topic = full_topic.strip(".")  # Remove any leading/trailing dots

            future = self.producer.send(full_topic, value=value, key=key)

            # Wait for message to be sent
            record_metadata = future.get(timeout=10)

            # Log production using consumer's activity logger if available
            if self.consumer and hasattr(self.consumer, "log_production"):
                await self.consumer.log_production(
                    topic=full_topic,
                    partition=record_metadata.partition,
                    offset=record_metadata.offset,
                    key=key,
                    value=value,
                )

            logging.debug(
                f"Message sent to {full_topic} at partition {record_metadata.partition}, offset {record_metadata.offset}"
            )

        except KafkaError as e:
            logging.error(f"Failed to send message to Kafka: {e}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error sending message: {e}")
            raise

    def close(self):
        """Close Kafka producer"""
        if self.producer:
            self.producer.close()
            logging.info("Kafka producer closed")
