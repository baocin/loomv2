import os
import logging
import schedule
import time
from email_fetcher import EmailFetcher
from kafka_producer import KafkaProducer

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
            message = {
                "schema_version": "v1",
                "device_id": None,
                "timestamp": email_data["date_received"].isoformat(),
                "data": email_data,
            }

            kafka_producer.send_message(
                topic=output_topic, key=email_data["email_id"], value=message
            )

        kafka_producer.close()

        logging.info(
            f"Successfully processed {len(emails)} emails to topic {output_topic}"
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
