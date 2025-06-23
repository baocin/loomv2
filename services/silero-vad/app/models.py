"""Data models for Silero VAD service."""

from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator
import base64


class BaseMessage(BaseModel):
    """Base message model with common fields."""

    device_id: str = Field(..., description="Unique device identifier")
    recorded_at: datetime = Field(..., description="Timestamp when data was recorded")
    received_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow, description="Timestamp when message was received"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional metadata"
    )


class AudioChunk(BaseMessage):
    """Audio chunk model matching device.audio.raw schema."""

    audio_data: str = Field(..., description="Base64 encoded audio data")
    sample_rate: int = Field(..., description="Audio sample rate in Hz")
    channels: int = Field(..., description="Number of audio channels")
    duration_ms: Optional[float] = Field(None, description="Duration in milliseconds")
    format: str = Field(default="pcm", description="Audio format")
    
    @field_validator("audio_data")
    @classmethod
    def validate_base64(cls, v: str) -> str:
        """Validate that audio_data is valid base64."""
        try:
            base64.b64decode(v, validate=True)
        except Exception:
            raise ValueError("Invalid base64 encoding for audio_data")
        return v
    
    def decode_audio(self) -> bytes:
        """Decode base64 audio data to bytes."""
        return base64.b64decode(self.audio_data)


class VADFilteredAudio(BaseMessage):
    """VAD filtered audio chunk for media.audio.vad_filtered topic."""

    audio_data: str = Field(..., description="Base64 encoded audio data containing speech")
    sample_rate: int = Field(..., description="Audio sample rate in Hz")
    channels: int = Field(..., description="Number of audio channels")
    duration_ms: float = Field(..., description="Duration in milliseconds")
    format: str = Field(default="pcm", description="Audio format")
    vad_confidence: float = Field(..., description="VAD confidence score (0-1)")
    speech_start_ms: float = Field(..., description="Speech start time in chunk")
    speech_end_ms: float = Field(..., description="Speech end time in chunk")
    
    def encode_audio(self, audio_bytes: bytes) -> None:
        """Encode audio bytes to base64."""
        self.audio_data = base64.b64encode(audio_bytes).decode("utf-8")