"""Unit tests for configuration."""


from app.config import Settings


class TestSettings:
    """Test Settings configuration."""

    def test_default_settings(self):
        """Test default settings values."""
        settings = Settings()
        assert settings.service_name == "minicpm-vision"
        assert settings.host == "0.0.0.0"
        assert settings.port == 8000
        assert settings.kafka_bootstrap_servers == "kafka:29092"
        assert settings.kafka_output_topic == "media.image.analysis.minicpm_results"
        assert settings.model_name == "openbmb/MiniCPM-Llama3-V-2_5"

    def test_env_override(self, monkeypatch):
        """Test environment variable overrides."""
        monkeypatch.setenv("LOOM_SERVICE_NAME", "test-service")
        monkeypatch.setenv("LOOM_PORT", "9000")
        monkeypatch.setenv("LOOM_KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        monkeypatch.setenv("LOOM_MODEL_DEVICE", "cuda")

        settings = Settings()
        assert settings.service_name == "test-service"
        assert settings.port == 9000
        assert settings.kafka_bootstrap_servers == "localhost:9092"
        assert settings.model_device == "cuda"

    def test_kafka_input_topics(self):
        """Test Kafka input topics configuration."""
        settings = Settings()
        assert "device.image.camera.raw" in settings.kafka_input_topics
        assert "device.video.screen.raw" in settings.kafka_input_topics
        assert len(settings.kafka_input_topics) == 2

    def test_model_configuration(self):
        """Test model configuration settings."""
        settings = Settings()
        assert settings.model_device is None  # Auto-detect by default
        assert settings.model_max_tokens == 1024
        assert settings.model_temperature == 0.7
        assert settings.max_image_size == 1920
