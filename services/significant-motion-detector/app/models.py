"""Data models for motion detection."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class AccelerometerReading(BaseModel):
    """Accelerometer reading from Kafka."""
    schema_version: str
    timestamp: datetime
    device_id: str
    x: float
    y: float
    z: float
    accuracy: Optional[int] = None


class MotionType(str, Enum):
    """Types of motion detected."""
    WALKING = "walking"
    RUNNING = "running"
    VEHICLE = "vehicle"
    SUDDEN_STOP = "sudden_stop"
    SUDDEN_START = "sudden_start"
    FALL = "fall"
    SHAKE = "shake"
    UNKNOWN = "unknown"


class ActivityType(str, Enum):
    """Types of activities detected."""
    STATIONARY = "stationary"
    WALKING = "walking"
    RUNNING = "running"
    CYCLING = "cycling"
    VEHICLE = "vehicle"
    UNKNOWN = "unknown"


class SignificantMotionEvent(BaseModel):
    """Significant motion event to be published."""
    schema_version: str = Field(default="1.0.0")
    event_id: str = Field(description="Unique event identifier")
    device_id: str
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    motion_type: MotionType
    confidence: float = Field(ge=0.0, le=1.0)
    
    # Motion statistics
    max_acceleration: float = Field(description="Maximum acceleration magnitude (m/s²)")
    avg_acceleration: float = Field(description="Average acceleration magnitude (m/s²)")
    dominant_axis: str = Field(description="Dominant axis of motion (x, y, z)")
    
    # Activity classification
    activity_type: Optional[ActivityType] = None
    activity_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    
    # Additional metadata
    sample_count: int = Field(description="Number of samples in this event")
    raw_data_summary: dict = Field(
        default_factory=dict,
        description="Summary statistics of raw accelerometer data"
    )