"""Shared test fixtures and configuration."""

import os
import sys
from pathlib import Path

import pytest

# Add app directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set test environment variables
os.environ["LOOM_ENVIRONMENT"] = "test"
os.environ["LOOM_LOG_LEVEL"] = "ERROR"


@pytest.fixture
def test_image_base64():
    """Provide a simple test image as base64."""
    # 1x1 white pixel PNG
    return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="


@pytest.fixture
def sample_image_message(test_image_base64):
    """Provide a sample image message."""
    from datetime import datetime

    return {
        "device_id": "test-device-001",
        "recorded_at": datetime.utcnow().isoformat(),
        "schema_version": "v1",
        "data": test_image_base64,
        "format": "png",
        "metadata": {
            "width": 1,
            "height": 1,
            "test": True,
        },
    }
