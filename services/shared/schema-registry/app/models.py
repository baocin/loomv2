"""Pydantic models for the Schema Registry service."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SchemaValidationRequest(BaseModel):
    """Request model for schema validation."""

    schema_name: str = Field(description="Name of the schema to validate against")
    data: Dict[str, Any] = Field(description="Data to validate")


class SchemaValidationResponse(BaseModel):
    """Response model for schema validation."""

    valid: bool = Field(description="Whether the data is valid")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    schema_name: str = Field(description="Name of the schema used")


class SchemaInfo(BaseModel):
    """Information about a schema."""

    name: str = Field(description="Schema name")
    version: str = Field(description="Schema version")
    description: Optional[str] = Field(default=None, description="Schema description")
    schema: Dict[str, Any] = Field(description="JSON Schema definition")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
    usage_count: int = Field(default=0, description="Number of times used")


class SchemaVersion(BaseModel):
    """Schema version information."""

    version: str = Field(description="Version identifier")
    created_at: datetime = Field(description="Creation timestamp")
    compatibility: str = Field(
        description="Compatibility level (BACKWARD, FORWARD, FULL)"
    )
    changes: List[str] = Field(default_factory=list, description="List of changes")


class HealthStatus(BaseModel):
    """Health status response."""

    status: str = Field(description="Health status")
    timestamp: float = Field(description="Check timestamp")
    cache_connected: bool = Field(description="Cache connection status")
    schemas_loaded: int = Field(description="Number of schemas loaded")
