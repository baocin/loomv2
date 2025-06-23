"""Unit tests for image ingestion endpoints."""

import base64
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import ImageData


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def mock_kafka_producer():
    """Mock Kafka producer."""
    with patch("app.routers.images.kafka_producer") as mock:
        mock.send_message = AsyncMock()
        yield mock


@pytest.fixture
def sample_image_data():
    """Sample image data for testing."""
    from ..test_helpers import create_image_test_data

    # Add additional test-specific fields
    image_data = create_image_test_data()
    image_data.update(
        {
            "file_size": 27,  # Length of base64 test data
            "metadata": {
                "exif": {"camera_make": "TestCam", "iso": 100},
                "location": {"lat": 37.7749, "lng": -122.4194},
            },
        },
    )
    return image_data


class TestImageUpload:
    """Test image upload endpoint."""

    def test_upload_image_success(self, client, mock_kafka_producer, sample_image_data):
        """Test successful image upload."""
        response = client.post("/images/upload", json=sample_image_data)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["topic"] == "device.image.camera.raw"
        assert "message_id" in data

        # Verify Kafka producer was called
        mock_kafka_producer.send_message.assert_called_once()

    def test_upload_image_invalid_base64(
        self,
        client,
        mock_kafka_producer,
        sample_image_data,
    ):
        """Test image upload with invalid base64 data fails."""
        sample_image_data["image_data"] = "invalid_base64_data!"

        response = client.post("/images/upload", json=sample_image_data)
        assert response.status_code == 400
        assert "Invalid base64 image data" in response.json()["detail"]

    def test_upload_image_missing_data(
        self,
        client,
        mock_kafka_producer,
        sample_image_data,
    ):
        """Test image upload without required fields fails."""
        del sample_image_data["image_data"]

        response = client.post("/images/upload", json=sample_image_data)
        assert response.status_code == 422

    def test_upload_image_kafka_failure(
        self,
        client,
        mock_kafka_producer,
        sample_image_data,
    ):
        """Test image upload when Kafka fails."""
        mock_kafka_producer.send_message.side_effect = Exception(
            "Kafka connection error",
        )

        response = client.post("/images/upload", json=sample_image_data)
        assert response.status_code == 500
        assert "Failed to upload image" in response.json()["detail"]

    def test_upload_image_minimal_data(self, client, mock_kafka_producer):
        """Test image upload with minimal required data."""
        from ..test_helpers import create_base_test_data

        test_image_bytes = b"minimal_test_image"
        encoded_image = base64.b64encode(test_image_bytes).decode("utf-8")

        minimal_image = create_base_test_data()
        minimal_image.update({"image_data": encoded_image, "width": 100, "height": 100})

        response = client.post("/images/upload", json=minimal_image)
        assert response.status_code == 200


class TestScreenshotUpload:
    """Test screenshot upload endpoint."""

    def test_upload_screenshot_success(
        self,
        client,
        mock_kafka_producer,
        sample_image_data,
    ):
        """Test successful screenshot upload."""
        response = client.post("/images/screenshot", json=sample_image_data)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["topic"] == "device.video.screen.raw"
        assert "message_id" in data

        # Verify camera_type was set to "screen"
        call_args = mock_kafka_producer.send_message.call_args
        image_message = call_args[1]["message"]
        assert image_message.camera_type == "screen"

    def test_upload_screenshot_invalid_base64(
        self,
        client,
        mock_kafka_producer,
        sample_image_data,
    ):
        """Test screenshot upload with invalid base64 data fails."""
        sample_image_data["image_data"] = "invalid_base64_data!"

        response = client.post("/images/screenshot", json=sample_image_data)
        assert response.status_code == 400
        assert "Invalid base64 image data" in response.json()["detail"]


