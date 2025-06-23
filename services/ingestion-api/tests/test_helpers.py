"""Test helper functions and fixtures."""

import uuid
from datetime import UTC, datetime
from typing import Any


def generate_test_device_id() -> str:
    """Generate a valid UUIDv8 for testing.

    Note: For simplicity in tests, we'll use UUIDv4 which has compatible format.
    In production, clients should generate proper UUIDv8s.
    """
    return str(uuid.uuid4())


def generate_test_recorded_at() -> str:
    """Generate a valid UTC timestamp for testing."""
    return datetime.now(UTC).isoformat()


def create_base_test_data() -> dict[str, Any]:
    """Create base test data with required device_id and recorded_at."""
    return {
        "device_id": generate_test_device_id(),
        "recorded_at": generate_test_recorded_at(),
    }


def create_audio_test_data() -> dict[str, Any]:
    """Create test data for audio upload."""
    base_data = create_base_test_data()
    base_data.update(
        {
            "chunk_data": "dGVzdCBhdWRpbyBkYXRh",  # base64 "test audio data"
            "sample_rate": 44100,
            "channels": 1,
            "format": "wav",
            "duration_ms": 1000,
        },
    )
    return base_data


def create_image_test_data() -> dict[str, Any]:
    """Create test data for image upload."""
    base_data = create_base_test_data()
    base_data.update(
        {
            "image_data": "dGVzdCBpbWFnZSBkYXRh",  # base64 "test image data"
            "width": 1920,
            "height": 1080,
            "format": "jpeg",
            "camera_type": "rear",
        },
    )
    return base_data


def create_note_test_data() -> dict[str, Any]:
    """Create test data for note upload."""
    base_data = create_base_test_data()
    base_data.update(
        {
            "content": "This is a test note with some content.",
            "title": "Test Note",
            "note_type": "text",
            "tags": ["test", "example"],
            "language": "en",
        },
    )
    return base_data


def create_gps_test_data() -> dict[str, Any]:
    """Create test data for GPS sensor."""
    base_data = create_base_test_data()
    base_data.update({"latitude": 37.7749, "longitude": -122.4194, "accuracy": 5.0})
    return base_data


def create_accelerometer_test_data() -> dict[str, Any]:
    """Create test data for accelerometer sensor."""
    base_data = create_base_test_data()
    base_data.update({"x": 0.1, "y": 0.2, "z": 9.8})
    return base_data


def create_heartrate_test_data() -> dict[str, Any]:
    """Create test data for heart rate sensor."""
    base_data = create_base_test_data()
    base_data.update({"bpm": 72, "confidence": 0.95})
    return base_data


def create_power_test_data() -> dict[str, Any]:
    """Create test data for power state."""
    base_data = create_base_test_data()
    base_data.update({"battery_level": 85.5, "is_charging": True, "power_source": "AC"})
    return base_data


def create_macos_apps_test_data() -> dict[str, Any]:
    """Create test data for macOS app monitoring."""
    base_data = create_base_test_data()
    base_data.update(
        {
            "running_applications": [
                {
                    "pid": 1234,
                    "name": "TestApp",
                    "bundle_id": "com.test.app",
                    "active": True,
                    "hidden": False,
                },
            ],
        },
    )
    return base_data


def create_device_metadata_test_data() -> dict[str, Any]:
    """Create test data for device metadata."""
    base_data = create_base_test_data()
    base_data.update(
        {
            "metadata_type": "device_capabilities",
            "metadata": {"cpu": "Intel i7", "ram": "16GB", "os": "macOS 14.0"},
        },
    )
    return base_data
