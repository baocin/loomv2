import json
import logging
from kafka import KafkaProducer as KP
from kafka.errors import KafkaError
import os
from typing import Any, Optional

class KafkaProducer:
    def __init__(self):
        """Initialize Kafka producer"""
        self.bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.topic_prefix = os.getenv("KAFKA_TOPIC_PREFIX", "loom")
        
        self.producer = KP(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            retries=3,
            acks='all'
        )
        
        logging.info(f"Kafka producer initialized with servers: {self.bootstrap_servers}")

    def send_message(self, topic: str, value: Any, key: Optional[str] = None):
        """Send message to Kafka topic"""
        try:
            # Add topic prefix if configured
            full_topic = f"{self.topic_prefix}.{topic}" if self.topic_prefix else topic
            
            future = self.producer.send(full_topic, value=value, key=key)
            
            # Wait for message to be sent
            record_metadata = future.get(timeout=10)
            
            logging.debug(f"Message sent to {full_topic} at partition {record_metadata.partition}, offset {record_metadata.offset}")
            
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