"""Data models for ONNX-VAD service matching silero-vad format."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class AudioChunk(BaseModel):
    """Raw audio chunk from Kafka."""

    device_id: str
    timestamp: str
    recorded_at: str
    audio_data: str  # Base64 encoded audio
    format: str
    sample_rate: int
    duration_seconds: float
    channels: int
    chunk_number: int
    file_id: str

    # Optional fields
    metadata: Optional[dict] = None


class VADResult(BaseModel):
    """Voice activity detection result."""

    device_id: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    audio_data: str  # Base64 encoded filtered audio
    format: str
    sample_rate: int
    duration_seconds: float
    channels: int
    chunk_number: int
    file_id: str

    # VAD specific fields
    speech_detected: bool
    speech_probability: float
    speech_segments: List[dict]  # List of {"start": float, "end": float} segments
    total_speech_duration: float
    processing_time_ms: float

    # Reference to original chunk
    original_chunk_id: str
