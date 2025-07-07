#!/usr/bin/env python3
"""
Test script to send properly formatted messages to Kafka topics
"""

import json
import sys
from datetime import datetime
from kafka import KafkaProducer


def send_test_messages():
    """Send test messages to various Kafka topics."""

    # Create Kafka producer
    producer = KafkaProducer(
        bootstrap_servers=["kafka:29092"],
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )

    # Test GPS message
    gps_message = {
        "device_id": "test-device-python",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "schema_version": "v1",
        "data": {
            "latitude": 37.7749,
            "longitude": -122.4194,
            "accuracy": 10.0,
            "altitude": 50.0,
            "speed": 2.5,
        },
    }

    # Test power state message
    power_message = {
        "device_id": "test-device-python",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "schema_version": "v1",
        "data": {
            "battery_level": 85,
            "is_charging": False,
            "is_plugged_in": False,
            "temperature_celsius": 25.5,
        },
    }

    # Test system event message
    system_event = {
        "device_id": "test-device-python",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "schema_version": "v1",
        "data": {
            "event_type": "screen_on",
            "event_category": "screen",
            "description": "Screen turned on",
        },
    }

    # Send messages
    print("Sending GPS message...")
    producer.send("device.sensor.gps.raw", value=gps_message)

    print("Sending power state message...")
    producer.send("device.state.power.raw", value=power_message)

    print("Sending system event message...")
    producer.send("os.events.system.raw", value=system_event)

    # Flush and close
    producer.flush()
    producer.close()

    print("\nMessages sent successfully!")
    print(f"GPS: {json.dumps(gps_message, indent=2)}")
    print(f"Power: {json.dumps(power_message, indent=2)}")
    print(f"System: {json.dumps(system_event, indent=2)}")


if __name__ == "__main__":
    try:
        send_test_messages()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
