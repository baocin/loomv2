import os
import logging
import schedule
import time
import json
from email_fetcher import EmailFetcher
from kafka_producer import KafkaProducer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - email-fetcher - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/email-fetcher.log'),
        logging.StreamHandler()
    ]
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
        
        # Send each email to Kafka
        for email_data in emails:
            message = {
                "schema_version": "v1",
                "device_id": None,
                "timestamp": email_data["date_received"].isoformat(),
                "data": email_data
            }
            
            kafka_producer.send_message(
                topic="external.email.events.raw",
                key=email_data["email_id"],
                value=message
            )
        
        logging.info(f"Successfully processed {len(emails)} emails")
        
    except Exception as e:
        logging.error(f"Error in email fetch process: {e}")

def main():
    """Main application entry point"""
    logging.info("Email fetcher service starting...")
    
    # Schedule email fetching every 5 minutes
    schedule.every(5).minutes.do(fetch_emails)
    
    # Also run immediately on startup
    fetch_emails()
    
    # Keep the service running
    while True:
        schedule.run_pending()
        time.sleep(30)

if __name__ == "__main__":
    main()