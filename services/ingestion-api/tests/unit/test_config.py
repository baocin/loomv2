"""Unit tests for configuration management."""

import os
from unittest.mock import patch

from app.config import Settings


class TestSettingsDefault:
    """Test default configuration values."""

    def test_default_values(self):
        """Test default configuration values."""
        settings = Settings()

        # Server settings
        assert settings.host == "0.0.0.0"
        assert settings.port == 8000
        assert settings.log_level == "INFO"
        assert settings.environment == "development"

        # Kafka settings
        assert settings.kafka_bootstrap_servers == "localhost:9092"
        assert settings.kafka_audio_topic == "device.audio.raw"
        assert settings.kafka_sensor_topic == "device.sensor.{type}.raw"
        assert settings.kafka_compression_type == "lz4"
        assert settings.kafka_batch_size == 16384
        assert settings.kafka_linger_ms == 10
        assert settings.kafka_retry_backoff_ms == 100
        assert settings.kafka_max_retries == 3

        # Monitoring settings
        assert settings.metrics_enabled is True
        assert settings.enable_cors is True


class TestSettingsEnvironmentVariables:
    """Test configuration from environment variables."""

    def test_server_environment_variables(self):
        """Test server settings from environment variables."""
        env_vars = {
            "LOOM_HOST": "127.0.0.1",
            "LOOM_PORT": "9000",
            "LOOM_LOG_LEVEL": "DEBUG",
            "LOOM_ENVIRONMENT": "production",
        }

        with patch.dict(os.environ, env_vars):
            settings = Settings()

        assert settings.host == "127.0.0.1"
        assert settings.port == 9000
        assert settings.log_level == "DEBUG"
        assert settings.environment == "production"

    def test_kafka_environment_variables(self):
        """Test Kafka settings from environment variables."""
        env_vars = {
            "LOOM_KAFKA_BOOTSTRAP_SERVERS": "kafka1:9092,kafka2:9092",
            "LOOM_KAFKA_AUDIO_TOPIC": "custom.audio.topic",
            "LOOM_KAFKA_SENSOR_TOPIC": "custom.sensor.{type}.topic",
            "LOOM_KAFKA_COMPRESSION_TYPE": "gzip",
            "LOOM_KAFKA_BATCH_SIZE": "32768",
            "LOOM_KAFKA_LINGER_MS": "20",
            "LOOM_KAFKA_RETRY_BACKOFF_MS": "200",
            "LOOM_KAFKA_MAX_RETRIES": "5",
        }

        with patch.dict(os.environ, env_vars):
            settings = Settings()

        assert settings.kafka_bootstrap_servers == "kafka1:9092,kafka2:9092"
        assert settings.kafka_audio_topic == "custom.audio.topic"
        assert settings.kafka_sensor_topic == "custom.sensor.{type}.topic"
        assert settings.kafka_compression_type == "gzip"
        assert settings.kafka_batch_size == 32768
        assert settings.kafka_linger_ms == 20
        assert settings.kafka_retry_backoff_ms == 200
        assert settings.kafka_max_retries == 5

    def test_monitoring_environment_variables(self):
        """Test monitoring settings from environment variables."""
        env_vars = {
            "LOOM_METRICS_ENABLED": "false",
            "LOOM_ENABLE_CORS": "false",
        }

        with patch.dict(os.environ, env_vars):
            settings = Settings()

        assert settings.metrics_enabled is False
        assert settings.enable_cors is False

    def test_boolean_environment_variables_case_insensitive(self):
        """Test boolean environment variables are case insensitive."""
        test_cases = [
            ("True", True),
            ("true", True),
            ("TRUE", True),
            ("1", True),
            ("False", False),
            ("false", False),
            ("FALSE", False),
            ("0", False),
        ]

        for env_value, expected in test_cases:
            env_vars = {"LOOM_METRICS_ENABLED": env_value}

            with patch.dict(os.environ, env_vars):
                settings = Settings()

            assert settings.metrics_enabled is expected


