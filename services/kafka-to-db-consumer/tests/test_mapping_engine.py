"""Unit tests for the MappingEngine."""

import base64
from datetime import datetime

import pytest

from app.mapping_engine import MappingEngine


class TestMappingEngine:
    """Test the mapping engine functionality."""

    @pytest.fixture
    def engine(self, sample_mapping_config):
        """Create a mapping engine instance."""
        # Create a test instance and set config directly
        engine = MappingEngine.__new__(MappingEngine)
        engine.config = sample_mapping_config
        return engine

    def test_engine_initialization(self, engine, sample_mapping_config):
        """Test that the engine initializes correctly."""
        assert engine.config == sample_mapping_config

    def test_get_topic_mapping(self, engine):
        """Test getting mapping for a configured topic."""
        mapping = engine.get_topic_mapping("device.sensor.gps.raw")

        assert mapping is not None
        assert mapping["table"] == "device_sensor_gps_raw"
        assert "field_mappings" in mapping
        assert mapping["field_mappings"]["data.latitude"] == "latitude"

    def test_get_topic_mapping_unknown(self, engine):
        """Test getting mapping for an unknown topic returns None."""
        mapping = engine.get_topic_mapping("unknown.topic")
        assert mapping is None

    def test_get_supported_topics(self, engine):
        """Test getting list of supported topics."""
        topics = engine.get_supported_topics()
        assert isinstance(topics, list)
        assert "device.sensor.gps.raw" in topics

    def test_map_message_to_record_gps(self, engine, sample_gps_message):
        """Test mapping a GPS message to database record."""
        topic = "device.sensor.gps.raw"
        result = engine.map_message_to_record(topic, sample_gps_message)

        assert result is not None
        table_name, record, upsert_key = result

        assert table_name == "device_sensor_gps_raw"
        assert upsert_key == "trace_id, timestamp"

        # Check mapped fields
        assert record["trace_id"] == "test-trace-123"
        assert record["device_id"] == "test-device-1"
        assert record["latitude"] == 37.7749
        assert record["longitude"] == -122.4194
        assert record["bearing"] == 180.0  # heading maps to bearing
        assert "created_at" in record

    def test_map_message_to_record_missing_required(self, engine):
        """Test mapping a message with missing required fields."""
        topic = "device.sensor.gps.raw"
        invalid_message = {
            "device_id": "test-123",
            # Missing required fields: trace_id, timestamp, data.latitude, data.longitude
        }

        result = engine.map_message_to_record(topic, invalid_message)
        assert result is None

    def test_map_message_to_record_unknown_topic(self, engine):
        """Test mapping a message for unknown topic."""
        result = engine.map_message_to_record("unknown.topic", {"test": "data"})
        assert result is None

    def test_extract_field_value(self, engine):
        """Test the _extract_field_value method."""
        # Simple field
        data = {"device_id": "test-123"}
        assert engine._extract_field_value(data, "device_id") == "test-123"

        # Nested field
        data = {"data": {"latitude": 37.7749, "location": {"city": "San Francisco"}}}
        assert engine._extract_field_value(data, "data.latitude") == 37.7749
        assert (
            engine._extract_field_value(data, "data.location.city") == "San Francisco"
        )

        # Missing field
        assert engine._extract_field_value(data, "missing.field") is None

    def test_convert_data_type(self, engine):
        """Test the _convert_data_type method."""
        # Integer
        assert engine._convert_data_type("123", "integer") == 123
        assert engine._convert_data_type(123.5, "integer") == 123

        # Float
        assert engine._convert_data_type("123.45", "float") == 123.45
        assert engine._convert_data_type(123, "float") == 123.0

        # Boolean
        assert engine._convert_data_type("true", "boolean") is True
        assert engine._convert_data_type("false", "boolean") is False
        assert engine._convert_data_type(1, "boolean") is True
        assert engine._convert_data_type(0, "boolean") is False

        # Timestamp
        result = engine._convert_data_type("2025-06-26T12:00:00Z", "timestamp")
        assert isinstance(result, datetime)

        # Array
        arr = ["item1", "item2"]
        assert engine._convert_data_type(arr, "array") == arr

    def test_apply_transformation(self, engine):
        """Test the _apply_transformation method."""
        # Base64 decode
        original = b"Hello, World!"
        encoded = base64.b64encode(original).decode("utf-8")
        result = engine._apply_transformation(encoded, "base64_decode")
        assert result == original

        # Unknown transformation
        result = engine._apply_transformation("test", "unknown_transform")
        assert result == "test"  # Should return original value

    def test_map_message_with_transforms(self, engine):
        """Test mapping a message that requires transformations."""
        # Add audio topic with base64 transform
        engine.config["topics"]["device.audio.raw"] = {
            "table": "device_audio_raw",
            "field_mappings": {
                "trace_id": "trace_id",
                "device_id": "device_id",
                "timestamp": "timestamp",
                "data.audio_data": "audio_data",
            },
            "transforms": {"audio_data": "base64_decode"},
            "required_fields": ["trace_id", "device_id", "timestamp"],
        }

        # Create message with base64 encoded audio
        audio_data = b"fake audio data"
        encoded_audio = base64.b64encode(audio_data).decode("utf-8")

        message = {
            "trace_id": "audio-123",
            "device_id": "mic-1",
            "timestamp": "2025-06-26T12:00:00Z",
            "data": {"audio_data": encoded_audio},
        }

        result = engine.map_message_to_record("device.audio.raw", message)
        assert result is not None

        table_name, record, upsert_key = result
        assert record["audio_data"] == audio_data  # Should be decoded

    def test_map_message_with_data_types(self, engine):
        """Test mapping with data type conversions."""
        message = {
            "trace_id": "test-123",
            "device_id": "device-1",
            "timestamp": "2025-06-26T12:00:00Z",
            "schema_version": "v1",
            "data": {
                "latitude": "37.7749",  # String that should be float
                "longitude": "-122.4194",
                "altitude": 100,
                "accuracy": 5,
                "speed": "10.5",
                "heading": "180",
            },
        }

        result = engine.map_message_to_record("device.sensor.gps.raw", message)
        assert result is not None

        table_name, record, upsert_key = result

        # Check conversions
        assert isinstance(record["latitude"], float)
        assert record["latitude"] == 37.7749
        assert isinstance(record["bearing"], float)
        assert record["bearing"] == 180.0

    def test_validate_config(self, engine):
        """Test config validation."""
        # Add validate_config method if it exists
        if hasattr(engine, "validate_config"):
            errors = engine.validate_config()
            assert isinstance(errors, list)
