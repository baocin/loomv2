import os
import logging
import schedule
import time
from hackernews_fetcher import HackerNewsFetcher
from kafka_producer import KafkaProducer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - hackernews-fetcher - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/hackernews-fetcher.log'),
        logging.StreamHandler()
    ]
)

def fetch_hackernews():
    """Fetch personal Hacker News favorites/upvoted items and send URLs to Kafka for processing"""
    try:
        logging.info("Starting Hacker News personal favorites fetch process")
        
        # Initialize services
        hn_fetcher = HackerNewsFetcher()
        kafka_producer = KafkaProducer()
        
        # Fetch user's favorites/upvoted items
        favorites = hn_fetcher.fetch_user_favorites()
        
        # Send each favorite URL to Kafka for processing
        for story_data in favorites:
            # Only process stories with URLs (not just text posts)
            if story_data.get("url"):
                message = {
                    "schema_version": "v1",
                    "device_id": None,
                    "timestamp": story_data.get("time"),
                    "data": {
                        "url": story_data["url"],
                        "source": "hackernews",
                        "type": "liked_story",
                        "title": story_data.get("title"),
                        "score": story_data.get("score"),
                        "comments_url": f"https://news.ycombinator.com/item?id={story_data['id']}",
                        "story_id": story_data["id"]
                    }
                }
                
                kafka_producer.send_message(
                    topic="task.likes.hackernews",
                    key=story_data["url"],
                    value=message
                )
        
        kafka_producer.close()
        
        logging.info(f"Successfully processed {len(favorites)} Hacker News favorites")
        
    except Exception as e:
        logging.error(f"Error in Hacker News fetch process: {e}")

def main():
    """Main application entry point"""
    logging.info("Hacker News fetcher service starting...")
    
    # Schedule Hacker News fetching every 2 hours
    schedule.every(2).hours.do(fetch_hackernews)
    
    # Also run immediately on startup
    fetch_hackernews()
    
    # Keep the service running
    while True:
        schedule.run_pending()
        time.sleep(300)  # Check every 5 minutes

if __name__ == "__main__":
    main()