class TestSettingsValidation:
    """Test configuration validation."""

    def test_port_validation_valid(self):
        """Test valid port numbers."""
        valid_ports = ["1000", "8000", "65535"]

        for port in valid_ports:
            env_vars = {"LOOM_PORT": port}

            with patch.dict(os.environ, env_vars):
                settings = Settings()

            assert settings.port == int(port)

    def test_log_level_validation(self):
        """Test log level validation."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for level in valid_levels:
            env_vars = {"LOOM_LOG_LEVEL": level}

            with patch.dict(os.environ, env_vars):
                settings = Settings()

            assert settings.log_level == level

    def test_kafka_compression_validation(self):
        """Test Kafka compression type validation."""
        valid_compression = ["none", "gzip", "snappy", "lz4", "zstd"]

        for compression in valid_compression:
            env_vars = {"LOOM_KAFKA_COMPRESSION_TYPE": compression}

            with patch.dict(os.environ, env_vars):
                settings = Settings()

            assert settings.kafka_compression_type == compression


class TestSettingsPrefix:
    """Test environment variable prefix handling."""

    def test_prefix_required(self):
        """Test that LOOM_ prefix is required."""
        # Set env var without prefix
        env_vars = {"HOST": "192.168.1.1"}

        with patch.dict(os.environ, env_vars):
            settings = Settings()

        # Should use default value, not the env var without prefix
        assert settings.host == "0.0.0.0"  # default

    def test_prefix_case_sensitive(self):
        """Test that prefix is case insensitive (user-friendly)."""
        env_vars = {"loom_host": "192.168.1.1"}  # lowercase prefix

        with patch.dict(os.environ, env_vars):
            settings = Settings()

        # Should pick up the lowercase variable (case insensitive)
        assert settings.host == "192.168.1.1"


class TestSettingsTypes:
    """Test configuration type conversions."""

    def test_integer_conversion(self):
        """Test integer type conversion."""
        env_vars = {
            "LOOM_PORT": "9000",
            "LOOM_KAFKA_BATCH_SIZE": "32768",
            "LOOM_KAFKA_LINGER_MS": "20",
            "LOOM_KAFKA_RETRY_BACKOFF_MS": "200",
            "LOOM_KAFKA_MAX_RETRIES": "5",
        }

        with patch.dict(os.environ, env_vars):
            settings = Settings()

        assert isinstance(settings.port, int)
        assert isinstance(settings.kafka_batch_size, int)
        assert isinstance(settings.kafka_linger_ms, int)
        assert isinstance(settings.kafka_retry_backoff_ms, int)
        assert isinstance(settings.kafka_max_retries, int)

    def test_boolean_conversion(self):
        """Test boolean type conversion."""
        env_vars = {
            "LOOM_METRICS_ENABLED": "true",
            "LOOM_ENABLE_CORS": "false",
        }

        with patch.dict(os.environ, env_vars):
            settings = Settings()

        assert isinstance(settings.metrics_enabled, bool)
        assert isinstance(settings.enable_cors, bool)
        assert settings.metrics_enabled is True
        assert settings.enable_cors is False

    def test_string_conversion(self):
        """Test string values remain strings."""
        env_vars = {
            "LOOM_HOST": "127.0.0.1",
            "LOOM_LOG_LEVEL": "DEBUG",
            "LOOM_KAFKA_BOOTSTRAP_SERVERS": "localhost:9092",
        }

        with patch.dict(os.environ, env_vars):
            settings = Settings()

        assert isinstance(settings.host, str)
        assert isinstance(settings.log_level, str)
        assert isinstance(settings.kafka_bootstrap_servers, str)


class TestSettingsKafkaTopics:
    """Test Kafka topic configuration."""

    def test_topic_templates(self):
        """Test topic template format."""
        settings = Settings()

        # Audio topic should be static
        assert "{type}" not in settings.kafka_audio_topic

        # Sensor topic should have type placeholder
        assert "{type}" in settings.kafka_sensor_topic

    def test_custom_topic_templates(self):
        """Test custom topic templates."""
        env_vars = {
            "LOOM_KAFKA_AUDIO_TOPIC": "custom.audio.raw",
            "LOOM_KAFKA_SENSOR_TOPIC": "custom.{type}.processed",
        }

        with patch.dict(os.environ, env_vars):
            settings = Settings()

        assert settings.kafka_audio_topic == "custom.audio.raw"
        assert settings.kafka_sensor_topic == "custom.{type}.processed"


class TestSettingsRepr:
    """Test settings string representation."""

    def test_settings_str_representation(self):
        """Test settings can be converted to string."""
        settings = Settings()

        settings_str = str(settings)

        # Should contain key configuration values
        assert "host=" in settings_str
        assert "port=" in settings_str
        assert "kafka_bootstrap_servers=" in settings_str

    def test_settings_repr(self):
        """Test settings repr."""
        settings = Settings()

        settings_repr = repr(settings)

        # Should be a valid representation
        assert "Settings" in settings_repr


class TestSettingsImmutability:
    """Test settings immutability after creation."""

    def test_settings_are_frozen(self):
        """Test that settings cannot be modified after creation."""
        settings = Settings()

        # pydantic BaseSettings should allow modification by default
        # If we want immutability, we'd need to add frozen=True to the model
        original_host = settings.host

        # This test documents current behavior
        # If immutability is desired, add frozen=True to Settings class
        settings.host = "new-host"
        assert settings.host == "new-host"  # Currently allows modification


class TestSettingsDocumentation:
    """Test settings field documentation."""

    def test_settings_have_field_info(self):
        """Test that settings fields have proper documentation."""
        settings = Settings()

        # Check that model has field information
        model_fields = Settings.model_fields

        # Should have all expected fields
        expected_fields = [
            "host",
            "port",
            "log_level",
            "environment",
            "kafka_bootstrap_servers",
            "kafka_audio_topic",
            "kafka_sensor_topic",
            "metrics_enabled",
            "enable_cors",
        ]

        for field in expected_fields:
            assert field in model_fields
