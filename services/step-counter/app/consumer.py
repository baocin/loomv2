"""Kafka consumer for step counting."""

import json
import signal
import sys
from typing import Optional, Dict
import logging


# Create optimized consumer with database config
def create_optimized_consumer():
    # Note: For sync consumers, you may need to refactor to async
    # or use the BaseKafkaConsumer from loom_common
    from loom_common.kafka.consumer import BaseKafkaConsumer

    consumer = BaseKafkaConsumer(
        service_name="step-counter",
        topics=["device.sensor.accelerometer.raw"],  # Update with actual topics
        bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"),
        db_pool=None,  # Pass asyncpg pool if available
    )

    return consumer


# Use it in your main function:
# consumer = create_optimized_consumer()

from kafka import KafkaConsumer, KafkaProducer

# Kafka consumer optimization

from .config import settings
from .step_detector import StepDetector
from .models import AccelerometerReading, StepCountEvent

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class StepCounterConsumer:
    """Consumes accelerometer data and counts steps."""

    def __init__(self):
        self.consumer: Optional[KafkaConsumer] = None
        self.producer: Optional[KafkaProducer] = None
        self.detectors: Dict[str, StepDetector] = {}  # One detector per device
        self.running = False

    def start(self):
        """Start consuming messages."""
        try:
            # Initialize Kafka consumer
            self.consumer = KafkaConsumer(
                settings.kafka_input_topic,
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
                f"Started step counter consumer on topic {settings.kafka_input_topic}"
            )

            self.running = True
            self._consume_messages()

        except Exception as e:
            logger.error(f"Failed to start consumer: {e}")
            raise

    def _consume_messages(self):
        """Main message consumption loop."""
        message_count = 0
        event_count = 0

        while self.running:
            try:
                # Poll for messages
                message_batch = self.consumer.poll(timeout_ms=1000)

                for topic_partition, messages in message_batch.items():
                    for message in messages:
                        message_count += 1

                        # Skip old data structure messages
                        if "data" in message.value:
                            continue

                        event = self._process_message(message.value)
                        if event:
                            event_count += 1

                        # Log progress every 1000 messages
                        if message_count % 1000 == 0:
                            logger.info(
                                f"Processed {message_count} messages, "
                                f"detected {event_count} step events"
                            )

            except KeyboardInterrupt:
                logger.info("Received interrupt signal")
                break
            except Exception as e:
                logger.error(f"Error in consumption loop: {e}")

    def _process_message(self, message_data: dict) -> Optional[StepCountEvent]:
        """Process a single accelerometer reading."""
        try:
            # Parse the reading
            reading = AccelerometerReading(**message_data)

            # Get or create detector for this device
            if reading.device_id not in self.detectors:
                self.detectors[reading.device_id] = StepDetector(reading.device_id)
                logger.info(f"Created step detector for device: {reading.device_id}")

            detector = self.detectors[reading.device_id]

            # Check for steps
            event = detector.add_reading(reading)

            if event:
                # Convert to dict for Kafka
                event_dict = event.model_dump(mode="json")

                # Send to Kafka
                self.producer.send(
                    settings.kafka_output_topic,
                    key=event.device_id.encode("utf-8"),
                    value=event_dict,
                )

                logger.debug(
                    f"Detected {event.step_count} steps for device {event.device_id}"
                )

                return event

        except Exception as e:
            logger.error(f"Failed to process message: {e}, data: {message_data}")

        return None

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
    consumer = StepCounterConsumer()

    try:
        consumer.start()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        consumer.cleanup()


if __name__ == "__main__":
    main()
