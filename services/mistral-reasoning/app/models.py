"""Data models for Mistral reasoning service."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class WordTimestamp(BaseModel):
    """Word timestamp from STT processing."""
    device_id: str
    timestamp: datetime
    schema_version: str = "v1"
    message_id: str
    word_sequence: int
    word_text: str
    start_time_ms: int
    end_time_ms: int
    confidence_score: float
    speaker_id: Optional[str] = None
    language_code: str = "en"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ProcessedContent(BaseModel):
    """Processed URL content."""
    device_id: str
    timestamp: datetime
    schema_version: str = "v1"
    message_id: str
    url_id: str
    original_url: str
    domain: str
    content_type: str
    title: Optional[str] = None
    content_text: Optional[str] = None
    content_summary: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EmotionScore(BaseModel):
    """Audio emotion analysis result."""
    device_id: str
    timestamp: datetime
    schema_version: str = "v1"
    message_id: str
    segment_id: str
    predicted_emotion: str
    confidence_score: float
    valence_score: Optional[float] = None
    arousal_score: Optional[float] = None
    dominance_score: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FaceEmotion(BaseModel):
    """Face emotion analysis result."""
    device_id: str
    timestamp: datetime
    schema_version: str = "v1"
    message_id: str
    face_id: str
    emotion_label: str
    confidence_score: float
    age_estimate: Optional[int] = None
    gender_estimate: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ReasoningStep(BaseModel):
    """Individual step in reasoning chain."""
    step_number: int
    step_type: str  # "observation", "inference", "hypothesis", "conclusion"
    content: str
    confidence: float = Field(ge=0.0, le=1.0)
    supporting_evidence: List[str] = Field(default_factory=list)


class ContextualInsight(BaseModel):
    """High-level contextual insight."""
    insight_type: str  # "pattern", "anomaly", "trend", "correlation"
    description: str
    confidence: float = Field(ge=0.0, le=1.0)
    temporal_scope: str  # "immediate", "recent", "historical"
    affected_domains: List[str] = Field(default_factory=list)


class ReasoningChain(BaseModel):
    """Complete reasoning chain analysis."""
    device_id: str
    timestamp: datetime
    schema_version: str = "v1"
    message_id: str
    reasoning_id: str
    
    # Context classification
    context_type: str
    context_confidence: float = Field(ge=0.0, le=1.0)
    
    # Reasoning process
    reasoning_chain: List[ReasoningStep]
    conclusion_text: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    
    # Input sources and metadata
    input_sources: List[Dict[str, Any]] = Field(default_factory=list)
    data_timespan_minutes: Optional[float] = None
    
    # Extracted information
    key_topics: List[str] = Field(default_factory=list)
    entities_mentioned: Dict[str, List[str]] = Field(default_factory=dict)  # {type: [entities]}
    
    # Contextual insights
    insights: List[ContextualInsight] = Field(default_factory=list)
    
    # Temporal and spatial context
    temporal_context: Optional[Dict[str, Any]] = None
    spatial_context: Optional[Dict[str, Any]] = None
    
    # Processing metadata
    processing_duration_ms: Optional[float] = None
    model_version: str
    prompt_version: str = "v1.0"
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)