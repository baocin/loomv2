"""Common test fixtures for kafka-to-db-consumer tests."""

from unittest.mock import AsyncMock

import asyncpg
import pytest
from aiokafka import AIOKafkaConsumer


@pytest.fixture
def mock_db_pool():
    """Mock database connection pool."""
    pool = AsyncMock(spec=asyncpg.Pool)
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=None)
    pool.acquire = AsyncMock()
    pool.acquire().__aenter__ = AsyncMock(return_value=conn)
    pool.acquire().__aexit__ = AsyncMock(return_value=None)
    pool.close = AsyncMock()
    return pool


@pytest.fixture
def mock_kafka_consumer():
    """Mock Kafka consumer."""
    consumer = AsyncMock(spec=AIOKafkaConsumer)
    consumer.start = AsyncMock()
    consumer.stop = AsyncMock()
    consumer.__aiter__ = AsyncMock()
    return consumer


@pytest.fixture
def sample_gps_message():
    """Sample GPS sensor message."""
    return {
        "schema_version": "v1",
        "device_id": "test-device-1",
        "timestamp": "2025-06-26T12:00:00Z",
        "trace_id": "test-trace-123",
        "data": {
            "latitude": 37.7749,
            "longitude": -122.4194,
            "altitude": 100.5,
            "accuracy": 5.0,
            "speed": 10.5,
            "heading": 180.0,
        },
        "metadata": {"activity": "walking"},
    }


@pytest.fixture
def sample_power_message():
    """Sample power state message."""
    return {
        "schema_version": "v1",
        "device_id": "test-device-1",
        "timestamp": "2025-06-26T12:00:00Z",
        "trace_id": "test-trace-456",
        "data": {
            "battery_level": 75,
            "is_charging": True,
            "is_plugged_in": True,
            "temperature_celsius": 25.5,
            "voltage": 3.8,
        },
        "metadata": {},
    }


@pytest.fixture
def sample_twitter_message():
    """Sample Twitter liked message."""
    return {
        "schema_version": "v1",
        "device_id": "test-device-1",
        "timestamp": "2025-06-26T12:00:00Z",
        "trace_id": "test-trace-789",
        "data": {
            "tweet_id": "1234567890",
            "tweet_url": "https://twitter.com/user/status/1234567890",
            "tweet_text": "This is a test tweet",
            "author_username": "testuser",
            "author_display_name": "Test User",
            "created_at": "2025-06-26T11:00:00Z",
            "like_count": 100,
            "retweet_count": 50,
            "reply_count": 25,
            "is_retweet": False,
            "has_media": True,
            "media_urls": ["https://example.com/image.jpg"],
        },
        "metadata": {"fetched_at": "2025-06-26T12:00:00Z", "user_agent": "test-agent"},
    }


@pytest.fixture
def sample_mapping_config():
    """Sample topic mapping configuration."""
    return {
        "schema_version": "v1",
        "defaults": {
            "upsert_key": "trace_id, timestamp",
            "conflict_strategy": "ignore",
            "timestamp_field": "timestamp",
            "device_id_field": "device_id",
            "schema_version_field": "schema_version",
        },
        "topics": {
            "device.sensor.gps.raw": {
                "table": "device_sensor_gps_raw",
                "description": "GPS location data",
                "field_mappings": {
                    "trace_id": "trace_id",
                    "device_id": "device_id",
                    "timestamp": "timestamp",
                    "schema_version": "schema_version",
                    "data.latitude": "latitude",
                    "data.longitude": "longitude",
                    "data.altitude": "altitude",
                    "data.accuracy": "accuracy",
                    "data.speed": "speed",
                    "data.heading": "bearing",
                },
                "data_types": {
                    "latitude": "float",
                    "longitude": "float",
                    "altitude": "float",
                    "accuracy": "float",
                    "speed": "float",
                    "bearing": "float",
                    "timestamp": "timestamp",
                },
                "required_fields": [
                    "trace_id",
                    "device_id",
                    "timestamp",
                    "data.latitude",
                    "data.longitude",
                ],
            }
        },
    }
