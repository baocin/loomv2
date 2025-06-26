import os
import logging
import schedule
import time
import asyncio
import uuid
from x_likes_fetcher import XLikesFetcher
from kafka_producer import KafkaProducer

# Configure logging
log_level = os.getenv("LOOM_LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, log_level.upper()),
    format="%(asctime)s - x-likes-fetcher - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/app/logs/x-likes-fetcher.log"),
        logging.StreamHandler(),
    ],
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

        # Get output topics from environment variables
        raw_topic = os.getenv("LOOM_KAFKA_OUTPUT_TOPIC", "external.twitter.liked.raw")
        url_topic = os.getenv("LOOM_KAFKA_URL_TOPIC", "task.url.ingest")
        send_to_url_processor = (
            os.getenv("LOOM_SEND_TO_URL_PROCESSOR", "true").lower() == "true"
        )

        logging.info(f"Using raw data topic: {raw_topic}")
        if send_to_url_processor:
            logging.info(f"Using URL ingest topic: {url_topic}")

        # Send each tweet data to Kafka
        for tweet_data in liked_tweets:
            # Generate a trace ID for this tweet
            trace_id = str(uuid.uuid4())
            
            # Extract tweet ID from URL
            tweet_id = tweet_data["tweetLink"].split("/")[-1] if tweet_data.get("tweetLink") else None
            
            # Send complete tweet data to raw topic
            raw_message = {
                "schema_version": "v1",
                "device_id": None,
                "timestamp": tweet_data.get("time"),
                "trace_id": trace_id,
                "data": {
                    "url": tweet_data["tweetLink"],
                    "source": "x.com",
                    "type": "liked_tweet",
                    "profile_link": tweet_data.get("profileLink"),
                    "text": tweet_data.get("text", ""),
                    "author": tweet_data.get("author", ""),
                    "tweet_id": tweet_id,
                    "trace_id": trace_id,
                    "metrics": {
                        "likes": tweet_data.get("likes", 0),
                        "retweets": tweet_data.get("retweets", 0),
                        "replies": tweet_data.get("replies", 0),
                    },
                },
            }

            kafka_producer.send_message(
                topic=raw_topic, key=tweet_data["tweetLink"], value=raw_message
            )

            # Optionally send URL to task.url.ingest for deeper processing
            if send_to_url_processor:
                url_message = {
                    "schema_version": "v1",
                    "device_id": None,
                    "timestamp": tweet_data.get("time"),
                    "trace_id": trace_id,
                    "data": {
                        "url": tweet_data["tweetLink"],
                        "source": "x.com",
                        "type": "liked_tweet",
                        "tweet_id": tweet_id,
                        "trace_id": trace_id,
                        "metadata": {
                            "author": tweet_data.get("author", ""),
                            "preview_text": tweet_data.get("text", "")[:200],
                        },
                    },
                }

                kafka_producer.send_message(
                    topic=url_topic, key=tweet_data["tweetLink"], value=url_message
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

    # Get schedule interval from environment variable (default 6 hours)
    schedule_interval_hours = int(os.getenv("LOOM_FETCH_INTERVAL_HOURS", "6"))

    # Schedule X.com likes fetching
    schedule.every(schedule_interval_hours).hours.do(run_async_fetch)
    logging.info(f"Scheduled to run every {schedule_interval_hours} hours")

    # Run immediately on startup if configured
    if os.getenv("LOOM_RUN_ON_STARTUP", "true").lower() == "true":
        logging.info("Running initial fetch on startup")
        run_async_fetch()

    # Keep the service running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


if __name__ == "__main__":
    main()
