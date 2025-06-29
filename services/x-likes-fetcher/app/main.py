import os
import logging
import schedule
import time
import asyncio
import uuid
from x_likes_fetcher import XLikesFetcher
from kafka_producer import KafkaProducer
from db_checker import DatabaseChecker

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
    db_checker = None
    try:
        logging.info("Starting X.com likes fetch process")

        # Initialize services
        x_fetcher = XLikesFetcher()
        kafka_producer = KafkaProducer()

        # Initialize database checker
        database_url = os.getenv(
            "LOOM_DATABASE_URL", "postgresql://loom:loom@postgres:5432/loom"
        )
        db_checker = DatabaseChecker(database_url)
        await db_checker.connect()

        # Setup browser and login
        await x_fetcher.setup()

        # Fetch ALL liked tweets first (no limits)
        logging.info("Fetching all liked tweets from X.com...")
        liked_tweets = await x_fetcher.scrape_likes()
        logging.info(
            f"Scraping completed. Found {len(liked_tweets)} total liked tweets"
        )

        # Get existing tweet IDs from database for duplicate checking
        existing_tweet_ids = await db_checker.get_existing_tweet_ids()
        logging.info(f"Found {len(existing_tweet_ids)} existing tweets in database")

        # Get output topics from environment variables
        raw_topic = os.getenv("LOOM_KAFKA_OUTPUT_TOPIC", "external.twitter.liked.raw")
        url_topic = os.getenv("LOOM_KAFKA_URL_TOPIC", "task.url.ingest")
        send_to_url_processor = (
            os.getenv("LOOM_SEND_TO_URL_PROCESSOR", "true").lower() == "true"
        )

        logging.info(f"Using raw data topic: {raw_topic}")
        if send_to_url_processor:
            logging.info(f"Using URL ingest topic: {url_topic}")

        # Filter out already processed tweets and send new ones to Kafka
        new_tweets = 0
        skipped_tweets = 0

        for tweet_data in liked_tweets:
            # Generate a trace ID for this tweet
            trace_id = str(uuid.uuid4())

            # Extract tweet ID from URL
            tweet_id = (
                tweet_data["tweetLink"].split("/")[-1]
                if tweet_data.get("tweetLink")
                else None
            )

            # Skip if tweet already exists in database
            if tweet_id and tweet_id in existing_tweet_ids:
                skipped_tweets += 1
                logging.debug(f"Skipping already processed tweet: {tweet_id}")
                continue

            new_tweets += 1
            logging.info(f"Processing new tweet {new_tweets}: {tweet_id}")

            # Send complete tweet data to raw topic
            raw_message = {
                "schema_version": "v1",
                "device_id": "x-likes-fetcher-default",
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

        # Get processing statistics
        stats = await db_checker.get_processing_stats()

        # Cleanup
        await x_fetcher.cleanup()
        kafka_producer.close()
        await db_checker.disconnect()

        # Log comprehensive summary
        logging.info(
            f"Fetch completed - Total found: {len(liked_tweets)}, "
            f"New: {new_tweets}, Skipped (already processed): {skipped_tweets}"
        )
        logging.info(
            f"Database stats - Total processed: {stats['total_processed']}, "
            f"With screenshots: {stats['with_screenshots']}, "
            f"Errors: {stats['errors']}"
        )

    except Exception as e:
        logging.error(f"Error in X.com likes fetch process: {e}")
        # Ensure database connection is cleaned up on error
        if db_checker:
            try:
                await db_checker.disconnect()
            except Exception as cleanup_error:
                logging.error(f"Error during cleanup: {cleanup_error}")


def run_async_fetch():
    """Wrapper to run async function in scheduler"""
    asyncio.run(fetch_liked_tweets())


def main():
    """Main application entry point"""
    logging.info("X.com likes fetcher service starting...")

    # Get schedule interval from environment variable (fixed at 6 hours)
    schedule_interval_hours = 6

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
