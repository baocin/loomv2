"""Data models for VAD Processor."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
import base64


class AudioChunk(BaseModel):
    """Raw audio chunk from Kafka."""

    device_id: str
    timestamp: datetime
    schema_version: str = "v1"
    chunk_number: int
    audio_data: str  # Base64 encoded
    format: str
    sample_rate: int
    channels: int
    duration_ms: int
    metadata: Optional[dict] = None

    def decode_audio(self) -> bytes:
        """Decode base64 audio data."""
        return base64.b64decode(self.audio_data)


class VADSegment(BaseModel):
    """Voice activity detection segment."""

    start_ms: int
    end_ms: int
    confidence: float


class VADResult(BaseModel):
    """VAD processing result."""

    device_id: str
    timestamp: datetime
    schema_version: str = "v1"
    source_timestamp: datetime
    has_speech: bool
    confidence: float
    audio_segment: str  # Base64 encoded
    segment_start_ms: int
    segment_duration_ms: int
    processing_model: str = "silero_vad"
    processing_version: str
    metadata: Optional[dict] = None

    def encode_audio(self, audio_bytes: bytes) -> None:
        """Encode audio bytes to base64."""
        self.audio_segment = base64.b64encode(audio_bytes).decode('utf-8')