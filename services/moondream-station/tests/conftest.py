"""Test configuration and fixtures for Moondream Station."""

import asyncio
import base64
import json
from datetime import datetime
from io import BytesIO
from typing import Generator
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.config import Settings
from app.main import app
from app.models import (
    DetectedObject,
    ImageAnalysisRequest,
    ImageFeatures,
    ImageMessage,
    MoondreamAnalysisResult,
    MoondreamResponse,
    OCRBlock,
)
from app.moondream_client import MoondreamClient


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings."""
    return Settings(
        environment="test",
        kafka_bootstrap_servers="localhost:9092",
        moondream_host="http://localhost:2020",
        log_level="DEBUG",
    )


@pytest.fixture
def test_client() -> TestClient:
    """Create test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_moondream_client() -> AsyncMock:
    """Create mock Moondream client."""
    client = AsyncMock(spec=MoondreamClient)
    client.health_check.return_value = True
    client.caption_image.return_value = "A beautiful sunset over the ocean"
    client.query_image.return_value = "There are 3 people in the image"
    client.detect_objects.return_value = [
        DetectedObject(label="person", confidence=0.9, bbox=[100, 100, 200, 300]),
        DetectedObject(label="car", confidence=0.85, bbox=[300, 200, 500, 400]),
    ]
    client.extract_text.return_value = [
        OCRBlock(text="Hello World", confidence=0.95, bbox=[50, 50, 150, 80]),
    ]
    client.analyze_visual_features.return_value = ImageFeatures(
        dominant_colors=["#FF5733", "#3366CC"],
        brightness=0.7,
        contrast=0.6,
        sharpness=0.8,
        aspect_ratio=1.5,
    )
    client.full_analysis.return_value = MoondreamResponse(
        caption="Test caption",
        query_response="Test response",
        objects=[{"label": "test", "confidence": 0.9, "bbox": [0, 0, 100, 100]}],
        text_blocks=[{"text": "test", "confidence": 0.9, "bbox": [0, 0, 50, 50]}],
        metadata={"processing_time_ms": 100},
    )
    return client


@pytest.fixture
def sample_image_base64() -> str:
    """Create sample base64 encoded image."""
    image = Image.new("RGB", (200, 200), color="blue")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


@pytest.fixture
def sample_large_image_base64() -> str:
    """Create sample large base64 encoded image."""
    image = Image.new("RGB", (3000, 2000), color="green")
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=95)
    return base64.b64encode(buffer.getvalue()).decode()


@pytest.fixture
def sample_image_message(sample_image_base64: str) -> ImageMessage:
    """Create sample image message."""
    return ImageMessage(
        device_id="test-device-001",
        recorded_at=datetime.utcnow(),
        data=sample_image_base64,
        format="png",
        metadata={"source": "test", "location": "test-lab"},
    )


@pytest.fixture
def sample_analysis_request(sample_image_base64: str) -> ImageAnalysisRequest:
    """Create sample analysis request."""
    return ImageAnalysisRequest(
        image_data=sample_image_base64,
        query="What objects are in this image?",
        enable_object_detection=True,
        enable_ocr=True,
        max_objects=5,
    )


@pytest.fixture
def sample_analysis_result() -> MoondreamAnalysisResult:
    """Create sample analysis result."""
    return MoondreamAnalysisResult(
        device_id="test-device-001",
        recorded_at=datetime.utcnow(),
        caption="A test image with various objects",
        query_response="I can see 2 objects",
        detected_objects=[
            DetectedObject(label="person", confidence=0.9, bbox=[100, 100, 200, 300])
        ],
        object_count={"person": 1},
        ocr_blocks=[
            OCRBlock(text="Test Text", confidence=0.95, bbox=[50, 50, 150, 80])
        ],
        full_text="Test Text",
        visual_features=ImageFeatures(
            dominant_colors=["#FF0000"],
            brightness=0.7,
            contrast=0.6,
            sharpness=0.8,
            aspect_ratio=1.0,
        ),
        scene_type="indoor",
        scene_attributes=["people", "technology"],
        image_quality_score=0.85,
        processing_time_ms=1500.0,
        model_version="moondream-latest",
    )


@pytest.fixture
def kafka_message_image(sample_image_message: ImageMessage) -> bytes:
    """Create Kafka message bytes for image."""
    return json.dumps(sample_image_message.model_dump(mode="json")).encode()


@pytest.fixture
def mock_kafka_consumer() -> Mock:
    """Create mock Kafka consumer."""
    consumer = Mock()
    consumer.start = AsyncMock()
    consumer.stop = AsyncMock()
    consumer.commit = AsyncMock()
    return consumer


@pytest.fixture
def mock_kafka_producer() -> Mock:
    """Create mock Kafka producer."""
    producer = Mock()
    producer.start = AsyncMock()
    producer.stop = AsyncMock()
    producer.send_and_wait = AsyncMock()
    return producer


@pytest.fixture
def mock_httpx_response() -> Mock:
    """Create mock httpx response."""
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "caption": "Test caption",
        "response": "Test response",
        "status": "ok",
    }
    response.raise_for_status = Mock()
    return response


@pytest.fixture
def sample_image_file() -> UploadFile:
    """Create sample image upload file."""
    image = Image.new("RGB", (100, 100), color="red")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)

    upload_file = Mock(spec=UploadFile)
    upload_file.filename = "test_image.png"
    upload_file.read = AsyncMock(return_value=buffer.getvalue())
    upload_file.content_type = "image/png"

    return upload_file
