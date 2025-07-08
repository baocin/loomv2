"""Data models for ONNX-ASR service matching kyutai-stt format."""

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


class Word(BaseModel):
    """Individual word with timing information."""

    word: str
    start_time: float
    end_time: float
    confidence: Optional[float] = Field(default=1.0)


class Transcript(BaseModel):
    """Transcription result matching kyutai-stt output format."""

    device_id: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    text: str
    words: List[Word]
    audio_chunk_id: str  # References the input chunk
    processing_time_ms: float
    model_name: str = "nvidia/parakeet-tdt-0.6b"

    # Optional metadata
    language: Optional[str] = "en"
    confidence: Optional[float] = None
