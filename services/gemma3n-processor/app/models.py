"""Data models for Gemma 3N Processor service."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class BaseMessage(BaseModel):
    """Base message model with common fields."""

    device_id: str = Field(..., description="Device ID that generated the data")
    recorded_at: datetime = Field(..., description="Timestamp when data was recorded")
    schema_version: str = Field(default="v1", description="Schema version")


class TextMessage(BaseMessage):
    """Input message for text data from Kafka."""

    text: str = Field(..., description="Text content to process")
    context: Optional[str] = Field(None, description="Additional context")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class ImageMessage(BaseMessage):
    """Input message for image data from Kafka."""

    data: str = Field(..., description="Base64 encoded image data")
    format: Optional[str] = Field(None, description="Image format (jpg, png, etc)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class AudioMessage(BaseMessage):
    """Input message for audio data from Kafka."""

    data: str = Field(..., description="Base64 encoded audio data")
    format: Optional[str] = Field(None, description="Audio format (wav, mp3, etc)")
    duration: Optional[float] = Field(None, description="Audio duration in seconds")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class MultimodalRequest(BaseModel):
    """Request model for multimodal processing."""

    prompt: str = Field(..., description="Processing prompt/instruction")
    text: Optional[str] = Field(None, description="Text input")
    image_data: Optional[str] = Field(None, description="Base64 encoded image")
    audio_data: Optional[str] = Field(None, description="Base64 encoded audio")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens to generate")
    temperature: Optional[float] = Field(None, description="Sampling temperature")


class AnalysisResult(BaseModel):
    """Individual analysis result."""

    type: str = Field(..., description="Type of analysis (text, image, audio)")
    content: str = Field(..., description="Analysis result content")
    confidence: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Confidence score"
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class MultimodalAnalysisResult(BaseMessage):
    """Multimodal analysis output to be sent to Kafka."""

    model_config = {"protected_namespaces": ()}

    # Core analysis
    analysis_type: str = Field(..., description="Type of multimodal analysis performed")
    primary_result: str = Field(..., description="Primary analysis result")

    # Individual modality results
    text_analysis: Optional[AnalysisResult] = Field(
        None, description="Text analysis result"
    )
    image_analysis: Optional[AnalysisResult] = Field(
        None, description="Image analysis result"
    )
    audio_analysis: Optional[AnalysisResult] = Field(
        None, description="Audio analysis result"
    )

    # Cross-modal insights
    multimodal_insights: Optional[List[str]] = Field(
        None, description="Insights from cross-modal analysis"
    )

    # Structured outputs
    entities: Optional[List[Dict[str, Any]]] = Field(
        None, description="Extracted entities across modalities"
    )
    sentiment: Optional[Dict[str, float]] = Field(
        None, description="Sentiment analysis results"
    )
    topics: Optional[List[str]] = Field(None, description="Identified topics/themes")

    # Processing metadata
    processing_time_ms: float = Field(
        ..., description="Time taken to process in milliseconds"
    )
    model_version: str = Field(default="gemma3n:e4b", description="Model version used")

    # Quality metrics
    input_quality: Optional[Dict[str, float]] = Field(
        None, description="Quality metrics for input data"
    )
    output_confidence: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Overall confidence in results"
    )


class OllamaResponse(BaseModel):
    """Response from Ollama API."""

    model: str
    created_at: datetime
    response: str
    done: bool
    context: Optional[List[int]] = None
    total_duration: Optional[int] = None
    load_duration: Optional[int] = None
    prompt_eval_count: Optional[int] = None
    prompt_eval_duration: Optional[int] = None
    eval_count: Optional[int] = None
    eval_duration: Optional[int] = None


class HealthStatus(BaseModel):
    """Health check response model."""

    status: str = Field(..., description="Health status")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Check timestamp"
    )
    checks: Optional[Dict[str, bool]] = Field(
        None, description="Individual component checks"
    )


class ProcessingMetrics(BaseModel):
    """Metrics for monitoring processing performance."""

    requests_processed: int = Field(default=0, description="Total requests processed")
    total_processing_time: float = Field(
        default=0.0, description="Total processing time"
    )
    average_processing_time: float = Field(
        default=0.0, description="Average processing time"
    )
    errors_count: int = Field(default=0, description="Number of errors encountered")
    last_processed: Optional[datetime] = Field(
        None, description="Last processing timestamp"
    )
