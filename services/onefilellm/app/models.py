"""Pydantic models for OneFileLLM service."""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class BaseMessage(BaseModel):
    """Base message structure for Kafka messages."""

    schema_version: str = Field(default="1.0", description="Message schema version")
    device_id: str = Field(description="Client device identifier")
    recorded_at: datetime = Field(description="UTC timestamp when data was recorded")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when message was processed by server",
    )
    message_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique message ID",
    )


class GitHubTask(BaseMessage):
    """GitHub URL processing task."""

    url: str = Field(description="GitHub URL to process")
    repository_type: str = Field(
        default="repository",
        description="Type of GitHub resource (repository, file, issue, pr)",
    )
    priority: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Processing priority (1=highest, 10=lowest)",
    )
    include_files: list[str] = Field(
        default_factory=list,
        description="File patterns to include (e.g., ['*.py', '*.md'])",
    )
    exclude_files: list[str] = Field(
        default_factory=list,
        description="File patterns to exclude",
    )
    max_file_size: int = Field(
        default=1048576,  # 1MB
        description="Maximum file size in bytes",
    )
    extract_options: dict[str, Any] = Field(
        default_factory=dict,
        description="Options for content extraction",
    )
    callback_webhook: str | None = Field(
        None,
        description="Webhook URL for processing completion notification",
    )


class DocumentTask(BaseMessage):
    """Document upload and processing task."""

    filename: str = Field(description="Original filename")
    file_data: str = Field(description="Base64 encoded file content")
    content_type: str = Field(
        default="application/octet-stream",
        description="MIME type of the file",
    )
    file_size: int = Field(description="File size in bytes")
    document_type: str = Field(
        default="general",
        description="Type of document (pdf, docx, txt, markdown, html)",
    )
    priority: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Processing priority (1=highest, 10=lowest)",
    )
    extract_options: dict[str, Any] = Field(
        default_factory=dict,
        description="Options for content extraction",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional document metadata",
    )
    callback_webhook: str | None = Field(
        None,
        description="Webhook URL for processing completion notification",
    )


class ProcessedGitHub(BaseMessage):
    """Processed GitHub content result."""

    original_url: str = Field(description="Original GitHub URL")
    repository_name: str = Field(description="Repository name (owner/repo)")
    repository_type: str = Field(description="Type of GitHub resource")
    aggregated_content: str = Field(description="Aggregated content from OneFileLLM")
    content_summary: str = Field(description="Brief summary of the content")
    file_count: int = Field(description="Number of files processed")
    total_size_bytes: int = Field(description="Total size of processed content")
    processing_duration_ms: int = Field(description="Processing time in milliseconds")
    files_processed: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of files that were processed",
    )
    files_skipped: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of files that were skipped",
    )
    extraction_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata about the extraction process",
    )
    onefilellm_version: str = Field(description="Version of OneFileLLM used")


class ProcessedDocument(BaseMessage):
    """Processed document content result."""

    original_filename: str = Field(description="Original filename")
    document_type: str = Field(description="Type of document")
    content_type: str = Field(description="MIME type of original file")
    extracted_text: str = Field(description="Extracted text content")
    content_summary: str = Field(description="Brief summary of the content")
    original_size_bytes: int = Field(description="Original file size")
    processing_duration_ms: int = Field(description="Processing time in milliseconds")
    extraction_method: str = Field(description="Method used for text extraction")
    language_detected: str | None = Field(None, description="Detected language")
    page_count: int | None = Field(None, description="Number of pages (for PDFs)")
    word_count: int = Field(description="Number of words in extracted text")
    character_count: int = Field(description="Number of characters in extracted text")
    extraction_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata about the extraction process",
    )
    onefilellm_version: str = Field(description="Version of OneFileLLM used")


class ProcessingError(BaseMessage):
    """Processing error message."""

    original_task_id: str = Field(description="ID of the original task")
    error_type: str = Field(description="Type of error")
    error_message: str = Field(description="Error description")
    error_details: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional error details",
    )
    retry_count: int = Field(default=0, description="Number of retry attempts")
    is_retryable: bool = Field(default=False, description="Whether error is retryable")


class HealthCheck(BaseModel):
    """Health check response."""

    status: str = Field(default="healthy", description="Service status")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Check timestamp",
    )
    version: str = Field(default="0.1.0", description="Service version")
    kafka_connected: bool = Field(description="Kafka connection status")
    database_connected: bool = Field(description="Database connection status")
    onefilellm_available: bool = Field(description="OneFileLLM availability status")
