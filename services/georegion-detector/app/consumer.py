"""Kafka consumer for georegion detection"""

import json
from typing import Optional


# Create optimized consumer with database config
def create_optimized_consumer():
    # Note: For sync consumers, you may need to refactor to async
    # or use the BaseKafkaConsumer from loom_common
    from loom_common.kafka.consumer import BaseKafkaConsumer

    consumer = BaseKafkaConsumer(
        service_name="georegion-detector",
        topics=["device.sensor.gps.raw"],  # Update with actual topics
        bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"),
        db_pool=None,  # Pass asyncpg pool if available
    )

    return consumer


# Use it in your main function:
# consumer = create_optimized_consumer()

import structlog
from kafka import KafkaConsumer, KafkaProducer

# Kafka consumer optimization

from .config import settings
from .detector import GeoregionDetector
from .models import GeocodedLocation
from .metrics import (
    messages_processed,
    detections_made,
    processing_errors,
    processing_duration,
)

logger = structlog.get_logger()


class GeoregionDetectionConsumer:
    """Consumes geocoded locations and detects georegion presence"""

    def __init__(self):
        self.consumer: Optional[KafkaConsumer] = None
        self.producer: Optional[KafkaProducer] = None
        self.detector = GeoregionDetector()
        self.running = False

    def start(self):
        """Start consuming messages"""
        try:
            # Initialize Kafka consumer
            self.consumer = KafkaConsumer(
                settings.kafka_input_topic,
                bootstrap_servers=settings.kafka_bootstrap_servers,
                group_id=settings.kafka_consumer_group_id,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                auto_offset_reset="earliest",
                enable_auto_commit=True,
                max_poll_records=50,
            )

            # Initialize Kafka producer
            self.producer = KafkaProducer(
                bootstrap_servers=settings.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
                compression_type="lz4",
            )

            logger.info(
                "Started georegion detection consumer",
                input_topic=settings.kafka_input_topic,
                output_topic=settings.kafka_output_topic,
            )

            self.running = True
            self._consume_messages()

        except Exception as e:
            logger.error("Failed to start consumer", error=str(e))
            raise

    def _consume_messages(self):
        """Main message consumption loop"""
        while self.running:
            try:
                # Poll for messages
                message_batch = self.consumer.poll(timeout_ms=1000)

                for topic_partition, messages in message_batch.items():
                    for message in messages:
                        with processing_duration.time():
                            self._process_message(message.value)

            except KeyboardInterrupt:
                logger.info("Received interrupt signal")
                break
            except Exception as e:
                logger.error("Error in consumption loop", error=str(e))
                processing_errors.inc()

    def _process_message(self, message_data: dict):
        """Process a single geocoded location message"""
        try:
            # Parse the geocoded location
            location = GeocodedLocation(**message_data)
            messages_processed.inc()

            # Detect georegions
            detections = self.detector.detect_georegions(location)

            # Send each detection to Kafka
            for detection in detections:
                self.producer.send(
                    settings.kafka_output_topic, value=detection.model_dump(mode="json")
                )
                detections_made.inc()

            if detections:
                logger.info(
                    "Processed geocoded location",
                    device_id=location.device_id,
                    detections=len(detections),
                )

        except Exception as e:
            logger.error(
                "Failed to process message",
                error=str(e),
                message=str(message_data)[:200],
            )
            processing_errors.inc()

    def cleanup(self):
        """Clean up resources"""
        self.running = False

        if self.consumer:
            try:
                self.consumer.close()
                logger.info("Closed Kafka consumer")
            except Exception as e:
                logger.error("Error closing consumer", error=str(e))

        if self.producer:
            try:
                self.producer.close()
                logger.info("Closed Kafka producer")
            except Exception as e:
                logger.error("Error closing producer", error=str(e))
