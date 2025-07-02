"""Data models for step counting."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class AccelerometerReading(BaseModel):
    """Accelerometer reading from Kafka."""
    schema_version: str
    timestamp: datetime
    device_id: str
    x: float
    y: float
    z: float
    accuracy: Optional[int] = None


class StepCountEvent(BaseModel):
    """Step count event to be published."""
    schema_version: str = Field(default="1.0.0")
    timestamp: datetime
    device_id: str
    message_id: str = Field(description="Unique message identifier")
    
    # Core step data
    step_count: int = Field(description="Number of steps detected in this period")
    distance_meters: float = Field(description="Estimated distance traveled")
    calories_burned: float = Field(description="Estimated calories burned")
    active_minutes: int = Field(description="Minutes with significant activity")
    
    # Additional metadata
    start_time: datetime = Field(description="Start of counting period")
    end_time: datetime = Field(description="End of counting period")
    duration_seconds: float = Field(description="Duration of counting period")
    
    # Activity classification
    activity_type: str = Field(default="walking", description="Type of activity")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in step detection")
    
    # Raw data summary
    avg_acceleration: float = Field(description="Average acceleration magnitude")
    peak_frequency_hz: float = Field(description="Dominant frequency in signal")