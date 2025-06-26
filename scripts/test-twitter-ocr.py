#!/usr/bin/env python3
"""Test script to send a Twitter screenshot to MiniCPM-Vision for OCR."""

import base64
import json
import time
from kafka import KafkaProducer

def main():
    # Create Kafka producer
    producer = KafkaProducer(
        bootstrap_servers=['localhost:9092'],
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    
    # Create a test image message
    test_message = {
        "schema_version": "v1",
        "device_id": "test-twitter-ocr",
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "data": {
            "tweet_id": "test_tweet_123",
            "tweet_url": "https://twitter.com/test/status/123",
            "screenshot_path": "/app/screenshots/test_tweet.png",
            "trace_id": "test-trace-123",
            # For testing, we'll send a base64 encoded test image
            # In production, this would be the actual screenshot data
            "image_data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
            "metadata": {
                "source": "x-url-processor",
                "processing_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
        }
    }
    
    # Send to Twitter images topic
    producer.send('external.twitter.images.raw', value=test_message)
    producer.flush()
    
    print("Test message sent to external.twitter.images.raw topic")
    print(json.dumps(test_message, indent=2))

if __name__ == "__main__":
    main()