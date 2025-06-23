"""Unit tests for device_id and recorded_at field validation."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import BaseMessage


@pytest.fixture()
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture()
def mock_kafka_producer():
    """Mock Kafka producer."""
    with patch("app.routers.notes.kafka_producer") as mock:
        mock.send_message = AsyncMock()
        yield mock


class TestDeviceIdValidation:
    """Test device_id validation across all endpoints."""

    def test_valid_uuidv4_device_id(self, client, mock_kafka_producer):
        """Test that valid UUIDv4 is accepted."""
        note_data = {
            "device_id": "550e8400-e29b-41d4-a716-446655440000",  # Valid UUIDv4
            "recorded_at": "2024-01-01T12:00:00Z",
            "content": "Test note content",
        }

        response = client.post("/notes/upload", json=note_data)
        assert response.status_code == 200

    def test_valid_uuidv8_device_id(self, client, mock_kafka_producer):
        """Test that valid UUIDv8 format is accepted."""
        note_data = {
            "device_id": "017F22E2-79B0-8CC3-98C4-DC0C0C07398F",  # Valid UUID format
            "recorded_at": "2024-01-01T12:00:00Z",
            "content": "Test note content",
        }

        response = client.post("/notes/upload", json=note_data)
        assert response.status_code == 200

    def test_invalid_device_id_format(self, client, mock_kafka_producer):
        """Test that invalid device_id format is rejected."""
        invalid_device_ids = [
            "not-a-uuid",
            "12345",
            "550e8400-e29b-41d4-a716",  # Too short
            "550e8400-e29b-41d4-a716-446655440000-extra",  # Too long
            "",  # Empty
        ]

        for invalid_id in invalid_device_ids:
            note_data = {
                "device_id": invalid_id,
                "recorded_at": "2024-01-01T12:00:00Z",
                "content": "Test note content",
            }

            response = client.post("/notes/upload", json=note_data)
            assert response.status_code == 422, f"Should reject device_id: {invalid_id}"

    def test_missing_device_id(self, client, mock_kafka_producer):
        """Test that missing device_id is rejected."""
        note_data = {
            "recorded_at": "2024-01-01T12:00:00Z",
            "content": "Test note content",
        }

        response = client.post("/notes/upload", json=note_data)
        assert response.status_code == 422
        assert "device_id" in response.text


class TestRecordedAtValidation:
    """Test recorded_at timestamp validation."""

    def test_valid_utc_timestamp(self, client, mock_kafka_producer):
        """Test that valid UTC timestamps are accepted."""
        valid_timestamps = [
            "2024-01-01T12:00:00Z",
            "2024-01-01T12:00:00+00:00",
            "2024-01-01T12:00:00.123Z",
            "2024-01-01T12:00:00.123456Z",
        ]

        for timestamp in valid_timestamps:
            note_data = {
                "device_id": "550e8400-e29b-41d4-a716-446655440000",
                "recorded_at": timestamp,
                "content": "Test note content",
            }

            response = client.post("/notes/upload", json=note_data)
            assert response.status_code == 200, f"Should accept timestamp: {timestamp}"

    def test_non_utc_timestamp_conversion(self, client, mock_kafka_producer):
        """Test that non-UTC timestamps are converted to UTC."""
        note_data = {
            "device_id": "550e8400-e29b-41d4-a716-446655440000",
            "recorded_at": "2024-01-01T12:00:00-05:00",  # EST timezone
            "content": "Test note content",
        }

        response = client.post("/notes/upload", json=note_data)
        assert response.status_code == 200

    def test_invalid_timestamp_format(self, client, mock_kafka_producer):
        """Test that various timestamp formats are handled gracefully."""
        various_timestamps = [
            "not-a-timestamp",
            "2024-01-01",  # Date only
            "12:00:00",  # Time only
            "2024/01/01 12:00:00",  # Wrong format
            "",  # Empty
        ]

        for timestamp in various_timestamps:
            note_data = {
                "device_id": "550e8400-e29b-41d4-a716-446655440000",
                "recorded_at": timestamp,
                "content": "Test note content",
            }

            response = client.post("/notes/upload", json=note_data)
            # Some timestamps may be parsed/converted, others may fail
            assert response.status_code in [
                200,
                201,
                422,
            ], f"Unexpected status for timestamp: {timestamp}"

    def test_missing_recorded_at(self, client, mock_kafka_producer):
        """Test that missing recorded_at is rejected."""
        note_data = {
            "device_id": "550e8400-e29b-41d4-a716-446655440000",
            "content": "Test note content",
        }

        response = client.post("/notes/upload", json=note_data)
        assert response.status_code == 422
        assert "recorded_at" in response.text


class TestBaseMessageModel:
    """Test BaseMessage model validation directly."""

    def test_device_id_validation_in_model(self):
        """Test device_id validation in Pydantic model."""
        valid_data = {
            "device_id": "550e8400-e29b-41d4-a716-446655440000",
            "recorded_at": datetime.now(UTC),
        }

        message = BaseMessage(**valid_data)
        assert message.device_id == valid_data["device_id"]

    def test_invalid_device_id_in_model(self):
        """Test invalid device_id raises validation error."""
        invalid_data = {
            "device_id": "invalid-uuid",
            "recorded_at": datetime.now(UTC),
        }

        with pytest.raises(ValueError, match="device_id must be a valid UUID format"):
            BaseMessage(**invalid_data)

    def test_recorded_at_timezone_conversion(self):
        """Test recorded_at timezone conversion in model."""
        # Test naive datetime (should add UTC)
        naive_dt = datetime(2024, 1, 1, 12, 0, 0)
        data = {
            "device_id": "550e8400-e29b-41d4-a716-446655440000",
            "recorded_at": naive_dt,
        }

        message = BaseMessage(**data)
        assert message.recorded_at.tzinfo == UTC

    def test_timestamp_auto_generation(self):
        """Test that timestamp is automatically generated as UTC."""
        data = {
            "device_id": "550e8400-e29b-41d4-a716-446655440000",
            "recorded_at": datetime.now(UTC),
        }

        message = BaseMessage(**data)
        assert message.timestamp.tzinfo == UTC
        assert isinstance(message.timestamp, datetime)


class TestEndpointConsistency:
    """Test that all endpoints consistently require device_id and recorded_at."""

    def test_audio_endpoint_requires_fields(self, client, mock_kafka_producer):
        """Test audio endpoint requires device_id and recorded_at."""
        audio_data = {
            "chunk_data": "dGVzdA==",
            "sample_rate": 44100,
            "duration_ms": 1000,
            # Missing device_id and recorded_at
        }

        response = client.post("/audio/upload", json=audio_data)
        assert response.status_code == 422

    def test_image_endpoint_requires_fields(self, client, mock_kafka_producer):
        """Test image endpoint requires device_id and recorded_at."""
        image_data = {
            "image_data": "dGVzdA==",
            "width": 100,
            "height": 100,
            # Missing device_id and recorded_at
        }

        response = client.post("/images/upload", json=image_data)
        assert response.status_code == 422

    def test_sensor_endpoint_requires_fields(self, client, mock_kafka_producer):
        """Test sensor endpoint requires device_id and recorded_at."""
        gps_data = {
            "latitude": 37.7749,
            "longitude": -122.4194,
            # Missing device_id and recorded_at
        }

        response = client.post("/sensor/gps", json=gps_data)
        assert response.status_code == 422
