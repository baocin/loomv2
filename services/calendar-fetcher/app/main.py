import os
import logging
import schedule
import time
from calendar_fetcher import CalendarFetcher
from kafka_producer import KafkaProducer

# Configure logging
log_level = os.getenv("LOOM_LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, log_level),
    format="%(asctime)s - calendar-fetcher - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],  # Remove file handler for container deployments
)


def fetch_calendar_events():
    """Fetch calendar events and send to Kafka"""
    try:
        logging.info("Starting calendar fetch process")

        # Initialize services
        calendar_fetcher = CalendarFetcher()
        kafka_producer = KafkaProducer()

        # Get output topic from environment
        output_topic = os.getenv(
            "LOOM_KAFKA_OUTPUT_TOPIC", "external.calendar.events.raw"
        )

        # Fetch events from all configured calendars
        events = calendar_fetcher.fetch_all_calendar_events()

        # Send each event to Kafka
        for event_data in events:
            # Generate device_id based on calendar
            calendar_name = event_data.get("calendar_name", "default")
            calendar_index = event_data.get("calendar_index", 1)
            device_id = f"calendar-fetcher-{calendar_name.lower().replace(' ', '-')}"

            message = {
                "schema_version": "v1",
                "device_id": device_id,
                "timestamp": (
                    event_data["start_time"].isoformat()
                    if event_data["start_time"]
                    else None
                ),
                "data": event_data,
            }

            kafka_producer.send_message(
                topic=output_topic, key=event_data["event_id"], value=message
            )

        kafka_producer.close()

        logging.info(
            f"Successfully processed {len(events)} calendar events to topic {output_topic}"
        )

    except Exception as e:
        logging.error(f"Error in calendar fetch process: {e}")


def main():
    """Main application entry point"""
    logging.info("Calendar fetcher service starting...")

    # Get fetch interval from environment (default 30 minutes)
    fetch_interval = int(os.getenv("LOOM_CALENDAR_FETCH_INTERVAL_MINUTES", "30"))
    run_on_startup = os.getenv("LOOM_CALENDAR_RUN_ON_STARTUP", "true").lower() == "true"

    # Schedule calendar fetching
    schedule.every(fetch_interval).minutes.do(fetch_calendar_events)
    logging.info(f"Scheduled calendar fetching every {fetch_interval} minutes")

    # Run immediately on startup if configured
    if run_on_startup:
        fetch_calendar_events()

    # Keep the service running
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
