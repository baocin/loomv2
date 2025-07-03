"""AI context endpoint for exposing latest data to LLMs."""

from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..auth import verify_api_key
from ..database import db_manager

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


class TableInfo(BaseModel):
    """Information about a single table's latest data."""

    data: dict[str, Any] | None = Field(description="Latest row data from the table")
    row_count: int | None = Field(description="Total number of rows in the table")
    latest_timestamp: str | None = Field(description="Timestamp of the latest entry")
    error: str | None = Field(default=None, description="Error message if query failed")


class AIContextResponse(BaseModel):
    """Response model for AI context endpoint."""

    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this context was generated",
    )
    device_count: int = Field(description="Number of unique devices in the system")
    summary: dict[str, str] = Field(description="High-level summary of available data")
    tables: dict[str, TableInfo] = Field(description="Latest data from each table")
    context_prompt: str = Field(
        description="Suggested prompt for LLMs to understand this data",
    )


@router.get(
    "/context",
    response_model=AIContextResponse,
    summary="Get latest context from all tables",
    description="Retrieves the most recent row from each database table, formatted for LLM consumption",
)
async def get_ai_context(
    api_key: str = Depends(verify_api_key),
) -> AIContextResponse:
    """Get latest data from all tables formatted for AI/LLM consumption.

    This endpoint provides a comprehensive snapshot of the most recent data
    across all tables in the system, making it easy for LLMs to understand
    the current state of the Loom v2 personal informatics pipeline.
    """
    try:
        if not db_manager.is_connected:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database not connected",
            )

        # Get latest data from all tables
        table_data = await db_manager.get_latest_from_all_tables()

        # Calculate summary statistics
        total_tables = len(table_data)
        populated_tables = sum(
            1 for t in table_data.values() if t.get("row_count", 0) > 0
        )
        error_tables = sum(1 for t in table_data.values() if t.get("error"))

        # Get device count from devices table
        device_count = 0
        if "devices" in table_data and table_data["devices"].get("row_count"):
            device_count = table_data["devices"]["row_count"]

        # Create summary of data categories
        summary = {
            "total_tables": f"{total_tables} tables in system",
            "populated_tables": f"{populated_tables} tables with data",
            "error_tables": f"{error_tables} tables with errors",
            "latest_activity": _get_latest_activity(table_data),
            "active_sensors": _get_active_sensors(table_data),
            "active_processors": _get_active_processors(table_data),
        }

        # Convert table data to response format
        tables = {}
        for table_name, data in table_data.items():
            tables[table_name] = TableInfo(**data)

        # Generate context prompt for LLMs
        context_prompt = _generate_context_prompt(table_data, device_count)

        return AIContextResponse(
            device_count=device_count,
            summary=summary,
            tables=tables,
            context_prompt=context_prompt,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get AI context", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve context: {e!s}",
        )


def _get_latest_activity(table_data: dict[str, Any]) -> str:
    """Get description of latest activity across all tables."""
    latest_time = None
    latest_table = None

    for table_name, data in table_data.items():
        if data.get("latest_timestamp") and not data.get("error"):
            try:
                # Parse ISO format timestamp
                timestamp = datetime.fromisoformat(
                    data["latest_timestamp"].replace("Z", "+00:00"),
                )
                if latest_time is None or timestamp > latest_time:
                    latest_time = timestamp
                    latest_table = table_name
            except:
                continue

    if latest_table:
        time_ago = datetime.utcnow() - latest_time
        if time_ago.total_seconds() < 60:
            return (
                f"Last activity {int(time_ago.total_seconds())}s ago in {latest_table}"
            )
        elif time_ago.total_seconds() < 3600:
            return f"Last activity {int(time_ago.total_seconds() / 60)}m ago in {latest_table}"
        else:
            return f"Last activity {int(time_ago.total_seconds() / 3600)}h ago in {latest_table}"

    return "No recent activity detected"


def _get_active_sensors(table_data: dict[str, Any]) -> str:
    """Get list of active sensors based on recent data."""
    active_sensors = []

    sensor_tables = {
        "device_sensor_gps_raw": "GPS",
        "device_sensor_accelerometer_raw": "Accelerometer",
        "device_health_heartrate_raw": "Heart Rate",
        "device_audio_raw": "Audio",
        "device_image_camera_raw": "Camera",
        "device_state_power_raw": "Power",
    }

    for table, sensor_name in sensor_tables.items():
        if table in table_data and table_data[table].get("row_count", 0) > 0:
            active_sensors.append(sensor_name)

    return (
        f"{len(active_sensors)} active: {', '.join(active_sensors)}"
        if active_sensors
        else "No active sensors"
    )


def _get_active_processors(table_data: dict[str, Any]) -> str:
    """Get list of active AI processors based on processed data."""
    active_processors = []

    processor_tables = {
        "media_audio_vad_filtered": "VAD",
        "media_text_transcribed_words": "Speech-to-Text",
        "media_image_analysis_minicpm_results": "Vision Analysis",
        "analysis_inferred_context_mistral_results": "Context Inference",
    }

    for table, processor_name in processor_tables.items():
        if table in table_data and table_data[table].get("row_count", 0) > 0:
            active_processors.append(processor_name)

    return (
        f"{len(active_processors)} active: {', '.join(active_processors)}"
        if active_processors
        else "No active processors"
    )


def _generate_context_prompt(table_data: dict[str, Any], device_count: int) -> str:
    """Generate a context prompt for LLMs to understand the data."""
    prompt_parts = [
        "This is data from a Loom v2 personal informatics system that collects and processes data from various devices.",
        f"The system currently has {device_count} registered device(s).",
        "",
        "Available data categories:",
    ]

    # Group tables by category
    categories = {
        "Device Sensors": ["gps", "accelerometer", "heartrate", "power", "temperature"],
        "Media": ["audio", "image", "video"],
        "Digital Activity": ["clipboard", "web_analytics", "notes"],
        "System Events": ["os_events", "app_lifecycle"],
        "External Sources": ["twitter", "calendar", "email", "hackernews"],
        "AI Processing": ["transcribed", "emotion", "context", "analysis"],
    }

    for category, keywords in categories.items():
        category_tables = []
        for table_name, data in table_data.items():
            if (
                any(kw in table_name for kw in keywords)
                and data.get("row_count", 0) > 0
            ):
                category_tables.append(table_name)

        if category_tables:
            prompt_parts.append(
                f"- {category}: {len(category_tables)} tables with data",
            )

    prompt_parts.extend(
        [
            "",
            "The latest data from each table is provided above. Use this context to understand:",
            "1. What sensors and data sources are active",
            "2. The types of activities and events being tracked",
            "3. Recent user behavior and context",
            "4. Results from AI processing pipelines",
        ],
    )

    return "\n".join(prompt_parts)
