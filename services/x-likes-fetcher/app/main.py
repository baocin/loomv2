import os
import logging
import schedule
import time
import asyncio
from x_likes_fetcher import XLikesFetcher
from kafka_producer import KafkaProducer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - x-likes-fetcher - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/x-likes-fetcher.log'),
        logging.StreamHandler()
    ]
)

async def fetch_liked_tweets():
    """Fetch liked tweets and send URLs to Kafka for processing"""
    try:
        logging.info("Starting X.com likes fetch process")
        
        # Initialize services
        x_fetcher = XLikesFetcher()
        kafka_producer = KafkaProducer()
        
        # Setup browser and login
        await x_fetcher.setup()
        
        # Fetch liked tweets
        liked_tweets = await x_fetcher.scrape_likes()
        
        # Send each tweet URL to Kafka for processing
        for tweet_data in liked_tweets:
            message = {
                "schema_version": "v1",
                "device_id": None,
                "timestamp": tweet_data.get("time"),
                "data": {
                    "url": tweet_data["tweetLink"],
                    "source": "x.com",
                    "type": "liked_tweet",
                    "profile_link": tweet_data.get("profileLink"),
                    "preview_text": tweet_data.get("text", "")[:200]  # First 200 chars
                }
            }
            
            kafka_producer.send_message(
                topic="task.likes.x",
                key=tweet_data["tweetLink"],
                value=message
            )
        
        # Cleanup
        await x_fetcher.cleanup()
        kafka_producer.close()
        
        logging.info(f"Successfully processed {len(liked_tweets)} liked tweets")
        
    except Exception as e:
        logging.error(f"Error in X.com likes fetch process: {e}")

def run_async_fetch():
    """Wrapper to run async function in scheduler"""
    asyncio.run(fetch_liked_tweets())

def main():
    """Main application entry point"""
    logging.info("X.com likes fetcher service starting...")
    
    # Schedule X.com likes fetching every 6 hours
    schedule.every(6).hours.do(run_async_fetch)
    
    # Also run immediately on startup
    run_async_fetch()
    
    # Keep the service running
    while True:
        schedule.run_pending()
        time.sleep(300)  # Check every 5 minutes

if __name__ == "__main__":
    main()