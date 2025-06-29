"""Tests for data models."""

import json
from datetime import datetime

import pytest
from pydantic import ValidationError

from app.models import (
    AnalysisResult,
    AudioMessage,
    BaseMessage,
    HealthStatus,
    ImageMessage,
    MultimodalAnalysisResult,
    MultimodalRequest,
    OllamaResponse,
    ProcessingMetrics,
    TextMessage,
)


def test_base_message():
    """Test BaseMessage model."""
    now = datetime.utcnow()
    message = BaseMessage(device_id="test-device", recorded_at=now, schema_version="v2")

    assert message.device_id == "test-device"
    assert message.recorded_at == now
    assert message.schema_version == "v2"


def test_base_message_defaults():
    """Test BaseMessage default values."""
    message = BaseMessage(device_id="test-device", recorded_at=datetime.utcnow())

    assert message.schema_version == "v1"


def test_text_message():
    """Test TextMessage model."""
    now = datetime.utcnow()
    message = TextMessage(
        device_id="test-device",
        recorded_at=now,
        text="Hello world",
        context="Test context",
        metadata={"source": "test"},
    )

    assert message.text == "Hello world"
    assert message.context == "Test context"
    assert message.metadata == {"source": "test"}


def test_text_message_required_fields():
    """Test TextMessage required fields."""
    with pytest.raises(ValidationError) as exc_info:
        TextMessage(device_id="test", recorded_at=datetime.utcnow())

    assert "text" in str(exc_info.value)


def test_image_message():
    """Test ImageMessage model."""
    now = datetime.utcnow()
    message = ImageMessage(
        device_id="test-device",
        recorded_at=now,
        data="base64encodeddata",
        format="png",
        metadata={"width": 100, "height": 100},
    )

    assert message.data == "base64encodeddata"
    assert message.format == "png"
    assert message.metadata == {"width": 100, "height": 100}


def test_audio_message():
    """Test AudioMessage model."""
    now = datetime.utcnow()
    message = AudioMessage(
        device_id="test-device",
        recorded_at=now,
        data="base64encodedaudio",
        format="wav",
        duration=5.5,
        metadata={"sample_rate": 44100},
    )

    assert message.data == "base64encodedaudio"
    assert message.format == "wav"
    assert message.duration == 5.5
    assert message.metadata == {"sample_rate": 44100}


def test_multimodal_request():
    """Test MultimodalRequest model."""
    request = MultimodalRequest(
        prompt="Analyze this content",
        text="Sample text",
        image_data="base64image",
        audio_data="base64audio",
        max_tokens=2000,
        temperature=0.8,
    )

    assert request.prompt == "Analyze this content"
    assert request.text == "Sample text"
    assert request.image_data == "base64image"
    assert request.audio_data == "base64audio"
    assert request.max_tokens == 2000
    assert request.temperature == 0.8


def test_multimodal_request_required_fields():
    """Test MultimodalRequest required fields."""
    # Only prompt is required
    request = MultimodalRequest(prompt="Test prompt")
    assert request.prompt == "Test prompt"
    assert request.text is None
    assert request.image_data is None
    assert request.audio_data is None


def test_analysis_result():
    """Test AnalysisResult model."""
    result = AnalysisResult(
        type="text",
        content="Analysis result content",
        confidence=0.95,
        metadata={"tokens": 150},
    )

    assert result.type == "text"
    assert result.content == "Analysis result content"
    assert result.confidence == 0.95
    assert result.metadata == {"tokens": 150}


def test_analysis_result_confidence_validation():
    """Test AnalysisResult confidence validation."""
    # Valid confidence values
    result = AnalysisResult(type="test", content="content", confidence=0.0)
    assert result.confidence == 0.0

    result = AnalysisResult(type="test", content="content", confidence=1.0)
    assert result.confidence == 1.0

    # Invalid confidence values should raise ValidationError
    with pytest.raises(ValidationError):
        AnalysisResult(type="test", content="content", confidence=-0.1)

    with pytest.raises(ValidationError):
        AnalysisResult(type="test", content="content", confidence=1.1)


def test_multimodal_analysis_result():
    """Test MultimodalAnalysisResult model."""
    now = datetime.utcnow()
    text_analysis = AnalysisResult(type="text", content="Text analysis")

    result = MultimodalAnalysisResult(
        device_id="test-device",
        recorded_at=now,
        analysis_type="multimodal_analysis",
        primary_result="Primary analysis result",
        text_analysis=text_analysis,
        processing_time_ms=1500.0,
        model_version="gemma3n:e4b",
    )

    assert result.analysis_type == "multimodal_analysis"
    assert result.primary_result == "Primary analysis result"
    assert result.text_analysis == text_analysis
    assert result.processing_time_ms == 1500.0
    assert result.model_version == "gemma3n:e4b"


def test_ollama_response():
    """Test OllamaResponse model."""
    now = datetime.utcnow()
    response = OllamaResponse(
        model="gemma3n:e4b",
        created_at=now,
        response="Generated response",
        done=True,
        total_duration=5000,
        eval_count=100,
    )

    assert response.model == "gemma3n:e4b"
    assert response.created_at == now
    assert response.response == "Generated response"
    assert response.done is True
    assert response.total_duration == 5000
    assert response.eval_count == 100


def test_health_status():
    """Test HealthStatus model."""
    checks = {"ollama": True, "kafka": False}
    status = HealthStatus(status="unhealthy", checks=checks)

    assert status.status == "unhealthy"
    assert status.checks == checks
    assert isinstance(status.timestamp, datetime)


def test_processing_metrics():
    """Test ProcessingMetrics model."""
    metrics = ProcessingMetrics(
        requests_processed=100,
        total_processing_time=50000.0,
        average_processing_time=500.0,
        errors_count=5,
    )

    assert metrics.requests_processed == 100
    assert metrics.total_processing_time == 50000.0
    assert metrics.average_processing_time == 500.0
    assert metrics.errors_count == 5
    assert metrics.last_processed is None


def test_processing_metrics_defaults():
    """Test ProcessingMetrics default values."""
    metrics = ProcessingMetrics()

    assert metrics.requests_processed == 0
    assert metrics.total_processing_time == 0.0
    assert metrics.average_processing_time == 0.0
    assert metrics.errors_count == 0
    assert metrics.last_processed is None


def test_model_serialization():
    """Test model JSON serialization."""
    now = datetime.utcnow()
    message = TextMessage(device_id="test-device", recorded_at=now, text="Test message")

    # Test model_dump
    data = message.model_dump(mode="json")
    assert isinstance(data, dict)
    assert data["device_id"] == "test-device"
    assert data["text"] == "Test message"

    # Test JSON serialization
    json_str = message.model_dump_json()
    assert isinstance(json_str, str)

    # Test deserialization
    loaded_data = json.loads(json_str)
    recreated = TextMessage(**loaded_data)
    assert recreated.device_id == message.device_id
    assert recreated.text == message.text
