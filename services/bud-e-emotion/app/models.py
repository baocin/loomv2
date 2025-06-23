"""Data models for BUD-E emotion analysis service."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import base64


class VADFilteredAudio(BaseModel):
    """Audio segment that has been filtered through VAD."""
    device_id: str
    timestamp: datetime
    schema_version: str = "v1"
    message_id: str
    audio_data: str  # Base64 encoded
    sample_rate: int
    channels: int
    duration_ms: float
    format: str
    vad_confidence: float
    speech_start_ms: float
    speech_end_ms: float
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def decode_audio(self) -> bytes:
        """Decode base64 audio data to bytes."""
        return base64.b64decode(self.audio_data)


class EmotionScore(BaseModel):
    """Individual emotion score."""
    emotion: str
    confidence: float = Field(ge=0.0, le=1.0)


class AudioEmotionAnalysis(BaseModel):
    """Audio emotion analysis result."""
    device_id: str
    timestamp: datetime
    schema_version: str = "v1"
    message_id: str
    segment_id: str
    
    # Primary emotion prediction
    predicted_emotion: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    
    # Dimensional scores
    valence_score: Optional[float] = Field(None, ge=-1.0, le=1.0)  # Positive/negative
    arousal_score: Optional[float] = Field(None, ge=-1.0, le=1.0)  # High/low energy
    dominance_score: Optional[float] = Field(None, ge=-1.0, le=1.0)  # Control/submission
    
    # All emotion probabilities
    emotion_probabilities: Dict[str, float] = Field(default_factory=dict)
    
    # Audio analysis metadata
    audio_features: Optional[Dict[str, Any]] = Field(default_factory=dict)
    processing_duration_ms: Optional[float] = None
    model_version: str
    
    # Source segment information
    source_start_ms: float
    source_end_ms: float
    source_duration_ms: float
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)