"""Unit tests for Kafka integration functionality."""

from unittest.mock import MagicMock, patch

import pytest

from app.main import kafka_consumer_thread
from tests.test_helpers import (
    create_test_twitter_image_message,
    create_kafka_message_with_base64_prefix,
)


@pytest.fixture
def mock_kafka_consumer():
    """Mock Kafka consumer."""
    mock = MagicMock()
    mock.__iter__ = MagicMock()
    return mock


@pytest.fixture
def mock_kafka_producer():
    """Mock Kafka producer."""
    return MagicMock()


@pytest.fixture
def mock_ocr_processor():
    """Mock OCR processor for Kafka tests."""
    mock = MagicMock()
    mock.process_image.return_value = {
        "ocr_text": "Extracted tweet text",
        "description": "Screenshot of a tweet",
        "success": True,
    }
    return mock


class TestKafkaIntegration:
    """Test Kafka message processing functionality."""

    @patch("app.main.KafkaProducer")
    @patch("app.main.KafkaConsumer")
    @patch("app.main.os.getenv")
    def test_kafka_consumer_configuration(
        self, mock_getenv, mock_consumer_class, mock_producer_class
    ):
        """Test Kafka consumer is configured correctly."""
        mock_getenv.return_value = "kafka1:9092,kafka2:9092"
        mock_consumer_class.return_value.__iter__.return_value = []

        with patch("app.main.ocr_processor") as mock_processor:
            mock_processor.process_image.return_value = {
                "success": True,
                "ocr_text": "",
                "description": "",
            }

            # This will exit quickly since we mocked empty iterator
            kafka_consumer_thread()

            # Verify consumer was created with correct config
            mock_consumer_class.assert_called_once()
            call_args = mock_consumer_class.call_args

            assert "external.twitter.images.raw" in call_args[0]  # Topic
            assert call_args[1]["bootstrap_servers"] == ["kafka1:9092", "kafka2:9092"]
            assert call_args[1]["group_id"] == "moondream-ocr-consumer"
            assert call_args[1]["auto_offset_reset"] == "latest"

    @patch("app.main.KafkaProducer")
    @patch("app.main.KafkaConsumer")
    @patch("app.main.os.getenv")
    def test_kafka_producer_configuration(
        self, mock_getenv, mock_consumer_class, mock_producer_class
    ):
        """Test Kafka producer is configured correctly."""
        mock_getenv.return_value = "kafka:9092"
        mock_consumer_class.return_value.__iter__.return_value = []

        with patch("app.main.ocr_processor") as mock_processor:
            mock_processor.process_image.return_value = {
                "success": True,
                "ocr_text": "",
                "description": "",
            }

            kafka_consumer_thread()

            # Verify producer was created with correct config
            mock_producer_class.assert_called_once()
            call_args = mock_producer_class.call_args

            assert call_args[1]["bootstrap_servers"] == ["kafka:9092"]

    @patch("app.main.KafkaProducer")
    @patch("app.main.KafkaConsumer")
    @patch("app.main.logging")
    def test_kafka_consumer_no_processor(
        self, mock_logging, mock_consumer_class, mock_producer_class
    ):
        """Test Kafka consumer handles missing OCR processor."""
        with patch("app.main.ocr_processor", None):
            kafka_consumer_thread()

            mock_logging.error.assert_called_with(
                "OCR processor not initialized for Kafka consumer"
            )
            mock_consumer_class.assert_not_called()
            mock_producer_class.assert_not_called()

    @patch("app.main.KafkaProducer")
    @patch("app.main.KafkaConsumer")
    @patch("app.main.time.time")
    def test_message_processing_success(
        self, mock_time, mock_consumer_class, mock_producer_class
    ):
        """Test successful message processing."""
        # Mock time for processing duration
        mock_time.side_effect = [1000.0, 1000.5]  # 500ms processing time

        # Create test message
        test_message = create_test_twitter_image_message()
        mock_kafka_message = MagicMock()
        mock_kafka_message.value = test_message

        # Mock consumer to return one message then stop
        mock_consumer = MagicMock()
        mock_consumer.__iter__.return_value = [mock_kafka_message]
        mock_consumer_class.return_value = mock_consumer

        # Mock producer
        mock_producer = MagicMock()
        mock_producer_class.return_value = mock_producer

        with patch("app.main.ocr_processor") as mock_processor:
            mock_processor.process_image.return_value = {
                "ocr_text": "Tweet text content",
                "description": "Twitter screenshot",
                "success": True,
            }

            # This will process one message then exit
            kafka_consumer_thread()

            # Verify OCR processor was called
            mock_processor.process_image.assert_called_once_with(
                test_message["data"]["image_data"]
            )

            # Verify producer sent message
            mock_producer.send.assert_called_once()
            sent_args = mock_producer.send.call_args

            assert sent_args[0][0] == "media.image.analysis.moondream_results"  # Topic
            sent_message = sent_args[1]["value"]

            # Verify output message structure
            assert sent_message["schema_version"] == "v1"
            assert sent_message["tweet_id"] == "1234567890"
            assert sent_message["ocr_results"]["full_text"] == "Tweet text content"
            assert sent_message["ocr_results"]["success"] is True
            assert sent_message["model_version"] == "moondream2"
            assert sent_message["processing_time_ms"] == 500.0

    @patch("app.main.KafkaProducer")
    @patch("app.main.KafkaConsumer")
    def test_message_processing_with_base64_prefix(
        self, mock_consumer_class, mock_producer_class
    ):
        """Test processing message with data:image/png;base64 prefix."""
        test_message = create_kafka_message_with_base64_prefix()
        mock_kafka_message = MagicMock()
        mock_kafka_message.value = test_message

        mock_consumer = MagicMock()
        mock_consumer.__iter__.return_value = [mock_kafka_message]
        mock_consumer_class.return_value = mock_consumer

        mock_producer = MagicMock()
        mock_producer_class.return_value = mock_producer

        with patch("app.main.ocr_processor") as mock_processor:
            mock_processor.process_image.return_value = {
                "ocr_text": "Text from image",
                "description": "Description",
                "success": True,
            }

            kafka_consumer_thread()

            # Verify OCR processor received the full image data (with prefix)
            mock_processor.process_image.assert_called_once()
            call_args = mock_processor.process_image.call_args[0][0]
            assert call_args.startswith("data:image/png;base64,")

    @patch("app.main.KafkaProducer")
    @patch("app.main.KafkaConsumer")
    @patch("app.main.logging")
    def test_message_processing_no_image_data(
        self, mock_logging, mock_consumer_class, mock_producer_class
    ):
        """Test handling message without image data."""
        test_message = {"data": {}, "trace_id": "test-trace"}  # No image_data field
        mock_kafka_message = MagicMock()
        mock_kafka_message.value = test_message

        mock_consumer = MagicMock()
        mock_consumer.__iter__.return_value = [mock_kafka_message]
        mock_consumer_class.return_value = mock_consumer

        mock_producer = MagicMock()
        mock_producer_class.return_value = mock_producer

        with patch("app.main.ocr_processor") as mock_processor:
            kafka_consumer_thread()

            # Should log warning and not process
            mock_logging.warning.assert_called_with("No image data in message")
            mock_processor.process_image.assert_not_called()
            mock_producer.send.assert_not_called()

    @patch("app.main.KafkaProducer")
    @patch("app.main.KafkaConsumer")
    @patch("app.main.logging")
    def test_message_processing_ocr_error(
        self, mock_logging, mock_consumer_class, mock_producer_class
    ):
        """Test handling OCR processing errors."""
        test_message = create_test_twitter_image_message()
        mock_kafka_message = MagicMock()
        mock_kafka_message.value = test_message

        mock_consumer = MagicMock()
        mock_consumer.__iter__.return_value = [mock_kafka_message]
        mock_consumer_class.return_value = mock_consumer

        mock_producer = MagicMock()
        mock_producer_class.return_value = mock_producer

        with patch("app.main.ocr_processor") as mock_processor:
            mock_processor.process_image.return_value = {
                "ocr_text": "",
                "description": "",
                "success": False,
                "error": "Model failed",
            }

            kafka_consumer_thread()

            # Should still send message but with error info
            mock_producer.send.assert_called_once()
            sent_message = mock_producer.send.call_args[1]["value"]
            assert sent_message["ocr_results"]["success"] is False
            assert sent_message["ocr_results"]["error"] == "Model failed"

    @patch("app.main.KafkaProducer")
    @patch("app.main.KafkaConsumer")
    @patch("app.main.logging")
    def test_message_processing_exception(
        self, mock_logging, mock_consumer_class, mock_producer_class
    ):
        """Test handling general processing exceptions."""
        test_message = create_test_twitter_image_message()
        mock_kafka_message = MagicMock()
        mock_kafka_message.value = test_message

        mock_consumer = MagicMock()
        mock_consumer.__iter__.return_value = [mock_kafka_message]
        mock_consumer_class.return_value = mock_consumer

        mock_producer = MagicMock()
        mock_producer_class.return_value = mock_producer

        with patch("app.main.ocr_processor") as mock_processor:
            mock_processor.process_image.side_effect = Exception("Unexpected error")

            kafka_consumer_thread()

            # Should log error and continue processing
            mock_logging.error.assert_called()
            error_call = mock_logging.error.call_args[0][0]
            assert "Error processing Kafka message" in error_call
