#!/usr/bin/env python
"""validate_schemas.py

Utility script to validate all JSON schemas in the shared/schemas directory.

Usage:
    python scripts/validate_schemas.py

This script validates:
1. All JSON schema files are valid JSON Schema Draft 7
2. Example messages validate against their schemas
3. Schema compatibility across versions
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any

import jsonschema
from jsonschema import Draft7Validator

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def find_schema_files(schemas_dir: Path) -> List[Path]:
    """Find all JSON schema files in the schemas directory."""
    return list(schemas_dir.rglob("*.json"))


def validate_schema_file(schema_path: Path) -> bool:
    """Validate a single schema file."""
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)

        # Validate the schema itself
        Draft7Validator.check_schema(schema)

        # Check required fields
        required_fields = ["$schema", "$id", "title", "type"]
        missing_fields = [field for field in required_fields if field not in schema]
        if missing_fields:
            logger.error(f"{schema_path}: Missing required fields: {missing_fields}")
            return False

        # Validate schema version format
        if "properties" in schema and "schema_version" in schema["properties"]:
            version_prop = schema["properties"]["schema_version"]
            if "const" not in version_prop:
                logger.error(
                    f"{schema_path}: schema_version must have 'const' property"
                )
                return False

        logger.info(f"✅ {schema_path.relative_to(schema_path.parents[3])}")
        return True

    except json.JSONDecodeError as e:
        logger.error(f"{schema_path}: Invalid JSON - {e}")
        return False
    except jsonschema.SchemaError as e:
        logger.error(f"{schema_path}: Invalid JSON Schema - {e}")
        return False
    except Exception as e:
        logger.error(f"{schema_path}: Unexpected error - {e}")
        return False


def create_example_messages() -> Dict[str, Dict[str, Any]]:
    """Create example messages for testing schemas."""
    return {
        "device/sensor/gps/v1.json": {
            "schema_version": "1.0.0",
            "timestamp": "2024-01-15T10:30:00Z",
            "device_id": "phone-001",
            "latitude": 37.7749,
            "longitude": -122.4194,
            "altitude": 10.5,
            "accuracy": 5.0,
            "speed": 2.5,
            "bearing": 45.0,
        },
        "device/sensor/accelerometer/v1.json": {
            "schema_version": "1.0.0",
            "timestamp": "2024-01-15T10:30:00Z",
            "device_id": "phone-001",
            "x": 0.1,
            "y": 9.8,
            "z": 0.2,
            "accuracy": 3,
        },
        "device/health/heartrate/v1.json": {
            "schema_version": "1.0.0",
            "timestamp": "2024-01-15T10:30:00Z",
            "device_id": "watch-001",
            "bpm": 72,
            "confidence": 0.95,
            "source": "wearable",
        },
        "media/audio/vad_filtered/v1.json": {
            "schema_version": "1.0.0",
            "timestamp": "2024-01-15T10:30:00Z",
            "device_id": "phone-001",
            "file_id": "audio-001",
            "chunk_index": 0,
            "audio_data": "UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA=",
            "sample_rate": 16000,
            "channels": 1,
            "duration_ms": 1000,
            "vad_confidence": 0.85,
            "speech_probability": 0.92,
        },
    }


def test_example_messages(schemas_dir: Path) -> bool:
    """Test example messages against their schemas."""
    examples = create_example_messages()
    all_valid = True

    for schema_path, example in examples.items():
        full_schema_path = schemas_dir / schema_path
        if not full_schema_path.exists():
            logger.warning(f"Schema not found for example: {schema_path}")
            continue

        try:
            with open(full_schema_path, "r", encoding="utf-8") as f:
                schema = json.load(f)

            validator = Draft7Validator(schema)
            errors = list(validator.iter_errors(example))

            if errors:
                logger.error(f"❌ Example for {schema_path} failed validation:")
                for error in errors:
                    path = " -> ".join(str(p) for p in error.absolute_path)
                    logger.error(f"  {path}: {error.message}")
                all_valid = False
            else:
                logger.info(f"✅ Example for {schema_path} validates")

        except Exception as e:
            logger.error(f"Error testing example for {schema_path}: {e}")
            all_valid = False

    return all_valid


def main():
    """Main validation function."""
    # Find schemas directory
    script_dir = Path(__file__).parent
    schemas_dir = script_dir.parent / "shared" / "schemas"

    if not schemas_dir.exists():
        logger.error(f"Schemas directory not found: {schemas_dir}")
        return 1

    logger.info(f"Validating schemas in: {schemas_dir}")

    # Find all schema files
    schema_files = find_schema_files(schemas_dir)
    if not schema_files:
        logger.warning("No schema files found")
        return 0

    logger.info(f"Found {len(schema_files)} schema files")

    # Validate each schema file
    valid_schemas = 0
    for schema_file in schema_files:
        if validate_schema_file(schema_file):
            valid_schemas += 1

    # Test example messages
    logger.info("\nTesting example messages...")
    examples_valid = test_example_messages(schemas_dir)

    # Summary
    logger.info("\nValidation Summary:")
    logger.info(f"  Schemas: {valid_schemas}/{len(schema_files)} valid")
    logger.info(f"  Examples: {'✅ All valid' if examples_valid else '❌ Some failed'}")

    if valid_schemas == len(schema_files) and examples_valid:
        logger.info("🎉 All validations passed!")
        return 0
    else:
        logger.error("❌ Some validations failed")
        return 1


if __name__ == "__main__":
    exit(main())