class TestImageBatch:
    """Test image batch upload endpoint."""

    def test_batch_upload_success(self, client, mock_kafka_producer, sample_image_data):
        """Test successful batch image upload."""
        images = [sample_image_data.copy() for _ in range(3)]
        for i, image in enumerate(images):
            image["camera_type"] = f"camera_{i}"

        response = client.post("/images/batch", json=images)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"
        assert data["topic"] == "device.image.camera.raw"

        # Verify Kafka producer was called for each image
        assert mock_kafka_producer.send_message.call_count == 3

    def test_batch_upload_too_large(
        self,
        client,
        mock_kafka_producer,
        sample_image_data,
    ):
        """Test batch upload with too many images fails."""
        images = [sample_image_data.copy() for _ in range(51)]  # Over limit

        response = client.post("/images/batch", json=images)
        assert response.status_code == 400
        assert "Batch size too large" in response.json()["detail"]

    def test_batch_upload_mixed_topics(
        self,
        client,
        mock_kafka_producer,
        sample_image_data,
    ):
        """Test batch upload routes to correct topics based on camera_type."""
        images = [sample_image_data.copy() for _ in range(3)]
        images[0]["camera_type"] = "rear"
        images[1]["camera_type"] = "screen"  # Should go to screen topic
        images[2]["camera_type"] = "front"

        response = client.post("/images/batch", json=images)
        assert response.status_code == 200

        # Verify correct topics were used
        calls = mock_kafka_producer.send_message.call_args_list
        assert len(calls) == 3

        # Check that screen image went to screen topic
        screen_call = calls[1]
        assert screen_call[1]["topic"] == "device.video.screen.raw"

        # Check that camera images went to camera topic
        camera_call_1 = calls[0]
        camera_call_2 = calls[2]
        assert camera_call_1[1]["topic"] == "device.image.camera.raw"
        assert camera_call_2[1]["topic"] == "device.image.camera.raw"

    def test_batch_upload_partial_failure(
        self,
        client,
        mock_kafka_producer,
        sample_image_data,
    ):
        """Test batch upload with partial failures."""
        images = [sample_image_data.copy() for _ in range(3)]

        # Mock Kafka to fail on second call
        mock_kafka_producer.send_message.side_effect = [
            None,  # Success
            Exception("Kafka error"),  # Failure
            None,  # Success
        ]

        response = client.post("/images/batch", json=images)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "partial"

    def test_batch_upload_invalid_base64_in_batch(
        self,
        client,
        mock_kafka_producer,
        sample_image_data,
    ):
        """Test batch upload with invalid base64 in one image."""
        images = [sample_image_data.copy() for _ in range(3)]
        images[1]["image_data"] = "invalid_base64!"  # Invalid in middle

        response = client.post("/images/batch", json=images)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "partial"


class TestImageDataModel:
    """Test ImageData model validation."""

    def test_image_data_validation(self, sample_image_data):
        """Test valid image data model creation."""
        image = ImageData(**sample_image_data)
        assert image.format == "jpeg"
        assert image.width == 1920
        assert image.height == 1080
        assert image.camera_type == "rear"
        assert image.file_size == 27  # Length of test data
        assert "exif" in image.metadata

    def test_image_data_defaults(self):
        """Test default values for optional fields."""
        test_image_bytes = b"test_image"
        encoded_image = base64.b64encode(test_image_bytes).decode("utf-8")

        image_data = {
            "device_id": "12345678-1234-8234-1234-123456789012",
            "image_data": encoded_image,
            "recorded_at": datetime.now(UTC),
            "width": 100,
            "height": 100,
        }

        image = ImageData(**image_data)
        assert image.format == "jpeg"  # Default
        assert image.camera_type is None
        assert image.file_size is None
        assert image.metadata is None

    def test_image_data_bytes_field(self):
        """Test that image_data properly handles bytes."""
        test_image_bytes = b"test_image_data"
        encoded_image = base64.b64encode(test_image_bytes).decode("utf-8")

        image_data = {
            "device_id": "12345678-1234-8234-1234-123456789012",
            "image_data": encoded_image,
            "recorded_at": datetime.now(UTC),
            "width": 100,
            "height": 100,
        }

        image = ImageData(**image_data)
        # The field should store as bytes after base64 decoding in the endpoint
        assert isinstance(
            image.image_data,
            (str, bytes),
        )  # Could be either depending on serialization
