"""Data models for activity classification."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class ActivityType(str, Enum):
    """Types of activities."""
    STATIONARY = "stationary"
    WALKING = "walking"
    RUNNING = "running"
    CYCLING = "cycling"
    VEHICLE = "vehicle"
    PUBLIC_TRANSPORT = "public_transport"
    UNKNOWN = "unknown"


class LocationContext(str, Enum):
    """Location context types."""
    HOME = "home"
    WORK = "work"
    OUTDOORS = "outdoors"
    INDOORS = "indoors"
    TRANSIT = "transit"
    UNKNOWN = "unknown"


class ActivityClassification(BaseModel):
    """Activity classification event."""
    schema_version: str = Field(default="1.0.0")
    timestamp: datetime
    device_id: str
    message_id: str = Field(description="Unique message identifier")
    
    # Classification results
    activity_type: ActivityType
    confidence: float = Field(ge=0.0, le=1.0)
    location_context: Optional[LocationContext] = None
    
    # Time window
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    
    # Supporting data
    motion_events_count: int = Field(default=0)
    step_count: int = Field(default=0)
    distance_meters: float = Field(default=0.0)
    avg_speed_ms: float = Field(default=0.0)
    max_speed_ms: float = Field(default=0.0)
    
    # Location data
    start_location: Optional[Dict[str, float]] = None  # lat, lon
    end_location: Optional[Dict[str, float]] = None  # lat, lon
    
    # Detailed metrics
    metrics: Dict[str, Any] = Field(default_factory=dict)
    
    # Source data references
    source_events: List[str] = Field(default_factory=list, description="Trace IDs of source events")