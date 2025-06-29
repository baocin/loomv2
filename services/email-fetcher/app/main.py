import os
import logging
import schedule
import time
from app.email_fetcher import EmailFetcher
from app.kafka_producer import KafkaProducer

# Configure logging
log_level = os.getenv("LOOM_LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, log_level),
    format="%(asctime)s - email-fetcher - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],  # Remove file handler for container deployments
)


def fetch_emails():
    """Fetch emails and send to Kafka"""
    try:
        logging.info("Starting email fetch process")

        # Initialize services
        email_fetcher = EmailFetcher()
        kafka_producer = KafkaProducer()

        # Fetch emails from all configured accounts
        emails = email_fetcher.fetch_all_emails()

        # Get output topic from environment
        output_topic = os.getenv("LOOM_KAFKA_OUTPUT_TOPIC", "external.email.events.raw")

        # Send each email to Kafka
        for email_data in emails:
            # Generate device_id based on account
            account_email = email_data.get("account_email", "unknown")
            account_index = email_data.get("account_index", 1)
            device_id = f"email-fetcher-account-{account_index}"

            message = {
                "schema_version": "v1",
                "device_id": device_id,
                "timestamp": email_data["date_received"].isoformat(),
                "content_hash": email_data.get(
                    "content_hash"
                ),  # Include content hash for deduplication
                "data": email_data,
            }

            # Use content_hash as key if available, otherwise fall back to email_id
            key = email_data.get("content_hash") or email_data["email_id"]
            kafka_producer.send_message(topic=output_topic, key=key, value=message)

        kafka_producer.close()

        # Count emails with content hashes for logging
        emails_with_hashes = sum(1 for e in emails if e.get("content_hash"))
        logging.info(
            f"Successfully processed {len(emails)} emails to topic {output_topic} "
            f"({emails_with_hashes} with content hashes for deduplication)"
        )

    except Exception as e:
        logging.error(f"Error in email fetch process: {e}")


def main():
    """Main application entry point"""
    logging.info("Email fetcher service starting...")

    # Get fetch interval from environment (default 5 minutes)
    fetch_interval = int(os.getenv("LOOM_EMAIL_FETCH_INTERVAL_MINUTES", "5"))
    run_on_startup = os.getenv("LOOM_EMAIL_RUN_ON_STARTUP", "true").lower() == "true"

    # Schedule email fetching
    schedule.every(fetch_interval).minutes.do(fetch_emails)
    logging.info(f"Scheduled email fetching every {fetch_interval} minutes")

    # Run immediately on startup if configured
    if run_on_startup:
        fetch_emails()

    # Keep the service running
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
