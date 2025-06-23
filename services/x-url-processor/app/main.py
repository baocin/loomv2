import asyncio
import logging
import json
from kafka_consumer import KafkaConsumer
from kafka_producer import KafkaProducer
from x_tweet_processor import XTweetProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - x-url-processor - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/x-url-processor.log'),
        logging.StreamHandler()
    ]
)

class XUrlProcessorService:
    def __init__(self):
        self.kafka_consumer = KafkaConsumer()
        self.kafka_producer = KafkaProducer()
        self.tweet_processor = XTweetProcessor()
        
    async def process_message(self, message):
        """Process a single URL message from Kafka"""
        try:
            data = message.get('data', {})
            url = data.get('url')
            source = data.get('source')
            
            # Only process X.com URLs (should already be filtered by topic, but double-check)
            if not url:
                return
            
            if not url.startswith('https://x.com/') and not url.startswith('https://twitter.com/'):
                logging.warning(f"Received non-X.com URL on task.likes.x topic: {url}")
                return
            
            logging.info(f"Processing X.com URL: {url}")
            
            # Setup browser and process tweet
            await self.tweet_processor.setup()
            tweet_data = await self.tweet_processor.scrape_tweet(url)
            await self.tweet_processor.cleanup()
            
            if tweet_data:
                # Send processed tweet data to Kafka
                output_message = {
                    "schema_version": "v1",
                    "device_id": None,
                    "timestamp": tweet_data.get('created_at'),
                    "data": {
                        "url": url,
                        "source": "x.com",
                        "tweet_data": tweet_data,
                        "screenshot_available": tweet_data.get('image_data') is not None
                    }
                }
                
                self.kafka_producer.send_message(
                    topic="task.url.processed.twitter_archived",
                    key=url,
                    value=output_message
                )
                
                logging.info(f"Successfully processed and archived X.com URL: {url}")
            else:
                logging.warning(f"Failed to process X.com URL: {url}")
                
        except Exception as e:
            logging.error(f"Error processing message: {e}")

    async def run(self):
        """Main service loop"""
        logging.info("X.com URL processor service starting...")
        
        await self.kafka_consumer.start()
        
        try:
            async for message in self.kafka_consumer.consume_messages("task.likes.x"):
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