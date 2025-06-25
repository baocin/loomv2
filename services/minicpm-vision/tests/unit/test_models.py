"""Unit tests for data models."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.models import (
    BaseMessage,
    DetectedObject,
    HealthStatus,
    ImageMessage,
    OCRResult,
    VisionAnalysisResult,
)


class TestBaseMessage:
    """Test BaseMessage model."""

    def test_valid_base_message(self):
        """Test creating a valid base message."""
        msg = BaseMessage(
            device_id="device123",
            recorded_at=datetime.utcnow(),
            schema_version="v1",
        )
        assert msg.device_id == "device123"
        assert msg.schema_version == "v1"
        assert isinstance(msg.recorded_at, datetime)

    def test_missing_required_fields(self):
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError):
            BaseMessage(device_id="device123")  # Missing recorded_at


class TestImageMessage:
    """Test ImageMessage model."""

    def test_valid_image_message(self):
        """Test creating a valid image message."""
        msg = ImageMessage(
            device_id="device123",
            recorded_at=datetime.utcnow(),
            data="base64encodeddata",
            format="jpg",
            metadata={"width": 1920, "height": 1080},
        )
        assert msg.data == "base64encodeddata"
        assert msg.format == "jpg"
        assert msg.metadata["width"] == 1920

    def test_minimal_image_message(self):
        """Test creating image message with only required fields."""
        msg = ImageMessage(
            device_id="device123",
            recorded_at=datetime.utcnow(),
            data="base64encodeddata",
        )
        assert msg.format is None
        assert msg.metadata is None


class TestDetectedObject:
    """Test DetectedObject model."""

    def test_valid_detected_object(self):
        """Test creating a valid detected object."""
        obj = DetectedObject(
            label="person",
            confidence=0.95,
            bbox=[100, 200, 300, 400],
        )
        assert obj.label == "person"
        assert obj.confidence == 0.95
        assert obj.bbox == [100, 200, 300, 400]

    def test_confidence_validation(self):
        """Test confidence value validation."""
        with pytest.raises(ValidationError):
            DetectedObject(label="person", confidence=1.5)  # > 1.0

        with pytest.raises(ValidationError):
            DetectedObject(label="person", confidence=-0.1)  # < 0.0


class TestOCRResult:
    """Test OCRResult model."""

    def test_valid_ocr_result(self):
        """Test creating a valid OCR result."""
        ocr = OCRResult(
            text="Hello World",
            confidence=0.89,
            bbox=[50, 50, 200, 100],
        )
        assert ocr.text == "Hello World"
        assert ocr.confidence == 0.89


class TestVisionAnalysisResult:
    """Test VisionAnalysisResult model."""

    def test_valid_vision_analysis(self):
        """Test creating a valid vision analysis result."""
        result = VisionAnalysisResult(
            device_id="device123",
            recorded_at=datetime.utcnow(),
            scene_description="A person standing in a park",
            scene_categories=["outdoor", "nature", "people"],
            detected_objects=[
                DetectedObject(label="person", confidence=0.95),
                DetectedObject(label="tree", confidence=0.87),
            ],
            ocr_results=[
                OCRResult(text="Park Sign", confidence=0.92),
            ],
            full_text="Park Sign",
            processing_time_ms=1234.5,
        )
        assert result.scene_description == "A person standing in a park"
        assert len(result.detected_objects) == 2
        assert len(result.ocr_results) == 1
        assert result.processing_time_ms == 1234.5

    def test_minimal_vision_analysis(self):
        """Test creating vision analysis with minimal fields."""
        result = VisionAnalysisResult(
            device_id="device123",
            recorded_at=datetime.utcnow(),
            scene_description="Empty scene",
            processing_time_ms=100.0,
        )
        assert result.scene_categories == []
        assert result.detected_objects == []
        assert result.ocr_results == []
        assert result.full_text is None


class TestHealthStatus:
    """Test HealthStatus model."""

    def test_health_status(self):
        """Test creating health status."""
        status = HealthStatus(
            status="healthy",
            checks={"database": True, "kafka": True},
        )
        assert status.status == "healthy"
        assert status.checks["database"] is True
        assert isinstance(status.timestamp, datetime)
