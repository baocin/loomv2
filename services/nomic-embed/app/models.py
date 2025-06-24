"""Pydantic models for Nomic Embed Vision service."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class BaseMessage(BaseModel):
    """Base message structure for all Kafka messages."""

    schema_version: str = Field(default="1.0", description="Message schema version")
    device_id: str = Field(description="Client device identifier")
    recorded_at: datetime = Field(description="UTC timestamp when data was recorded")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when message was processed by server",
    )
    message_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique message ID",
    )


class TextEmbedding(BaseMessage):
    """Text embedding output message."""

    text_content: str = Field(description="Original text content")
    text_length: int = Field(description="Length of text in characters")
    embedding: List[float] = Field(description="Text embedding vector")
    embedding_model: str = Field(description="Model used for embedding")
    embedding_dimension: int = Field(description="Dimension of embedding vector")
    source_topic: str = Field(description="Original Kafka topic")
    source_message_id: str = Field(description="Original message ID")
    processing_time_ms: float = Field(description="Processing time in milliseconds")
    
    # Optional metadata from source
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata from source"
    )


class ImageEmbedding(BaseMessage):
    """Image embedding output message."""

    image_format: str = Field(description="Image format (jpeg, png, etc.)")
    image_width: int = Field(description="Image width in pixels")
    image_height: int = Field(description="Image height in pixels")
    image_size_bytes: int = Field(description="Image size in bytes")
    embedding: List[float] = Field(description="Image embedding vector")
    embedding_model: str = Field(description="Model used for embedding")
    embedding_dimension: int = Field(description="Dimension of embedding vector")
    source_topic: str = Field(description="Original Kafka topic")
    source_message_id: str = Field(description="Original message ID")
    processing_time_ms: float = Field(description="Processing time in milliseconds")
    
    # Optional metadata from source
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata from source"
    )
    
    # Optional image analysis results
    image_description: Optional[str] = Field(
        default=None, description="Generated image description"
    )


class EmbeddingRequest(BaseModel):
    """Direct embedding request for API endpoint."""

    text: Optional[str] = Field(default=None, description="Text to embed")
    image_data: Optional[str] = Field(
        default=None, description="Base64 encoded image data"
    )
    include_description: bool = Field(
        default=False, description="Generate image description"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class EmbeddingResponse(BaseModel):
    """Embedding API response."""

    text_embedding: Optional[List[float]] = Field(
        default=None, description="Text embedding vector"
    )
    image_embedding: Optional[List[float]] = Field(
        default=None, description="Image embedding vector"
    )
    image_description: Optional[str] = Field(
        default=None, description="Generated image description"
    )
    embedding_model: str = Field(description="Model used for embedding")
    embedding_dimension: int = Field(description="Dimension of embedding vector")
    processing_time_ms: float = Field(description="Processing time in milliseconds")
    message_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique message ID"
    )


class HealthCheck(BaseModel):
    """Health check response."""

    status: str = Field(default="healthy", description="Service status")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Check timestamp",
    )
    version: str = Field(default="0.1.0", description="Service version")
    model_loaded: bool = Field(description="Whether embedding model is loaded")
    model_name: str = Field(description="Name of loaded model")
    device: str = Field(description="Device being used (cpu/cuda)")
    total_processed: int = Field(
        default=0, description="Total items processed since startup"
    )
    queue_size: int = Field(default=0, description="Current processing queue size")


class ProcessingStats(BaseModel):
    """Processing statistics."""

    total_text_processed: int = Field(
        default=0, description="Total text items processed"
    )
    total_images_processed: int = Field(
        default=0, description="Total images processed"
    )
    average_text_processing_time_ms: float = Field(
        default=0.0, description="Average text processing time"
    )
    average_image_processing_time_ms: float = Field(
        default=0.0, description="Average image processing time"
    )
    queue_size: int = Field(default=0, description="Current queue size")
    model_memory_usage_mb: float = Field(
        default=0.0, description="Model memory usage in MB"
    )
    uptime_seconds: float = Field(default=0.0, description="Service uptime")


class BatchEmbeddingRequest(BaseModel):
    """Batch embedding request."""

    texts: List[str] = Field(default_factory=list, description="List of texts to embed")
    images: List[str] = Field(
        default_factory=list, description="List of base64 encoded images"
    )
    include_descriptions: bool = Field(
        default=False, description="Generate image descriptions"
    )
    batch_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Batch identifier"
    )


class BatchEmbeddingResponse(BaseModel):
    """Batch embedding response."""

    text_embeddings: List[List[float]] = Field(
        default_factory=list, description="Text embedding vectors"
    )
    image_embeddings: List[List[float]] = Field(
        default_factory=list, description="Image embedding vectors"
    )
    image_descriptions: List[Optional[str]] = Field(
        default_factory=list, description="Generated image descriptions"
    )
    batch_id: str = Field(description="Batch identifier")
    total_processed: int = Field(description="Total items processed in batch")
    total_processing_time_ms: float = Field(
        description="Total processing time for batch"
    )
    embedding_model: str = Field(description="Model used for embedding")
    embedding_dimension: int = Field(description="Dimension of embedding vectors")