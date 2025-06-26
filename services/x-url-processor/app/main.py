import asyncio
import logging
import os
from kafka_consumer import KafkaConsumer
from kafka_producer import KafkaProducer
from x_tweet_processor import XTweetProcessor

# Configure logging
log_level = os.getenv("LOOM_LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, log_level.upper()),
    format="%(asctime)s - x-url-processor - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/app/logs/x-url-processor.log"),
        logging.StreamHandler(),
    ],
)


class XUrlProcessorService:
    def __init__(self):
        self.kafka_consumer = KafkaConsumer()
        self.kafka_producer = KafkaProducer()
        self.tweet_processor = XTweetProcessor()

    async def process_message(self, message):
        """Process a single URL message from Kafka"""
        try:
            # Handle both wrapped and direct message formats
            if "data" in message:
                data = message.get("data", {})
                # Check for trace_id at both top level and inside data
                trace_id = message.get("trace_id") or data.get("trace_id")
                tweet_id = data.get("tweet_id")
            else:
                data = message
                trace_id = data.get("trace_id")
                tweet_id = data.get("tweet_id")

            url = data.get("url")
            metadata = data.get("metadata", {})

            # Only process X.com/Twitter URLs
            if not url:
                return

            if not (
                url.startswith("https://x.com/")
                or url.startswith("https://twitter.com/")
                or url.startswith("http://x.com/")
                or url.startswith("http://twitter.com/")
            ):
                logging.debug(f"Skipping non-X.com URL: {url}")
                return

            logging.info(
                f"Processing X.com URL: {url} (trace_id: {trace_id}, tweet_id: {tweet_id})"
            )

            # Setup browser and process tweet
            await self.tweet_processor.setup()
            tweet_data = await self.tweet_processor.scrape_tweet(
                url, trace_id, tweet_id
            )
            await self.tweet_processor.cleanup()

            if tweet_data:
                # Get output topic from environment variable
                output_topic = os.getenv(
                    "LOOM_KAFKA_OUTPUT_TOPIC", "task.url.processed.twitter_archived"
                )

                # Send processed tweet data to Kafka
                # Flatten the structure for the DB consumer
                output_message = {
                    "trace_id": tweet_data.get("trace_id"),
                    "tweet_id": tweet_data.get("tweet_id"),
                    "url": tweet_data.get("url"),
                    "extraction_timestamp": tweet_data.get("extraction_timestamp"),
                    "screenshot_path": tweet_data.get("screenshot_path"),
                    "extracted_text": tweet_data.get("extracted_text"),
                    "extracted_links": tweet_data.get("extracted_links", []),
                    "extracted_media": tweet_data.get("extracted_media", []),
                    "extracted_metadata": {
                        "author_name": tweet_data.get("author_name"),
                        "created_at": tweet_data.get("created_at"),
                        "full_data": tweet_data.get("tweet", {}),
                    },
                    "processor_version": "1.0.0",
                    "processing_duration_ms": tweet_data.get(
                        "processing_duration_ms", 0
                    ),
                }

                self.kafka_producer.send_message(
                    topic=output_topic,
                    key=tweet_data.get("tweet_id", url),
                    value=output_message,
                )

                logging.info(f"Successfully processed and archived X.com URL: {url}")
            else:
                logging.warning(f"Failed to process X.com URL: {url}")

        except Exception as e:
            logging.error(f"Error processing message: {e}")

    async def run(self):
        """Main service loop"""
        logging.info("X.com URL processor service starting...")

        # Get input topic from environment variable
        input_topic = os.getenv("LOOM_KAFKA_INPUT_TOPIC", "task.url.ingest")
        logging.info(f"Consuming from topic: {input_topic}")

        await self.kafka_consumer.start()

        try:
            async for message in self.kafka_consumer.consume_messages(input_topic):
                await self.process_message(message)
        except KeyboardInterrupt:
            logging.info("Received shutdown signal")
        finally:
            await self.kafka_consumer.stop()
            self.kafka_producer.close()


async def main():
    service = XUrlProcessorService()
    await service.run()


if __name__ == "__main__":
    asyncio.run(main())
