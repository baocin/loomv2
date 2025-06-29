"""Test helper functions and fixtures for moondream-ocr service."""

import base64
import uuid
from datetime import datetime, timezone
from io import BytesIO
from typing import Any

from PIL import Image


def generate_test_device_id() -> str:
    """Generate a valid UUIDv4 for testing."""
    return str(uuid.uuid4())


def generate_test_recorded_at() -> str:
    """Generate a valid UTC timestamp for testing."""
    return datetime.now(timezone.utc).isoformat()


def create_test_image_base64() -> str:
    """Create a simple test image encoded as base64."""
    # Create a simple RGB image with some text-like patterns
    img = Image.new("RGB", (200, 100), color="white")

    # Add some simple patterns that could be interpreted as text
    pixels = img.load()

    # Create horizontal lines that might look like text
    for y in range(20, 30):
        for x in range(20, 180):
            pixels[x, y] = (0, 0, 0)  # Black line

    for y in range(40, 50):
        for x in range(20, 140):
            pixels[x, y] = (0, 0, 0)  # Black line

    for y in range(60, 70):
        for x in range(20, 160):
            pixels[x, y] = (0, 0, 0)  # Black line

    # Convert to base64
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    img_bytes = buffer.getvalue()
    return base64.b64encode(img_bytes).decode("utf-8")


def create_test_twitter_image_message() -> dict[str, Any]:
    """Create a test Kafka message for Twitter image processing."""
    return {
        "schema_version": "v1",
        "trace_id": str(uuid.uuid4()),
        "device_id": generate_test_device_id(),
        "recorded_at": generate_test_recorded_at(),
        "data": {
            "tweet_id": "1234567890",
            "tweet_url": "https://twitter.com/user/status/1234567890",
            "image_data": create_test_image_base64(),
            "metadata": {"user": "test_user", "timestamp": generate_test_recorded_at()},
        },
    }


def create_ocr_request_data() -> dict[str, Any]:
    """Create test data for OCR API request."""
    return {
        "image_data": create_test_image_base64(),
        "prompt": "Extract all text from this image.",
    }


def create_expected_ocr_response() -> dict[str, Any]:
    """Create expected OCR response structure."""
    return {
        "ocr_text": "Sample extracted text",
        "description": "Sample image description",
        "success": True,
        "error": None,
        "processing_time_ms": 100.0,
    }


def create_kafka_message_with_base64_prefix() -> dict[str, Any]:
    """Create Kafka message with data:image/png;base64 prefix."""
    message = create_test_twitter_image_message()
    message["data"][
        "image_data"
    ] = f"data:image/png;base64,{message['data']['image_data']}"
    return message
