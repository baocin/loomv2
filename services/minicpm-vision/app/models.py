"""Data models for MiniCPM-Vision service."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class BaseMessage(BaseModel):
    """Base message model with common fields."""

    device_id: str = Field(..., description="Device ID that generated the data")
    recorded_at: datetime = Field(..., description="Timestamp when data was recorded")
    schema_version: str = Field(default="v1", description="Schema version")


class ImageMessage(BaseMessage):
    """Input message for image data from Kafka."""

    data: str = Field(..., description="Base64 encoded image data")
    format: Optional[str] = Field(None, description="Image format (jpg, png, etc)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class DetectedObject(BaseModel):
    """Detected object in an image."""

    label: str = Field(..., description="Object class label")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")
    bbox: Optional[List[float]] = Field(
        None, description="Bounding box [x1, y1, x2, y2]"
    )


class OCRResult(BaseModel):
    """OCR text extraction result."""

    text: str = Field(..., description="Extracted text")
    confidence: float = Field(..., ge=0.0, le=1.0, description="OCR confidence")
    bbox: Optional[List[float]] = Field(
        None, description="Text bounding box [x1, y1, x2, y2]"
    )


class VisionAnalysisResult(BaseMessage):
    """Vision analysis output to be sent to Kafka."""

    # Scene understanding
    scene_description: str = Field(..., description="Natural language scene description")
    scene_categories: List[str] = Field(
        default_factory=list, description="Scene categories/tags"
    )

    # Object detection
    detected_objects: List[DetectedObject] = Field(
        default_factory=list, description="List of detected objects"
    )

    # OCR results
    ocr_results: List[OCRResult] = Field(
        default_factory=list, description="OCR text extraction results"
    )
    full_text: Optional[str] = Field(
        None, description="Full concatenated OCR text"
    )

    # Visual attributes
    dominant_colors: Optional[List[str]] = Field(
        None, description="Dominant colors in the image"
    )
    image_quality: Optional[Dict[str, float]] = Field(
        None, description="Image quality metrics (brightness, contrast, etc)"
    )

    # Processing metadata
    processing_time_ms: float = Field(
        ..., description="Time taken to process the image in milliseconds"
    )
    model_version: str = Field(
        default="MiniCPM-Llama3-V-2.5", description="Model version used"
    )
    
    # Additional insights
    visual_questions_answered: Optional[Dict[str, str]] = Field(
        None, description="Answers to specific visual questions if any"
    )


class HealthStatus(BaseModel):
    """Health check response model."""

    status: str = Field(..., description="Health status")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Check timestamp"
    )
    checks: Optional[Dict[str, bool]] = Field(
        None, description="Individual component checks"
    )