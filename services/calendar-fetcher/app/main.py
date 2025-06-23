import os
import logging
import schedule
import time
import json
from calendar_fetcher import CalendarFetcher
from kafka_producer import KafkaProducer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - calendar-fetcher - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/calendar-fetcher.log'),
        logging.StreamHandler()
    ]
)

def fetch_calendar_events():
    """Fetch calendar events and send to Kafka"""
    try:
        logging.info("Starting calendar fetch process")
        
        # Initialize services
        calendar_fetcher = CalendarFetcher()
        kafka_producer = KafkaProducer()
        
        # Fetch events from all configured calendars
        events = calendar_fetcher.fetch_all_calendar_events()
        
        # Send each event to Kafka
        for event_data in events:
            message = {
                "schema_version": "v1",
                "device_id": None,
                "timestamp": event_data["start_time"].isoformat() if event_data["start_time"] else None,
                "data": event_data
            }
            
            kafka_producer.send_message(
                topic="external.calendar.events.raw",
                key=event_data["event_id"],
                value=message
            )
        
        logging.info(f"Successfully processed {len(events)} calendar events")
        
    except Exception as e:
        logging.error(f"Error in calendar fetch process: {e}")

def main():
    """Main application entry point"""
    logging.info("Calendar fetcher service starting...")
    
    # Schedule calendar fetching every 30 minutes
    schedule.every(30).minutes.do(fetch_calendar_events)
    
    # Also run immediately on startup
    fetch_calendar_events()
    
    # Keep the service running
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main()