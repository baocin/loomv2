"""Tests for data models."""

import json
from datetime import datetime

import pytest
from pydantic import ValidationError

from app.models import (
    BaseMessage,
    ImageMessage,
    ImageAnalysisRequest,
    DetectedObject,
    OCRBlock,
    ImageFeatures,
    MoondreamAnalysisResult,
    HealthStatus,
    ProcessingMetrics,
    MoondreamResponse,
)


def test_base_message():
    """Test BaseMessage model."""
    now = datetime.utcnow()
    message = BaseMessage(
        device_id="test-device",
        recorded_at=now,
        schema_version="v2"
    )
    
    assert message.device_id == "test-device"
    assert message.recorded_at == now
    assert message.schema_version == "v2"


def test_base_message_defaults():
    """Test BaseMessage default values."""
    message = BaseMessage(
        device_id="test-device",
        recorded_at=datetime.utcnow()
    )
    
    assert message.schema_version == "v1"


def test_image_message():
    """Test ImageMessage model."""
    now = datetime.utcnow()
    message = ImageMessage(
        device_id="test-device",
        recorded_at=now,
        data="base64encodeddata",
        format="jpeg",
        metadata={"camera": "front", "resolution": "1920x1080"}
    )
    
    assert message.data == "base64encodeddata"
    assert message.format == "jpeg"
    assert message.metadata == {"camera": "front", "resolution": "1920x1080"}


def test_image_analysis_request():
    """Test ImageAnalysisRequest model."""
    request = ImageAnalysisRequest(
        image_data="base64encodedimage",
        query="What's in this image?",
        enable_object_detection=True,
        enable_ocr=False,
        max_objects=15
    )
    
    assert request.image_data == "base64encodedimage"
    assert request.query == "What's in this image?"
    assert request.enable_object_detection is True
    assert request.enable_ocr is False
    assert request.max_objects == 15


def test_image_analysis_request_defaults():
    """Test ImageAnalysisRequest default values."""
    request = ImageAnalysisRequest(image_data="base64image")
    
    assert request.query is None
    assert request.enable_object_detection is None
    assert request.enable_ocr is None
    assert request.max_objects == 10


def test_detected_object():
    """Test DetectedObject model."""
    obj = DetectedObject(
        label="person",
        confidence=0.95,
        bbox=[100.0, 200.0, 300.0, 400.0],
        attributes={"age": "adult", "gender": "unknown"}
    )
    
    assert obj.label == "person"
    assert obj.confidence == 0.95
    assert obj.bbox == [100.0, 200.0, 300.0, 400.0]
    assert obj.attributes == {"age": "adult", "gender": "unknown"}


def test_detected_object_confidence_validation():
    """Test DetectedObject confidence validation."""
    # Valid confidence
    obj = DetectedObject(label="test", confidence=0.0, bbox=[0, 0, 10, 10])
    assert obj.confidence == 0.0
    
    obj = DetectedObject(label="test", confidence=1.0, bbox=[0, 0, 10, 10])
    assert obj.confidence == 1.0
    
    # Invalid confidence
    with pytest.raises(ValidationError):
        DetectedObject(label="test", confidence=-0.1, bbox=[0, 0, 10, 10])
    
    with pytest.raises(ValidationError):
        DetectedObject(label="test", confidence=1.1, bbox=[0, 0, 10, 10])


def test_ocr_block():
    """Test OCRBlock model."""
    block = OCRBlock(
        text="Hello World",
        confidence=0.98,
        bbox=[50.0, 50.0, 200.0, 100.0],
        language="en"
    )
    
    assert block.text == "Hello World"
    assert block.confidence == 0.98
    assert block.bbox == [50.0, 50.0, 200.0, 100.0]
    assert block.language == "en"


def test_image_features():
    """Test ImageFeatures model."""
    features = ImageFeatures(
        dominant_colors=["#FF0000", "#00FF00", "#0000FF"],
        brightness=0.75,
        contrast=0.65,
        sharpness=0.85,
        aspect_ratio=1.78
    )
    
    assert features.dominant_colors == ["#FF0000", "#00FF00", "#0000FF"]
    assert features.brightness == 0.75
    assert features.contrast == 0.65
    assert features.sharpness == 0.85
    assert features.aspect_ratio == 1.78


