"""Unit tests for configuration."""


from app.config import Settings


class TestSettings:
    """Test Settings configuration."""

    def test_default_settings(self):
        """Test default settings values."""
        settings = Settings()
        assert settings.service_name == "silero-vad"
        assert settings.host == "0.0.0.0"
        assert settings.port == 8000
        assert settings.kafka_bootstrap_servers == "kafka:29092"
        assert settings.kafka_input_topic == "device.audio.raw"
        assert settings.kafka_output_topic == "media.audio.vad_filtered"
        assert settings.vad_threshold == 0.5
        assert settings.vad_sample_rate == 16000

    def test_env_override(self, monkeypatch):
        """Test environment variable override."""
        monkeypatch.setenv("LOOM_SERVICE_NAME", "custom-vad")
        monkeypatch.setenv("LOOM_PORT", "8080")
        monkeypatch.setenv("LOOM_VAD_THRESHOLD", "0.7")
        monkeypatch.setenv("LOOM_DEBUG", "true")

        settings = Settings()
        assert settings.service_name == "custom-vad"
        assert settings.port == 8080
        assert settings.vad_threshold == 0.7
        assert settings.debug is True

    def test_kafka_settings(self):
        """Test Kafka-specific settings."""
        settings = Settings()
        assert settings.kafka_consumer_group == "silero-vad-consumer"
        assert settings.kafka_auto_offset_reset == "latest"
        assert settings.kafka_enable_auto_commit is False
        assert settings.kafka_max_poll_records == 10

    def test_vad_settings(self):
        """Test VAD-specific settings."""
        settings = Settings()
        assert settings.vad_min_speech_duration_ms == 250.0
        assert settings.vad_min_silence_duration_ms == 100.0
        assert settings.vad_window_size_samples == 512
        assert settings.silero_model_name == "silero_vad"
        assert settings.silero_model_version == "v4.0"
        assert settings.silero_use_onnx is False
