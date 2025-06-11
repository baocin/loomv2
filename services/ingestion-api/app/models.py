"""Pydantic models for ingestion API data structures."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class BaseMessage(BaseModel):
    """Base message structure for all Kafka messages."""
    
    schema_version: str = Field(default="1.0", description="Message schema version")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")
    device_id: str = Field(description="Device identifier")
    message_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique message ID")


class AudioChunk(BaseMessage):
    """Audio chunk data from microphone."""
    
    chunk_data: bytes = Field(description="Raw audio chunk data")
    sample_rate: int = Field(description="Audio sample rate in Hz")
    channels: int = Field(default=1, description="Number of audio channels")
    format: str = Field(default="wav", description="Audio format")
    duration_ms: int = Field(description="Chunk duration in milliseconds")
    file_id: Optional[str] = Field(default=None, description="Associated file ID for chunking")


class SensorReading(BaseMessage):
    """Generic sensor reading."""
    
    sensor_type: str = Field(description="Type of sensor (gps, accelerometer, etc.)")
    value: Dict[str, Any] = Field(description="Sensor reading values")
    unit: Optional[str] = Field(default=None, description="Unit of measurement")
    accuracy: Optional[float] = Field(default=None, description="Reading accuracy")


class GPSReading(BaseMessage):
    """GPS coordinate reading."""
    
    latitude: float = Field(description="Latitude in decimal degrees")
    longitude: float = Field(description="Longitude in decimal degrees")
    altitude: Optional[float] = Field(default=None, description="Altitude in meters")
    accuracy: Optional[float] = Field(default=None, description="GPS accuracy in meters")
    heading: Optional[float] = Field(default=None, description="Heading in degrees")
    speed: Optional[float] = Field(default=None, description="Speed in m/s")


class AccelerometerReading(BaseMessage):
    """Accelerometer sensor reading."""
    
    x: float = Field(description="X-axis acceleration in m/s²")
    y: float = Field(description="Y-axis acceleration in m/s²") 
    z: float = Field(description="Z-axis acceleration in m/s²")


class HeartRateReading(BaseMessage):
    """Heart rate sensor reading."""
    
    bpm: int = Field(description="Beats per minute")
    confidence: Optional[float] = Field(default=None, description="Reading confidence 0-1")


class PowerState(BaseMessage):
    """Device power state information."""
    
    battery_level: float = Field(description="Battery level percentage 0-100")
    is_charging: bool = Field(description="Whether device is charging")
    power_source: Optional[str] = Field(default=None, description="Power source type")


class ImageData(BaseMessage):
    """Image data from camera or screenshot."""
    
    image_data: bytes = Field(description="Raw image data")
    format: str = Field(default="jpeg", description="Image format")
    width: int = Field(description="Image width in pixels")
    height: int = Field(description="Image height in pixels")
    camera_type: Optional[str] = Field(default=None, description="Camera type (front/rear/screen)")


class WebSocketMessage(BaseModel):
    """WebSocket message wrapper."""
    
    message_type: str = Field(description="Type of message (audio, sensor, etc.)")
    data: Dict[str, Any] = Field(description="Message payload")


class HealthCheck(BaseModel):
    """Health check response."""
    
    status: str = Field(default="healthy", description="Service status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")
    version: str = Field(default="0.1.0", description="Service version")
    kafka_connected: bool = Field(description="Kafka connection status") 