def test_moondream_analysis_result():
    """Test MoondreamAnalysisResult model."""
    now = datetime.utcnow()
    detected_obj = DetectedObject(label="cat", confidence=0.9, bbox=[0, 0, 100, 100])
    ocr_block = OCRBlock(text="Test", confidence=0.95, bbox=[10, 10, 50, 30])
    
    result = MoondreamAnalysisResult(
        device_id="test-device",
        recorded_at=now,
        caption="A cat sitting on a table",
        query_response="Yes, there is a cat",
        detected_objects=[detected_obj],
        object_count={"cat": 1},
        ocr_blocks=[ocr_block],
        full_text="Test",
        scene_type="indoor",
        scene_attributes=["animals", "furniture"],
        image_quality_score=0.9,
        processing_time_ms=2500.0
    )
    
    assert result.caption == "A cat sitting on a table"
    assert result.query_response == "Yes, there is a cat"
    assert len(result.detected_objects) == 1
    assert result.object_count == {"cat": 1}
    assert len(result.ocr_blocks) == 1
    assert result.full_text == "Test"
    assert result.scene_type == "indoor"
    assert result.scene_attributes == ["animals", "furniture"]
    assert result.image_quality_score == 0.9
    assert result.processing_time_ms == 2500.0
    assert result.model_version == "moondream-latest"


def test_moondream_analysis_result_with_error():
    """Test MoondreamAnalysisResult with error."""
    result = MoondreamAnalysisResult(
        device_id="test-device",
        recorded_at=datetime.utcnow(),
        caption="",
        detected_objects=[],
        object_count={},
        ocr_blocks=[],
        processing_time_ms=0,
        error="Processing failed: timeout",
        warnings=["Low quality image", "Partial results"]
    )
    
    assert result.error == "Processing failed: timeout"
    assert result.warnings == ["Low quality image", "Partial results"]


def test_health_status():
    """Test HealthStatus model."""
    checks = {"moondream": True, "kafka": False}
    status = HealthStatus(
        status="unhealthy",
        checks=checks
    )
    
    assert status.status == "unhealthy"
    assert status.checks == checks
    assert isinstance(status.timestamp, datetime)


def test_processing_metrics():
    """Test ProcessingMetrics model."""
    now = datetime.utcnow()
    metrics = ProcessingMetrics(
        images_processed=150,
        total_processing_time=75000.0,
        average_processing_time=500.0,
        errors_count=3,
        last_processed=now,
        caption_count=140,
        query_count=50,
        objects_detected_total=320,
        ocr_blocks_total=85
    )
    
    assert metrics.images_processed == 150
    assert metrics.total_processing_time == 75000.0
    assert metrics.average_processing_time == 500.0
    assert metrics.errors_count == 3
    assert metrics.last_processed == now
    assert metrics.caption_count == 140
    assert metrics.query_count == 50
    assert metrics.objects_detected_total == 320
    assert metrics.ocr_blocks_total == 85


def test_processing_metrics_defaults():
    """Test ProcessingMetrics default values."""
    metrics = ProcessingMetrics()
    
    assert metrics.images_processed == 0
    assert metrics.total_processing_time == 0.0
    assert metrics.average_processing_time == 0.0
    assert metrics.errors_count == 0
    assert metrics.last_processed is None
    assert metrics.caption_count == 0
    assert metrics.query_count == 0
    assert metrics.objects_detected_total == 0
    assert metrics.ocr_blocks_total == 0


def test_moondream_response():
    """Test MoondreamResponse model."""
    response = MoondreamResponse(
        caption="A beautiful landscape",
        query_response="The image shows mountains and a lake",
        objects=[
            {"label": "mountain", "confidence": 0.9},
            {"label": "lake", "confidence": 0.85}
        ],
        text_blocks=[
            {"text": "Welcome", "confidence": 0.95}
        ],
        metadata={"processing_time": 1200, "model": "moondream-v1"}
    )
    
    assert response.caption == "A beautiful landscape"
    assert response.query_response == "The image shows mountains and a lake"
    assert len(response.objects) == 2
    assert response.objects[0]["label"] == "mountain"
    assert len(response.text_blocks) == 1
    assert response.metadata["processing_time"] == 1200


def test_model_serialization():
    """Test model JSON serialization."""
    now = datetime.utcnow()
    message = ImageMessage(
        device_id="test-device",
        recorded_at=now,
        data="base64data"
    )
    
    # Test model_dump
    data = message.model_dump(mode="json")
    assert isinstance(data, dict)
    assert data["device_id"] == "test-device"
    assert data["data"] == "base64data"
    
    # Test JSON serialization
    json_str = message.model_dump_json()
    assert isinstance(json_str, str)
    
    # Test deserialization
    loaded_data = json.loads(json_str)
    recreated = ImageMessage(**loaded_data)
    assert recreated.device_id == message.device_id
    assert recreated.data == message.data