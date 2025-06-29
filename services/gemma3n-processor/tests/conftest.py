"""Test configuration and fixtures for Gemma 3N Processor."""

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
    AudioMessage,
    ImageMessage,
    MultimodalAnalysisResult,
    MultimodalRequest,
    TextMessage,
)
from app.ollama_client import OllamaClient


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
        ollama_host="http://localhost:11434",
        log_level="DEBUG",
    )


@pytest.fixture
def test_client() -> TestClient:
    """Create test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_ollama_client() -> AsyncMock:
    """Create mock Ollama client."""
    client = AsyncMock(spec=OllamaClient)
    client.health_check.return_value = True
    client.list_models.return_value = ["gemma3n:e4b"]
    client.pull_model.return_value = True
    client.generate_text.return_value = "Mock text analysis result"
    client.analyze_image.return_value = "Mock image analysis result"
    client.process_multimodal.return_value = "Mock multimodal analysis result"
    return client


@pytest.fixture
def sample_text_message() -> TextMessage:
    """Create sample text message."""
    return TextMessage(
        device_id="test-device-001",
        recorded_at=datetime.utcnow(),
        text="This is a test message for analysis.",
        context="Testing context",
        metadata={"source": "test"},
    )


@pytest.fixture
def sample_image_data() -> str:
    """Create sample base64 encoded image."""
    # Create a simple test image
    image = Image.new("RGB", (100, 100), color="red")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


@pytest.fixture
def sample_image_message(sample_image_data: str) -> ImageMessage:
    """Create sample image message."""
    return ImageMessage(
        device_id="test-device-001",
        recorded_at=datetime.utcnow(),
        data=sample_image_data,
        format="png",
        metadata={"source": "test"},
    )


@pytest.fixture
def sample_audio_data() -> str:
    """Create sample base64 encoded audio data."""
    # Create dummy audio data (not actual audio, just for testing)
    dummy_audio = b"dummy_audio_data_for_testing"
    return base64.b64encode(dummy_audio).decode()


@pytest.fixture
def sample_audio_message(sample_audio_data: str) -> AudioMessage:
    """Create sample audio message."""
    return AudioMessage(
        device_id="test-device-001",
        recorded_at=datetime.utcnow(),
        data=sample_audio_data,
        format="wav",
        duration=5.0,
        metadata={"source": "test"},
    )


@pytest.fixture
def sample_multimodal_request(
    sample_image_data: str, sample_audio_data: str
) -> MultimodalRequest:
    """Create sample multimodal request."""
    return MultimodalRequest(
        prompt="Analyze this multimodal content",
        text="Sample text content",
        image_data=sample_image_data,
        audio_data=sample_audio_data,
        max_tokens=1000,
        temperature=0.7,
    )


@pytest.fixture
def sample_analysis_result() -> MultimodalAnalysisResult:
    """Create sample analysis result."""
    return MultimodalAnalysisResult(
        device_id="test-device-001",
        recorded_at=datetime.utcnow(),
        analysis_type="multimodal_analysis",
        primary_result="Mock analysis result",
        processing_time_ms=1500.0,
        model_version="gemma3n:e4b",
    )


@pytest.fixture
def kafka_message_text(sample_text_message: TextMessage) -> bytes:
    """Create Kafka message bytes for text."""
    return json.dumps(sample_text_message.model_dump(mode="json")).encode()


@pytest.fixture
def kafka_message_image(sample_image_message: ImageMessage) -> bytes:
    """Create Kafka message bytes for image."""
    return json.dumps(sample_image_message.model_dump(mode="json")).encode()


@pytest.fixture
def kafka_message_audio(sample_audio_message: AudioMessage) -> bytes:
    """Create Kafka message bytes for audio."""
    return json.dumps(sample_audio_message.model_dump(mode="json")).encode()


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
