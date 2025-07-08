#!/usr/bin/env python3
"""Test script to verify OS events are flowing through the pipeline correctly."""

import asyncio
import json
from datetime import datetime
from uuid import uuid4

import httpx
import asyncpg
from aiokafka import AIOKafkaConsumer

# Configuration
API_BASE_URL = "http://localhost:8000"
KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
DATABASE_URL = "postgresql://loom:loom@localhost:5432/loom"

# Test device ID
TEST_DEVICE_ID = str(uuid4())


async def send_test_events():
    """Send test events to all OS event endpoints."""
    headers = {"X-API-Key": "apikeyhere"}
    async with httpx.AsyncClient(headers=headers) as client:
        # Test app lifecycle event
        app_lifecycle_event = {
            "device_id": TEST_DEVICE_ID,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": "foreground",
            "app_identifier": "com.example.testapp",  # Changed from package_name
            "app_name": "Test App",
            "duration_seconds": 120,
        }

        print(f"Sending app lifecycle event: {app_lifecycle_event}")
        response = await client.post(
            f"{API_BASE_URL}/os-events/app-lifecycle", json=app_lifecycle_event
        )
        print(f"App lifecycle response: {response.status_code}")
        if response.status_code != 201:
            print(f"Error: {response.text}")

        # Test system event
        system_event = {
            "device_id": TEST_DEVICE_ID,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": "screen_on",
            "category": "screen",
            "metadata": {"brightness": 80, "auto_brightness": True},
        }

        print(f"\nSending system event: {system_event}")
        response = await client.post(
            f"{API_BASE_URL}/os-events/system", json=system_event
        )
        print(f"System event response: {response.status_code}")
        if response.status_code != 201:
            print(f"Error: {response.text}")

        # Test notification event
        notification_event = {
            "device_id": TEST_DEVICE_ID,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "notification_id": str(uuid4()),
            "app_identifier": "com.android.messaging",  # Changed from package_name
            "title": "Test Message",
            "body": "This is a test notification",  # Changed from text to body
            "action": "posted",  # Changed from event_type to action
            "metadata": {"category": "msg", "priority": 1, "app_name": "Messages"},
        }

        print(f"\nSending notification event: {notification_event}")
        response = await client.post(
            f"{API_BASE_URL}/os-events/notifications", json=notification_event
        )
        print(f"Notification response: {response.status_code}")
        if response.status_code != 201:
            print(f"Error: {response.text}")


async def check_kafka_messages():
    """Check if messages are in Kafka topics."""
    topics = [
        "os.events.app_lifecycle.raw",
        "os.events.system.raw",
        "os.events.notifications.raw",
    ]

    print("\n\nChecking Kafka topics...")

    for topic in topics:
        consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            auto_offset_reset="earliest",
            enable_auto_commit=False,
            consumer_timeout_ms=5000,
            value_deserializer=lambda x: json.loads(x.decode("utf-8")),
        )

        try:
            await consumer.start()
            print(f"\n{topic}:")

            count = 0
            async for msg in consumer:
                if msg.value.get("device_id") == TEST_DEVICE_ID:
                    count += 1
                    print(f"  Found test message: {msg.value}")

            if count == 0:
                print("  No test messages found")

        except asyncio.TimeoutError:
            print("  Topic appears empty or no new messages")
        finally:
            await consumer.stop()


async def check_database():
    """Check if events are stored in the database."""
    print("\n\nChecking database tables...")

    conn = await asyncpg.connect(DATABASE_URL)

    try:
        # Check app lifecycle events
        query = """
        SELECT COUNT(*) as count, MAX(timestamp) as latest
        FROM os_events_app_lifecycle_raw
        WHERE device_id = $1
        """
        row = await conn.fetchrow(query, TEST_DEVICE_ID)
        print(f"\nApp lifecycle events: {row['count']} records")
        if row["count"] > 0:
            print(f"  Latest: {row['latest']}")

        # Check system events
        query = """
        SELECT COUNT(*) as count, MAX(timestamp) as latest
        FROM os_events_system_raw
        WHERE device_id = $1
        """
        row = await conn.fetchrow(query, TEST_DEVICE_ID)
        print(f"\nSystem events: {row['count']} records")
        if row["count"] > 0:
            print(f"  Latest: {row['latest']}")

        # Check notification events
        query = """
        SELECT COUNT(*) as count, MAX(timestamp) as latest
        FROM os_events_notifications_raw
        WHERE device_id = $1
        """
        row = await conn.fetchrow(query, TEST_DEVICE_ID)
        print(f"\nNotification events: {row['count']} records")
        if row["count"] > 0:
            print(f"  Latest: {row['latest']}")

        # Show total counts
        print("\n\nTotal counts in database:")
        for table in [
            "os_events_app_lifecycle_raw",
            "os_events_system_raw",
            "os_events_notifications_raw",
        ]:
            query = f"SELECT COUNT(*) as count FROM {table}"
            row = await conn.fetchrow(query)
            print(f"  {table}: {row['count']} total records")

    finally:
        await conn.close()


async def main():
    """Run all tests."""
    print(f"Testing OS events pipeline with device ID: {TEST_DEVICE_ID}")
    print("=" * 60)

    # Send test events
    await send_test_events()

    # Wait for processing
    print("\nWaiting 5 seconds for events to be processed...")
    await asyncio.sleep(5)

    # Skip Kafka check when running outside Docker
    # await check_kafka_messages()

    # Check database
    await check_database()

    print("\n\nTest complete!")
    print("\nTo check real mobile app events, run:")
    print(
        '  docker exec loomv2-postgres-1 psql -U loom -d loom -c "SELECT * FROM os_events_system_raw ORDER BY timestamp DESC LIMIT 10;"'
    )


if __name__ == "__main__":
    asyncio.run(main())
