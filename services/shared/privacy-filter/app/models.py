"""Pydantic models for the Privacy Filter service."""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EntityType(str, Enum):
    """Supported PII entity types."""
    EMAIL = "EMAIL_ADDRESS"
    PHONE = "PHONE_NUMBER"
    SSN = "US_SSN"
    CREDIT_CARD = "CREDIT_CARD"
    PERSON = "PERSON"
    LOCATION = "LOCATION"
    DATE = "DATE_TIME"
    URL = "URL"
    IP_ADDRESS = "IP_ADDRESS"
    IBAN = "IBAN_CODE"
    US_DRIVER_LICENSE = "US_DRIVER_LICENSE"
    CRYPTO = "CRYPTO"


class ReplacementStrategy(str, Enum):
    """Data replacement strategies."""
    REDACT = "redact"  # Replace with [REDACTED]
    MASK = "mask"      # Replace with ***
    HASH = "hash"      # Replace with hash
    FAKE = "fake"      # Replace with fake data
    REMOVE = "remove"  # Remove entirely


class PIIEntity(BaseModel):
    """Detected PII entity."""
    entity_type: str = Field(description="Type of PII entity")
    start: int = Field(description="Start position in text")
    end: int = Field(description="End position in text")
    text: str = Field(description="Original text")
    confidence: float = Field(description="Detection confidence score", ge=0, le=1)


class PIIDetectionRequest(BaseModel):
    """Request for PII detection."""
    text: str = Field(description="Text to analyze for PII")
    entity_types: Optional[List[EntityType]] = Field(
        default=None, 
        description="Specific entity types to detect (all if None)"
    )
    language: str = Field(default="en", description="Language code")
    context: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Additional context for auditing"
    )


class PIIDetectionResponse(BaseModel):
    """Response from PII detection."""
    entities: List[PIIEntity] = Field(description="Detected PII entities")
    has_pii: bool = Field(description="Whether any PII was detected")
    processed_at: float = Field(description="Processing timestamp")


class FilterRequest(BaseModel):
    """Request for data filtering."""
    data: Dict[str, Any] = Field(description="Data to filter")
    rules: List[EntityType] = Field(description="PII types to filter")
    replacement_strategy: ReplacementStrategy = Field(
        default=ReplacementStrategy.REDACT,
        description="How to replace detected PII"
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional context for auditing"
    )


class FilterResponse(BaseModel):
    """Response from data filtering."""
    filtered_data: Dict[str, Any] = Field(description="Data with PII filtered")
    entities_found: List[PIIEntity] = Field(description="PII entities that were filtered")
    original_entities_count: int = Field(description="Number of entities found")
    processed_at: float = Field(description="Processing timestamp")


class AnonymizeRequest(BaseModel):
    """Request for data anonymization."""
    data: Dict[str, Any] = Field(description="Data to anonymize")
    entity_types: Optional[List[EntityType]] = Field(
        default=None,
        description="Specific entity types to anonymize (all if None)"
    )
    preserve_format: bool = Field(
        default=True,
        description="Whether to preserve original format"
    )
    seed: Optional[int] = Field(
        default=None,
        description="Random seed for consistent fake data"
    )
    return_mapping: bool = Field(
        default=False,
        description="Whether to return anonymization mapping"
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional context for auditing"
    )


class AnonymizeResponse(BaseModel):
    """Response from data anonymization."""
    anonymized_data: Dict[str, Any] = Field(description="Anonymized data")
    anonymization_map: Dict[str, str] = Field(
        description="Mapping of original to anonymized values"
    )
    processed_at: float = Field(description="Processing timestamp")


class AuditLogEntry(BaseModel):
    """Audit log entry for privacy operations."""
    operation: str = Field(description="Type of operation performed")
    timestamp: float = Field(description="Operation timestamp")
    entities_processed: int = Field(description="Number of entities processed")
    data_size: int = Field(description="Size of processed data")
    context: Optional[Dict[str, Any]] = Field(description="Operation context")
    user_id: Optional[str] = Field(description="User who performed operation")


class PrivacyStats(BaseModel):
    """Privacy service statistics."""
    total_requests: int = Field(description="Total requests processed")
    pii_detections: int = Field(description="Total PII detections")
    entities_by_type: Dict[str, int] = Field(description="Entity counts by type")
    avg_processing_time: float = Field(description="Average processing time")
    uptime_seconds: float = Field(description="Service uptime")