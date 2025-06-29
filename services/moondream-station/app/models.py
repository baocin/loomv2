"""Data models for Moondream Station service."""

from datetime import datetime
from typing import Any, Dict, List, Optional

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


class ImageAnalysisRequest(BaseModel):
    """Request model for image analysis."""

    image_data: str = Field(..., description="Base64 encoded image data")
    query: Optional[str] = Field(None, description="Optional query about the image")
    enable_object_detection: Optional[bool] = Field(
        None, description="Enable object detection"
    )
    enable_ocr: Optional[bool] = Field(None, description="Enable OCR text extraction")
    max_objects: Optional[int] = Field(10, description="Maximum objects to detect")


class DetectedObject(BaseModel):
    """Detected object in an image."""

    label: str = Field(..., description="Object class label")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")
    bbox: List[float] = Field(..., description="Bounding box [x1, y1, x2, y2]")
    attributes: Optional[Dict[str, Any]] = Field(
        None, description="Additional attributes"
    )


class OCRBlock(BaseModel):
    """OCR text block."""

    text: str = Field(..., description="Extracted text")
    confidence: float = Field(..., ge=0.0, le=1.0, description="OCR confidence")
    bbox: List[float] = Field(..., description="Text bounding box [x1, y1, x2, y2]")
    language: Optional[str] = Field(None, description="Detected language")


class ImageFeatures(BaseModel):
    """Visual features extracted from image."""

    dominant_colors: List[str] = Field(..., description="Dominant colors in hex format")
    brightness: float = Field(..., ge=0.0, le=1.0, description="Image brightness")
    contrast: float = Field(..., ge=0.0, le=1.0, description="Image contrast")
    sharpness: float = Field(..., ge=0.0, le=1.0, description="Image sharpness")
    aspect_ratio: float = Field(..., description="Width/height ratio")


class MoondreamAnalysisResult(BaseMessage):
    """Moondream analysis output to be sent to Kafka."""

    model_config = {"protected_namespaces": ()}

    # Core analysis
    caption: str = Field(..., description="Natural language image description")
    query_response: Optional[str] = Field(
        None, description="Response to specific query"
    )

    # Object detection
    detected_objects: List[DetectedObject] = Field(
        default_factory=list, description="List of detected objects"
    )
    object_count: Dict[str, int] = Field(
        default_factory=dict, description="Count of each object type"
    )

    # OCR results
    ocr_blocks: List[OCRBlock] = Field(
        default_factory=list, description="OCR text extraction results"
    )
    full_text: Optional[str] = Field(None, description="Full concatenated OCR text")

    # Visual features
    visual_features: Optional[ImageFeatures] = Field(
        None, description="Extracted visual features"
    )

    # Scene understanding
    scene_type: Optional[str] = Field(None, description="Detected scene type")
    scene_attributes: Optional[List[str]] = Field(
        None, description="Scene attributes/tags"
    )

    # Quality assessment
    image_quality_score: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Overall image quality score"
    )

    # Processing metadata
    processing_time_ms: float = Field(
        ..., description="Time taken to process in milliseconds"
    )
    model_version: str = Field(
        default="moondream-latest", description="Model version used"
    )

    # Error handling
    error: Optional[str] = Field(None, description="Error message if processing failed")
    warnings: Optional[List[str]] = Field(None, description="Warning messages")


class HealthStatus(BaseModel):
    """Health check response model."""

    status: str = Field(..., description="Health status")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Check timestamp"
    )
    checks: Optional[Dict[str, bool]] = Field(
        None, description="Individual component checks"
    )


class ProcessingMetrics(BaseModel):
    """Metrics for monitoring processing performance."""

    images_processed: int = Field(default=0, description="Total images processed")
    total_processing_time: float = Field(
        default=0.0, description="Total processing time"
    )
    average_processing_time: float = Field(
        default=0.0, description="Average processing time"
    )
    errors_count: int = Field(default=0, description="Number of errors encountered")
    last_processed: Optional[datetime] = Field(
        None, description="Last processing timestamp"
    )

    # Detailed metrics
    caption_count: int = Field(default=0, description="Number of captions generated")
    query_count: int = Field(default=0, description="Number of queries processed")
    objects_detected_total: int = Field(default=0, description="Total objects detected")
    ocr_blocks_total: int = Field(default=0, description="Total OCR blocks extracted")


class MoondreamResponse(BaseModel):
    """Response from Moondream Station API."""

    caption: Optional[str] = Field(None, description="Generated caption")
    query_response: Optional[str] = Field(None, description="Response to query")
    objects: Optional[List[Dict[str, Any]]] = Field(
        None, description="Detected objects"
    )
    text_blocks: Optional[List[Dict[str, Any]]] = Field(None, description="OCR results")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
