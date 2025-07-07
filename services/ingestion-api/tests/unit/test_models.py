"""Unit tests for pydantic models."""

from datetime import datetime
from uuid import uuid4

import pytest

from app.models import (
    AccelerometerReading,
    AudioChunk,
    GPSReading,
    HealthCheck,
    HeartRateReading,
    LockState,
    PowerState,
    SensorReading,
    WebSocketMessage,
)


class TestBaseMessage:
    """Test the BaseMessage functionality."""

    def test_audio_chunk_creation(self):
        """Test AudioChunk model creation."""
        audio_chunk = AudioChunk(
            device_id="test-device",
            chunk_data=b"test audio data",
            sample_rate=44100,
            channels=1,
            format="wav",
            duration_ms=1000,
        )

        assert audio_chunk.device_id == "test-device"
        assert audio_chunk.chunk_data == b"test audio data"
        assert audio_chunk.sample_rate == 44100
        assert audio_chunk.channels == 1
        assert audio_chunk.format == "wav"
        assert audio_chunk.duration_ms == 1000
        assert audio_chunk.schema_version == "1.0"
        assert isinstance(audio_chunk.timestamp, datetime)
        assert isinstance(audio_chunk.message_id, str)

    def test_audio_chunk_with_file_id(self):
        """Test AudioChunk with file_id for chunking."""
        file_id = str(uuid4())
        audio_chunk = AudioChunk(
            device_id="test-device",
            chunk_data=b"test chunk",
            sample_rate=16000,
            duration_ms=500,
            file_id=file_id,
        )

        assert audio_chunk.file_id == file_id


class TestSensorModels:
    """Test sensor-specific models."""

    def test_gps_reading(self):
        """Test GPSReading model."""
        gps_reading = GPSReading(
            device_id="test-device",
            latitude=37.7749,
            longitude=-122.4194,
            altitude=50.0,
            accuracy=5.0,
            heading=180.0,
            speed=10.5,
        )

        assert gps_reading.device_id == "test-device"
        assert gps_reading.latitude == 37.7749
        assert gps_reading.longitude == -122.4194
        assert gps_reading.altitude == 50.0
        assert gps_reading.accuracy == 5.0
        assert gps_reading.heading == 180.0
        assert gps_reading.speed == 10.5

    def test_gps_reading_minimal(self):
        """Test GPSReading with minimal required fields."""
        gps_reading = GPSReading(
            device_id="test-device",
            latitude=37.7749,
            longitude=-122.4194,
        )

        assert gps_reading.latitude == 37.7749
        assert gps_reading.longitude == -122.4194
        assert gps_reading.altitude is None
        assert gps_reading.accuracy is None

    def test_accelerometer_reading(self):
        """Test AccelerometerReading model."""
        accel_reading = AccelerometerReading(
            device_id="test-device",
            x=0.5,
            y=-0.3,
            z=9.8,
        )

        assert accel_reading.device_id == "test-device"
        assert accel_reading.x == 0.5
        assert accel_reading.y == -0.3
        assert accel_reading.z == 9.8

    def test_heart_rate_reading(self):
        """Test HeartRateReading model."""
        hr_reading = HeartRateReading(
            device_id="test-device",
            bpm=72,
            confidence=0.95,
        )

        assert hr_reading.device_id == "test-device"
        assert hr_reading.bpm == 72
        assert hr_reading.confidence == 0.95

    def test_power_state(self):
        """Test PowerState model."""
        power_state = PowerState(
            device_id="test-device",
            battery_level=85.5,
            is_charging=True,
            power_source="USB",
        )

        assert power_state.device_id == "test-device"
        assert power_state.battery_level == 85.5
        assert power_state.is_charging is True
        assert power_state.power_source == "USB"

    def test_lock_state(self):
        """Test LockState model."""
        lock_timestamp = datetime(2025, 7, 7, 12, 0, 0)
        lock_state = LockState(
            device_id="test-device",
            is_locked=True,
            lock_type="biometric",
            lock_timestamp=lock_timestamp,
        )

        assert lock_state.device_id == "test-device"
        assert lock_state.is_locked is True
        assert lock_state.lock_type == "biometric"
        assert lock_state.lock_timestamp == lock_timestamp
        assert lock_state.schema_version == "1.0"
        assert isinstance(lock_state.timestamp, datetime)
        assert isinstance(lock_state.message_id, str)

    def test_lock_state_minimal(self):
        """Test LockState with minimal required fields."""
        lock_state = LockState(
            device_id="test-device",
            is_locked=False,
        )

        assert lock_state.device_id == "test-device"
        assert lock_state.is_locked is False
        assert lock_state.lock_type is None
        assert lock_state.lock_timestamp is None

    def test_generic_sensor_reading(self):
        """Test generic SensorReading model."""
        sensor_reading = SensorReading(
            device_id="test-device",
            sensor_type="temperature",
            value={"temperature": 23.5, "humidity": 45.0},
            unit="celsius",
            accuracy=0.1,
        )

        assert sensor_reading.device_id == "test-device"
        assert sensor_reading.sensor_type == "temperature"
        assert sensor_reading.value["temperature"] == 23.5
        assert sensor_reading.value["humidity"] == 45.0
        assert sensor_reading.unit == "celsius"
        assert sensor_reading.accuracy == 0.1


class TestWebSocketMessage:
    """Test WebSocket message wrapper."""

    def test_websocket_message_creation(self):
        """Test WebSocketMessage creation."""
        message = WebSocketMessage(
            message_type="audio_chunk",
            data={
                "chunk_data": "base64encodeddata",
                "sample_rate": 44100,
                "duration_ms": 1000,
            },
        )

        assert message.message_type == "audio_chunk"
        assert message.data["chunk_data"] == "base64encodeddata"
        assert message.data["sample_rate"] == 44100
        assert message.data["duration_ms"] == 1000


class TestHealthCheck:
    """Test health check model."""

    def test_health_check_creation(self):
        """Test HealthCheck model creation."""
        health = HealthCheck(
            status="healthy",
            version="0.1.0",
            kafka_connected=True,
        )

        assert health.status == "healthy"
        assert health.version == "0.1.0"
        assert health.kafka_connected is True
        assert isinstance(health.timestamp, datetime)

    def test_health_check_defaults(self):
        """Test HealthCheck with default values."""
        health = HealthCheck(kafka_connected=False)

        assert health.status == "healthy"
        assert health.version == "0.1.0"
        assert health.kafka_connected is False


class TestModelValidation:
    """Test model validation and error handling."""

    def test_missing_required_field(self):
        """Test validation error for missing required field."""
        with pytest.raises(ValueError):
            AudioChunk(
                # Missing device_id
                chunk_data=b"test",
                sample_rate=44100,
                duration_ms=1000,
            )

    def test_invalid_gps_coordinates(self):
        """Test GPS coordinate validation."""
        # This should work - no validation constraints set
        gps_reading = GPSReading(
            device_id="test-device",
            latitude=200.0,  # Invalid latitude (should be -90 to 90)
            longitude=200.0,  # Invalid longitude (should be -180 to 180)
        )

        # Note: Add coordinate validation constraints to the model if needed
        assert gps_reading.latitude == 200.0
        assert gps_reading.longitude == 200.0
