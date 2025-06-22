"""Schema validation utilities for Loom message types."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from jsonschema import Draft7Validator

logger = logging.getLogger(__name__)

# Cache for loaded schemas
_SCHEMA_CACHE: Dict[str, Dict[str, Any]] = {}


def get_schema_path() -> Path:
    """Get the path to the schemas directory."""
    return Path(__file__).parent.parent / "schemas"


def load_schema(schema_path: str) -> Dict[str, Any]:
    """Load a JSON schema from the schemas directory.

    Args:
        schema_path: Relative path to schema file (e.g., "device/sensor/gps/v1.json")

    Returns:
        Loaded JSON schema as dictionary

    Raises:
        FileNotFoundError: If schema file doesn't exist
        json.JSONDecodeError: If schema file is invalid JSON
    """
    if schema_path in _SCHEMA_CACHE:
        return _SCHEMA_CACHE[schema_path]

    full_path = get_schema_path() / schema_path
    if not full_path.exists():
        raise FileNotFoundError(f"Schema not found: {full_path}")

    with open(full_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    # Validate the schema itself
    Draft7Validator.check_schema(schema)

    _SCHEMA_CACHE[schema_path] = schema
    return schema


def validate_message(message: Dict[str, Any], schema_path: str) -> Optional[str]:
    """Validate a message against a JSON schema.

    Args:
        message: Message data to validate
        schema_path: Relative path to schema file

    Returns:
        None if valid, error message string if invalid
    """
    try:
        schema = load_schema(schema_path)
        validator = Draft7Validator(schema)

        # Collect all validation errors
        errors = list(validator.iter_errors(message))
        if errors:
            error_messages = []
            for error in errors:
                path = " -> ".join(str(p) for p in error.absolute_path)
                error_messages.append(f"{path}: {error.message}")
            return "; ".join(error_messages)

        return None

    except Exception as e:
        logger.error(f"Schema validation error: {e}")
        return f"Schema validation failed: {str(e)}"


def get_schema_for_topic(topic: str) -> Optional[str]:
    """Get the schema path for a given Kafka topic.

    Args:
        topic: Kafka topic name (e.g., "device.sensor.gps.raw")

    Returns:
        Schema path or None if no schema found
    """
    # Map topic names to schema paths
    topic_schema_map = {
        "device.sensor.gps.raw": "device/sensor/gps/v1.json",
        "device.sensor.accelerometer.raw": "device/sensor/accelerometer/v1.json",
        "device.health.heartrate.raw": "device/health/heartrate/v1.json",
        "media.audio.vad_filtered": "media/audio/vad_filtered/v1.json",
        # Add more mappings as schemas are created
    }

    return topic_schema_map.get(topic)


def validate_topic_message(topic: str, message: Dict[str, Any]) -> Optional[str]:
    """Validate a message for a specific Kafka topic.

    Args:
        topic: Kafka topic name
        message: Message data to validate

    Returns:
        None if valid, error message string if invalid
    """
    schema_path = get_schema_for_topic(topic)
    if not schema_path:
        logger.warning(f"No schema found for topic: {topic}")
        return None

    return validate_message(message, schema_path)
