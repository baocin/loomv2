import json
import logging
import asyncio
from kafka import KafkaConsumer as KC
import os
from typing import AsyncGenerator, Dict, Any


class KafkaConsumer:
    def __init__(self):
        """Initialize Kafka consumer"""
        self.bootstrap_servers = os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS", os.getenv("LOOM_KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        )
        self.topic_prefix = os.getenv("KAFKA_TOPIC_PREFIX", os.getenv("LOOM_KAFKA_TOPIC_PREFIX", ""))
        self.group_id = os.getenv(
            "LOOM_KAFKA_CONSUMER_GROUP", "hackernews-url-processor"
        )

        self.consumer = None

    async def start(self):
        """Start the Kafka consumer"""
        try:
            self.consumer = KC(
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                auto_offset_reset="latest",
                enable_auto_commit=True,
                consumer_timeout_ms=1000,
            )
            logging.info(f"Kafka consumer started with group_id: {self.group_id}")
        except Exception as e:
            logging.error(f"Failed to start Kafka consumer: {e}")
            raise

    async def consume_messages(
        self, topic: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Consume messages from a Kafka topic"""
        if not self.consumer:
            raise ValueError("Consumer not started. Call start() first.")

        # Add topic prefix if configured
        full_topic = f"{self.topic_prefix}.{topic}" if self.topic_prefix else topic
        full_topic = full_topic.strip(".")  # Remove any leading/trailing dots

        self.consumer.subscribe([full_topic])
        logging.info(f"Subscribed to topic: {full_topic}")

        try:
            while True:
                message_pack = self.consumer.poll(timeout_ms=1000)

                if message_pack:
                    for topic_partition, messages in message_pack.items():
                        for message in messages:
                            try:
                                logging.debug(
                                    f"Received message from {topic_partition.topic} at offset {message.offset}"
                                )
                                yield message.value
                            except Exception as e:
                                logging.error(f"Error processing message: {e}")

                # Allow other coroutines to run
                await asyncio.sleep(0.1)

        except KeyboardInterrupt:
            logging.info("Consumer interrupted")
        except Exception as e:
            logging.error(f"Error in consumer loop: {e}")

    async def stop(self):
        """Stop the Kafka consumer"""
        if self.consumer:
            self.consumer.close()
            logging.info("Kafka consumer stopped")
