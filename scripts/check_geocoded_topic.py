#!/usr/bin/env python3
"""Check if messages are in the location.address.geocoded topic"""

import json
from kafka import KafkaConsumer

consumer = KafkaConsumer(
    'location.address.geocoded',
    bootstrap_servers=['localhost:9092'],
    auto_offset_reset='earliest',
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    consumer_timeout_ms=5000  # 5 second timeout
)

print("Checking location.address.geocoded topic...")
message_count = 0

try:
    for message in consumer:
        message_count += 1
        print(f"\nMessage {message_count}:")
        print(f"  Partition: {message.partition}, Offset: {message.offset}")
        print(f"  Key: {message.key.decode('utf-8') if message.key else None}")
        print(f"  Value: {json.dumps(message.value, indent=2)}")
except:
    pass

print(f"\nTotal messages found: {message_count}")
consumer.close()