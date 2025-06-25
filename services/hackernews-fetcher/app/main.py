import os
import logging
import schedule
import time
from hackernews_fetcher import HackerNewsFetcher
from kafka_producer import KafkaProducer

# Configure logging
log_level = os.getenv("LOOM_LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, log_level),
    format="%(asctime)s - hackernews-fetcher - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],  # Remove file handler for container deployments
)


def fetch_hackernews():
    """Fetch personal Hacker News favorites/upvoted items and send URLs to Kafka for processing"""
    try:
        logging.info("Starting Hacker News personal favorites fetch process")

        # Initialize services
        hn_fetcher = HackerNewsFetcher()
        kafka_producer = KafkaProducer()

        # Get output topic from environment
        output_topic = os.getenv("LOOM_KAFKA_OUTPUT_TOPIC", "task.likes.hackernews")
        fetch_type = os.getenv(
            "LOOM_HACKERNEWS_FETCH_TYPE", "favorites"
        )  # favorites or submissions

        # Fetch user's favorites/upvoted items or submissions
        if fetch_type == "submissions":
            items = hn_fetcher.fetch_user_submissions_direct()
        else:
            items = hn_fetcher.fetch_user_favorites()

        # Send each item URL to Kafka for processing
        sent_count = 0
        for story_data in items:
            # Only process stories with URLs (not just text posts)
            if story_data.get("url"):
                message = {
                    "schema_version": "v1",
                    "device_id": None,
                    "timestamp": story_data.get("time"),
                    "data": {
                        "url": story_data["url"],
                        "source": "hackernews",
                        "type": (
                            "liked_story"
                            if fetch_type == "favorites"
                            else "submitted_story"
                        ),
                        "title": story_data.get("title"),
                        "score": story_data.get("score"),
                        "comments_url": f"https://news.ycombinator.com/item?id={story_data['id']}",
                        "story_id": story_data["id"],
                        "author": story_data.get("by"),
                        "comment_count": story_data.get("descendants", 0),
                    },
                }

                kafka_producer.send_message(
                    topic=output_topic, key=story_data["url"], value=message
                )
                sent_count += 1

        kafka_producer.close()

        logging.info(
            f"Successfully processed {sent_count} Hacker News {fetch_type} with URLs (out of {len(items)} total) to topic {output_topic}"
        )

    except Exception as e:
        logging.error(f"Error in Hacker News fetch process: {e}")


def main():
    """Main application entry point"""
    logging.info("Hacker News fetcher service starting...")

    # Get fetch interval from environment (default 2 hours = 120 minutes)
    fetch_interval = int(os.getenv("LOOM_HACKERNEWS_FETCH_INTERVAL_MINUTES", "120"))
    run_on_startup = (
        os.getenv("LOOM_HACKERNEWS_RUN_ON_STARTUP", "true").lower() == "true"
    )

    # Schedule Hacker News fetching
    if fetch_interval < 60:
        schedule.every(fetch_interval).minutes.do(fetch_hackernews)
        logging.info(f"Scheduled Hacker News fetching every {fetch_interval} minutes")
    else:
        hours = fetch_interval // 60
        schedule.every(hours).hours.do(fetch_hackernews)
        logging.info(f"Scheduled Hacker News fetching every {hours} hours")

    # Run immediately on startup if configured
    if run_on_startup:
        fetch_hackernews()

    # Keep the service running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


if __name__ == "__main__":
    main()
