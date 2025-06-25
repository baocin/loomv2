"""Test configuration."""

import os

from app.config import Settings


class TestSettings:
    """Test Settings configuration."""

    def test_default_settings(self):
        """Test default settings values."""
        settings = Settings()
        assert settings.service_name == "parakeet-tdt"
        assert settings.environment == "development"
        assert settings.host == "0.0.0.0"
        assert settings.port == 8000
        assert settings.kafka_input_topic == "media.audio.vad_filtered"
        assert settings.kafka_output_topic == "media.text.transcribed.words"
        assert settings.model_name == "nvidia/parakeet-tdt_ctc-1.1b"
        assert settings.target_sample_rate == 16000

    def test_env_override(self, monkeypatch):
        """Test environment variable override."""
        monkeypatch.setenv("LOOM_SERVICE_NAME", "test-service")
        monkeypatch.setenv("LOOM_PORT", "9000")
        monkeypatch.setenv("LOOM_KAFKA_BOOTSTRAP_SERVERS", "kafka-test:9092")

        settings = Settings()
        assert settings.service_name == "test-service"
        assert settings.port == 9000
        assert settings.kafka_bootstrap_servers == "kafka-test:9092"

    def test_model_device_detection(self, monkeypatch):
        """Test model device detection based on CUDA availability."""
        # Test with CUDA available
        monkeypatch.setattr(os.path, "exists", lambda path: path == "/usr/local/cuda")
        settings = Settings()
        assert settings.model_device == "cuda"

        # Test without CUDA
        monkeypatch.setattr(os.path, "exists", lambda path: False)
        settings = Settings()
        assert settings.model_device == "cpu"

    def test_kafka_settings(self):
        """Test Kafka-specific settings."""
        settings = Settings()
        assert settings.kafka_consumer_group == "parakeet-tdt-consumer"
        assert settings.kafka_max_poll_records == 10
        assert settings.kafka_session_timeout_ms == 30000
        assert settings.kafka_heartbeat_interval_ms == 10000
