"""Data models for georegion detection"""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class GeocodedLocation(BaseModel):
    """Geocoded location from Kafka"""
    trace_id: str
    device_id: str
    timestamp: datetime
    schema_version: str = "v1"
    data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


class Georegion(BaseModel):
    """Georegion definition"""
    id: str
    name: str
    type: str  # home, work, custom
    latitude: float
    longitude: float
    radius_meters: float
    metadata: Optional[Dict[str, Any]] = None


class GeoregionDetection(BaseModel):
    """Georegion detection event"""
    trace_id: str = Field(description="Unique trace ID for the event")
    device_id: str = Field(description="Device that generated the location")
    timestamp: datetime = Field(description="When the detection occurred")
    schema_version: str = Field(default="v1", description="Schema version")
    
    data: Dict[str, Any] = Field(
        description="Detection data including georegion info and confidence"
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata"
    )