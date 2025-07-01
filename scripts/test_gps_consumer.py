#!/usr/bin/env python3
"""Test script to send GPS messages to Kafka and verify geocoding consumer"""

import json
import time
from kafka import KafkaProducer
from datetime import datetime

# Create producer
producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Test GPS message
test_message = {
    "device_id": "test_device_001",
    "latitude": 40.7128,  # New York City
    "longitude": -74.0060,
    "accuracy": 10.0,
    "timestamp": datetime.utcnow().isoformat() + "Z",
    "altitude": 50.0,
    "speed": 0.0,
    "bearing": 0.0,
    "schema_version": "v1"
}

print("Sending test GPS message:")
print(json.dumps(test_message, indent=2))

# Send message
future = producer.send(
    'device.sensor.gps.raw',
    key=test_message['device_id'].encode('utf-8'),
    value=test_message
)

# Wait for send
result = future.get(timeout=10)
print(f"\nMessage sent to {result.topic} partition {result.partition} offset {result.offset}")

# Flush and close
producer.flush()
producer.close()

print("\nNow check the consumer logs and location.address.geocoded topic for output...")