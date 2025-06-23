import asyncio
import logging
import json
from kafka_consumer import KafkaConsumer
from kafka_producer import KafkaProducer
from url_processor import URLProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - hackernews-url-processor - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/hackernews-url-processor.log'),
        logging.StreamHandler()
    ]
)

class HackerNewsUrlProcessorService:
    def __init__(self):
        self.kafka_consumer = KafkaConsumer()
        self.kafka_producer = KafkaProducer()
        self.url_processor = URLProcessor()
        
    async def process_message(self, message):
        """Process a single URL message from Kafka"""
        try:
            data = message.get('data', {})
            url = data.get('url')
            source = data.get('source')
            
            # Only process URLs from HackerNews topic (should already be filtered, but double-check)
            if not url:
                return
            
            logging.info(f"Processing Hacker News URL: {url}")
            
            # Process the URL
            result = await self.url_processor.process_url(url, data)
            
            if result:
                # Send processed data to Kafka
                output_message = {
                    "schema_version": "v1",
                    "device_id": None,
                    "timestamp": result.get('timestamp'),
                    "data": {
                        "url": url,
                        "source": "hackernews",
                        "title": data.get('title'),
                        "score": data.get('score'),
                        "story_id": data.get('story_id'),
                        "comments_url": data.get('comments_url'),
                        "processed_content": result,
                        "screenshot_available": result.get('screenshot_data') is not None
                    }
                }
                
                self.kafka_producer.send_message(
                    topic="task.url.processed.hackernews_archived",
                    key=url,
                    value=output_message
                )
                
                logging.info(f"Successfully processed and archived Hacker News URL: {url}")
            else:
                logging.warning(f"Failed to process Hacker News URL: {url}")
                
        except Exception as e:
            logging.error(f"Error processing message: {e}")

    async def run(self):
        """Main service loop"""
        logging.info("Hacker News URL processor service starting...")
        
        await self.kafka_consumer.start()
        
        try:
            async for message in self.kafka_consumer.consume_messages("task.likes.hackernews"):
                await self.process_message(message)
        except KeyboardInterrupt:
            logging.info("Received shutdown signal")
        finally:
            await self.kafka_consumer.stop()
            self.kafka_producer.close()
            await self.url_processor.cleanup()

async def main():
    service = HackerNewsUrlProcessorService()
    await service.run()

if __name__ == "__main__":
    asyncio.run(main())