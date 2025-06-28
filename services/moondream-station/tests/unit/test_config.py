"""Tests for configuration module."""

import pytest

from app.config import Settings


def test_default_settings():
    """Test default settings values."""
    settings = Settings()
    
    assert settings.service_name == "moondream-station"
    assert settings.host == "0.0.0.0"
    assert settings.port == 8000
    assert settings.log_level == "INFO"
    assert settings.environment == "development"
    
    # Kafka settings
    assert settings.kafka_bootstrap_servers == "kafka:29092"
    assert settings.kafka_consumer_group == "moondream-station-consumer"
    assert settings.kafka_auto_offset_reset == "latest"
    assert settings.kafka_compression_type == "lz4"
    
    # Moondream settings
    assert settings.moondream_host == "http://localhost:2020"
    assert settings.moondream_api_path == "/v1"
    assert settings.moondream_timeout == 30
    assert settings.moondream_max_retries == 3
    
    # Processing settings
    assert settings.max_image_size == 2048
    assert settings.jpeg_quality == 95
    assert settings.batch_size == 1
    assert settings.processing_timeout == 60


def test_environment_override():
    """Test environment variable overrides."""
    settings = Settings(
        loom_service_name="custom-moondream",
        loom_port=9000,
        loom_log_level="DEBUG",
        loom_moondream_host="http://moondream:3030"
    )
    
    assert settings.service_name == "custom-moondream"
    assert settings.port == 9000
    assert settings.log_level == "DEBUG"
    assert settings.moondream_host == "http://moondream:3030"


def test_kafka_topics_configuration():
    """Test Kafka topics configuration."""
    settings = Settings()
    
    expected_input_topics = [
        "device.image.camera.raw",
        "device.video.screen.raw",
        "task.image.analyze",
    ]
    
    assert settings.kafka_input_topics == expected_input_topics
    assert settings.kafka_output_topic == "media.image.analysis.moondream_results"


def test_model_configuration():
    """Test model configuration settings."""
    settings = Settings()
    
    assert settings.default_caption_prompt == "Describe this image in detail."
    assert settings.enable_object_detection is True
    assert settings.enable_ocr is True
    assert settings.confidence_threshold == 0.7


def test_health_check_settings():
    """Test health check configuration."""
    settings = Settings()
    
    assert settings.health_check_interval == 30
    assert settings.readiness_timeout == 5


def test_storage_configuration():
    """Test storage configuration."""
    settings = Settings()
    
    assert settings.temp_storage_path == "/app/data/temp"
    assert settings.max_temp_storage_mb == 1000


def test_custom_kafka_settings():
    """Test custom Kafka configuration."""
    settings = Settings(
        loom_kafka_bootstrap_servers="localhost:9093",
        loom_kafka_consumer_group="test-moondream-group",
        loom_kafka_auto_offset_reset="earliest",
        loom_kafka_compression_type="gzip"
    )
    
    assert settings.kafka_bootstrap_servers == "localhost:9093"
    assert settings.kafka_consumer_group == "test-moondream-group"
    assert settings.kafka_auto_offset_reset == "earliest"
    assert settings.kafka_compression_type == "gzip"


def test_processing_limits():
    """Test processing limit configuration."""
    settings = Settings(
        loom_max_image_size=4096,
        loom_jpeg_quality=80,
        loom_processing_timeout=120,
        loom_confidence_threshold=0.8
    )
    
    assert settings.max_image_size == 4096
    assert settings.jpeg_quality == 80
    assert settings.processing_timeout == 120
    assert settings.confidence_threshold == 0.8