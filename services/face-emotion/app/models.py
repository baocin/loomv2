"""Data models for face emotion detection service."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class VisionAnnotation(BaseModel):
    """Vision annotation from MiniCPM processing."""

    device_id: str
    timestamp: datetime
    schema_version: str = "v1"
    message_id: str
    annotation_id: str
    object_class: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    bounding_box: Optional[Dict[str, float]] = None  # {x, y, width, height}
    object_attributes: Optional[Dict[str, Any]] = None
    ocr_text: Optional[str] = None
    scene_description: Optional[str] = None
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    model_version: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FaceBoundingBox(BaseModel):
    """Face bounding box coordinates."""

    x: float
    y: float
    width: float
    height: float
    confidence: Optional[float] = None


class FacialLandmarks(BaseModel):
    """Facial landmarks for detailed analysis."""

    left_eye: Optional[Dict[str, float]] = None
    right_eye: Optional[Dict[str, float]] = None
    nose: Optional[Dict[str, float]] = None
    mouth: Optional[Dict[str, float]] = None
    face_contour: Optional[List[Dict[str, float]]] = None


class FaceEmotionAnalysis(BaseModel):
    """Face emotion analysis result."""

    device_id: str
    timestamp: datetime
    schema_version: str = "v1"
    message_id: str
    face_id: str

    # Primary emotion prediction
    emotion_label: str
    confidence_score: float = Field(ge=0.0, le=1.0)

    # Face detection information
    face_bounding_box: FaceBoundingBox
    facial_landmarks: Optional[FacialLandmarks] = None

    # Demographics (if available)
    age_estimate: Optional[int] = None
    gender_estimate: Optional[str] = None

    # All emotion scores
    emotion_intensities: Dict[str, float] = Field(default_factory=dict)

    # Face quality metrics
    face_quality_score: Optional[float] = None
    face_size_pixels: Optional[int] = None
    face_angle: Optional[Dict[str, float]] = None  # pitch, yaw, roll

    # Processing metadata
    processing_duration_ms: Optional[float] = None
    model_version: str

    # Source annotation information
    source_annotation_id: str
    source_object_class: str
    source_bounding_box: Optional[Dict[str, float]] = None

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
