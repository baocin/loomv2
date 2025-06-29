"""Tests for configuration module."""

from app.config import Settings


def test_default_settings():
    """Test default settings values."""
    settings = Settings()

    assert settings.service_name == "gemma3n-processor"
    assert settings.host == "0.0.0.0"
    assert settings.port == 8000
    assert settings.log_level == "INFO"
    assert settings.environment == "development"

    # Kafka settings
    assert settings.kafka_bootstrap_servers == "kafka:29092"
    assert settings.kafka_consumer_group == "gemma3n-processor-consumer"
    assert settings.kafka_auto_offset_reset == "latest"
    assert settings.kafka_compression_type == "lz4"

    # Ollama settings
    assert settings.ollama_host == "http://localhost:11434"
    assert settings.ollama_model == "gemma3n:e4b"
    assert settings.ollama_timeout == 60
    assert settings.ollama_keep_alive == 300

    # Processing settings
    assert settings.max_image_size == 768
    assert settings.max_audio_duration == 30
    assert settings.batch_size == 1
    assert settings.processing_timeout == 120


def test_environment_override():
    """Test environment variable overrides."""
    settings = Settings(
        loom_service_name="custom-service",
        loom_port=9000,
        loom_log_level="DEBUG",
        loom_ollama_model="gemma3n:e2b",
    )

    assert settings.service_name == "custom-service"
    assert settings.port == 9000
    assert settings.log_level == "DEBUG"
    assert settings.ollama_model == "gemma3n:e2b"


def test_kafka_topics_configuration():
    """Test Kafka topics configuration."""
    settings = Settings()

    expected_input_topics = [
        "media.text.transcribed.words",
        "device.image.camera.raw",
        "device.video.screen.raw",
        "media.audio.vad_filtered",
    ]

    assert settings.kafka_input_topics == expected_input_topics
    assert settings.kafka_output_topic == "analysis.multimodal.gemma3n_results"


def test_model_parameters():
    """Test model parameter validation."""
    settings = Settings()

    assert settings.model_max_tokens == 4096
    assert settings.model_temperature == 0.7
    assert settings.model_top_p == 0.9
    assert settings.model_device is None  # Auto-detect


def test_health_check_settings():
    """Test health check configuration."""
    settings = Settings()

    assert settings.health_check_interval == 30
    assert settings.readiness_timeout == 10


def test_custom_kafka_settings():
    """Test custom Kafka configuration."""
    settings = Settings(
        loom_kafka_bootstrap_servers="localhost:9093",
        loom_kafka_consumer_group="test-group",
        loom_kafka_auto_offset_reset="earliest",
        loom_kafka_compression_type="gzip",
    )

    assert settings.kafka_bootstrap_servers == "localhost:9093"
    assert settings.kafka_consumer_group == "test-group"
    assert settings.kafka_auto_offset_reset == "earliest"
    assert settings.kafka_compression_type == "gzip"


def test_processing_limits():
    """Test processing limit configuration."""
    settings = Settings(
        loom_max_image_size=1024,
        loom_max_audio_duration=60,
        loom_processing_timeout=180,
    )

    assert settings.max_image_size == 1024
    assert settings.max_audio_duration == 60
    assert settings.processing_timeout == 180
