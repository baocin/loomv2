"""Kafka consumer for activity classification."""

import json
import signal
import sys
from typing import Optional
import logging


# Create optimized consumer with database config
def create_optimized_consumer():
    # Note: For sync consumers, you may need to refactor to async
    # or use the BaseKafkaConsumer from loom_common
    from loom_common.kafka.consumer import BaseKafkaConsumer

    consumer = BaseKafkaConsumer(
        service_name="activity-classifier",
        topics=["device.sensor.accelerometer.windowed"],  # Update with actual topics
        bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"),
        db_pool=None,  # Pass asyncpg pool if available
    )

    return consumer


# Use it in your main function:
# consumer = create_optimized_consumer()

from kafka import KafkaConsumer, KafkaProducer

# Kafka consumer optimization

from .config import settings
from .classifier import ActivityClassifier
from .models import ActivityClassification

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ActivityClassifierConsumer:
    """Consumes motion, GPS, and step data to classify activities."""

    def __init__(self):
        self.consumer: Optional[KafkaConsumer] = None
        self.producer: Optional[KafkaProducer] = None
        self.classifier = ActivityClassifier()
        self.running = False

    def start(self):
        """Start consuming messages."""
        try:
            # Parse input topics
            input_topics = [t.strip() for t in settings.kafka_input_topics.split(",")]

            # Initialize Kafka consumer
            self.consumer = KafkaConsumer(
                *input_topics,
                bootstrap_servers=settings.kafka_bootstrap_servers,
                group_id=settings.kafka_consumer_group_id,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                auto_offset_reset=settings.kafka_auto_offset_reset,
                enable_auto_commit=True,
                max_poll_records=100,
            )

            # Initialize Kafka producer
            self.producer = KafkaProducer(
                bootstrap_servers=settings.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
                compression_type="lz4",
            )

            logger.info(
                f"Started activity classifier consumer on topics: {input_topics}"
            )

            self.running = True
            self._consume_messages()

        except Exception as e:
            logger.error(f"Failed to start consumer: {e}")
            raise

    def _consume_messages(self):
        """Main message consumption loop."""
        message_count = 0
        classification_count = 0

        while self.running:
            try:
                # Poll for messages
                message_batch = self.consumer.poll(timeout_ms=1000)

                for topic_partition, messages in message_batch.items():
                    topic = topic_partition.topic

                    for message in messages:
                        message_count += 1

                        # Process based on topic
                        classification = self._process_message(topic, message.value)

                        if classification:
                            classification_count += 1
                            self._send_classification(classification)

                        # Log progress
                        if message_count % 1000 == 0:
                            logger.info(
                                f"Processed {message_count} messages, "
                                f"created {classification_count} classifications"
                            )

            except KeyboardInterrupt:
                logger.info("Received interrupt signal")
                break
            except Exception as e:
                logger.error(f"Error in consumption loop: {e}")

    def _process_message(
        self, topic: str, message_data: dict
    ) -> Optional[ActivityClassification]:
        """Process a message based on its topic."""
        try:
            # Determine event type from topic
            if "motion.events.significant" in topic:
                event_type = "motion"
            elif "device.sensor.gps.raw" in topic:
                event_type = "gps"
            elif "device.health.steps.raw" in topic:
                event_type = "steps"
            else:
                logger.warning(f"Unknown topic: {topic}")
                return None

            # Get device ID
            device_id = message_data.get("device_id")
            if not device_id:
                logger.warning("Message missing device_id")
                return None

            # Add event to classifier
            return self.classifier.add_event(device_id, event_type, message_data)

        except Exception as e:
            logger.error(f"Failed to process message: {e}, data: {message_data}")
            return None

    def _send_classification(self, classification: ActivityClassification):
        """Send classification to Kafka."""
        try:
            # Convert to dict
            classification_dict = classification.model_dump(mode="json")

            # Send to Kafka
            self.producer.send(
                settings.kafka_output_topic,
                key=classification.device_id.encode("utf-8"),
                value=classification_dict,
            )

            logger.debug(
                f"Sent activity classification for device {classification.device_id}: "
                f"{classification.activity_type} (confidence: {classification.confidence:.2f})"
            )

        except Exception as e:
            logger.error(f"Failed to send classification: {e}")

    def cleanup(self):
        """Clean up resources."""
        self.running = False

        if self.consumer:
            try:
                self.consumer.close()
                logger.info("Closed Kafka consumer")
            except Exception as e:
                logger.error(f"Error closing consumer: {e}")

        if self.producer:
            try:
                self.producer.close()
                logger.info("Closed Kafka producer")
            except Exception as e:
                logger.error(f"Error closing producer: {e}")


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {signum}")
    sys.exit(0)


def main():
    """Main entry point."""
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create and start consumer
    consumer = ActivityClassifierConsumer()

    try:
        consumer.start()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        consumer.cleanup()


if __name__ == "__main__":
    main()
