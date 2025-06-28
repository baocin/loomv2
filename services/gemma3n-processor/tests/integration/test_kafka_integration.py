"""Integration tests for Kafka functionality."""

import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.kafka_consumer import KafkaConsumerManager
from app.models import TextMessage, ImageMessage, AudioMessage
from app.ollama_client import OllamaClient


@pytest.fixture
def mock_ollama_client():
    """Create mock Ollama client."""
    client = AsyncMock(spec=OllamaClient)
    client.generate_text.return_value = "Mock text analysis"
    client.analyze_image.return_value = "Mock image analysis"
    client.process_multimodal.return_value = "Mock multimodal analysis"
    return client


@pytest.fixture
def kafka_consumer_manager(mock_ollama_client):
    """Create KafkaConsumerManager with mock client."""
    return KafkaConsumerManager(mock_ollama_client)


class TestKafkaConsumerManager:
    """Test KafkaConsumerManager functionality."""

    def test_init(self, kafka_consumer_manager, mock_ollama_client):
        """Test KafkaConsumerManager initialization."""
        assert kafka_consumer_manager.ollama_client == mock_ollama_client
        assert kafka_consumer_manager.consumer is None
        assert kafka_consumer_manager.producer is None
        assert kafka_consumer_manager.running is False

    def test_is_healthy_not_started(self, kafka_consumer_manager):
        """Test health check when not started."""
        assert kafka_consumer_manager.is_healthy() is False

    @patch('app.kafka_consumer.AIOKafkaConsumer')
    @patch('app.kafka_consumer.AIOKafkaProducer')
    async def test_start_success(self, mock_producer_class, mock_consumer_class, kafka_consumer_manager):
        """Test successful start of Kafka consumer/producer."""
        # Mock consumer and producer
        mock_consumer = AsyncMock()
        mock_producer = AsyncMock()
        mock_consumer_class.return_value = mock_consumer
        mock_producer_class.return_value = mock_producer
        
        await kafka_consumer_manager.start()
        
        assert kafka_consumer_manager.running is True
        assert kafka_consumer_manager.consumer == mock_consumer
        assert kafka_consumer_manager.producer == mock_producer
        
        mock_consumer.start.assert_called_once()
        mock_producer.start.assert_called_once()

    @patch('app.kafka_consumer.AIOKafkaConsumer')
    @patch('app.kafka_consumer.AIOKafkaProducer')
    async def test_start_failure(self, mock_producer_class, mock_consumer_class, kafka_consumer_manager):
        """Test start failure handling."""
        mock_consumer_class.side_effect = Exception("Connection failed")
        
        with pytest.raises(Exception, match="Connection failed"):
            await kafka_consumer_manager.start()
        
        assert kafka_consumer_manager.running is False

    async def test_stop(self, kafka_consumer_manager):
        """Test stopping Kafka consumer/producer."""
        # Set up mock consumer and producer
        mock_consumer = AsyncMock()
        mock_producer = AsyncMock()
        kafka_consumer_manager.consumer = mock_consumer
        kafka_consumer_manager.producer = mock_producer
        kafka_consumer_manager.running = True
        
        await kafka_consumer_manager.stop()
        
        assert kafka_consumer_manager.running is False
        mock_consumer.stop.assert_called_once()
        mock_producer.stop.assert_called_once()

    async def test_process_text_message(self, kafka_consumer_manager, mock_ollama_client, sample_text_message):
        """Test processing text messages."""
        message_dict = sample_text_message.model_dump(mode="json")
        
        result = await kafka_consumer_manager.process_text_message(message_dict)
        
        assert result is not None
        assert result.analysis_type == "text_analysis"
        assert result.device_id == sample_text_message.device_id
        assert result.text_analysis is not None
        assert result.text_analysis.type == "text"
        
        mock_ollama_client.generate_text.assert_called_once()

    async def test_process_image_message(self, kafka_consumer_manager, mock_ollama_client, sample_image_message):
        """Test processing image messages."""
        message_dict = sample_image_message.model_dump(mode="json")
        
        result = await kafka_consumer_manager.process_image_message(message_dict)
        
        assert result is not None
        assert result.analysis_type == "image_analysis"
        assert result.device_id == sample_image_message.device_id
        assert result.image_analysis is not None
        assert result.image_analysis.type == "image"
        
        mock_ollama_client.analyze_image.assert_called_once()

    async def test_process_audio_message(self, kafka_consumer_manager, mock_ollama_client, sample_audio_message):
        """Test processing audio messages."""
        message_dict = sample_audio_message.model_dump(mode="json")
        
        result = await kafka_consumer_manager.process_audio_message(message_dict)
        
        assert result is not None
        assert result.analysis_type == "audio_analysis"
        assert result.device_id == sample_audio_message.device_id
        assert result.audio_analysis is not None
        assert result.audio_analysis.type == "audio"
        
        mock_ollama_client.generate_text.assert_called_once()

    async def test_process_multimodal_message_text_topic(self, kafka_consumer_manager, sample_text_message):
        """Test routing text topic to text processor."""
        message_dict = sample_text_message.model_dump(mode="json")
        
        result = await kafka_consumer_manager.process_multimodal_message(
            message_dict, 
            "media.text.transcribed.words"
        )
        
        assert result is not None
        assert result.analysis_type == "text_analysis"

    async def test_process_multimodal_message_image_topic(self, kafka_consumer_manager, sample_image_message):
        """Test routing image topic to image processor."""
        message_dict = sample_image_message.model_dump(mode="json")
        
        result = await kafka_consumer_manager.process_multimodal_message(
            message_dict,
            "device.image.camera.raw"
        )
        
        assert result is not None
        assert result.analysis_type == "image_analysis"

    async def test_process_multimodal_message_audio_topic(self, kafka_consumer_manager, sample_audio_message):
        """Test routing audio topic to audio processor."""
        message_dict = sample_audio_message.model_dump(mode="json")
        
        result = await kafka_consumer_manager.process_multimodal_message(
            message_dict,
            "media.audio.vad_filtered"
        )
        
        assert result is not None
        assert result.analysis_type == "audio_analysis"

    async def test_process_multimodal_message_unknown_topic(self, kafka_consumer_manager, sample_text_message):
        """Test handling unknown topic."""
        message_dict = sample_text_message.model_dump(mode="json")
        
        result = await kafka_consumer_manager.process_multimodal_message(
            message_dict,
            "unknown.topic.name"
        )
        
        assert result is None

    async def test_process_message_invalid_data(self, kafka_consumer_manager):
        """Test handling invalid message data."""
        invalid_message = {"invalid": "data"}
        
        result = await kafka_consumer_manager.process_text_message(invalid_message)
        
        assert result is None

    async def test_process_message_ollama_error(self, kafka_consumer_manager, mock_ollama_client, sample_text_message):
        """Test handling Ollama client errors."""
        mock_ollama_client.generate_text.side_effect = Exception("Ollama error")
        message_dict = sample_text_message.model_dump(mode="json")
        
        result = await kafka_consumer_manager.process_text_message(message_dict)
        
        assert result is None


class TestKafkaMessageProcessing:
    """Test end-to-end message processing scenarios."""

    @patch('app.kafka_consumer.AIOKafkaConsumer')
    @patch('app.kafka_consumer.AIOKafkaProducer')
    async def test_consume_messages_success(self, mock_producer_class, mock_consumer_class, kafka_consumer_manager, sample_text_message):
        """Test successful message consumption and processing."""
        # Set up mocks
        mock_consumer = AsyncMock()
        mock_producer = AsyncMock()
        mock_consumer_class.return_value = mock_consumer
        mock_producer_class.return_value = mock_producer
        
        # Create mock message
        mock_message = Mock()
        mock_message.topic = "media.text.transcribed.words"
        mock_message.partition = 0
        mock_message.offset = 123
        mock_message.value = sample_text_message.model_dump(mode="json")
        
        # Set up async iteration
        mock_messages = [mock_message]
        
        async def mock_iter():
            for msg in mock_messages:
                yield msg
                kafka_consumer_manager.running = False  # Stop after one message
        
        mock_consumer.__aiter__ = mock_iter
        
        # Start consumer manager
        await kafka_consumer_manager.start()
        
        # Run consumption loop
        await kafka_consumer_manager.consume_messages()
        
        # Verify message was processed and sent
        mock_producer.send_and_wait.assert_called_once()
        mock_consumer.commit.assert_called_once()

    @patch('app.kafka_consumer.AIOKafkaConsumer')
    @patch('app.kafka_consumer.AIOKafkaProducer')
    async def test_consume_messages_processing_failure(self, mock_producer_class, mock_consumer_class, kafka_consumer_manager):
        """Test handling of message processing failures."""
        # Set up mocks
        mock_consumer = AsyncMock()
        mock_producer = AsyncMock()
        mock_consumer_class.return_value = mock_consumer
        mock_producer_class.return_value = mock_producer
        
        # Create mock message with invalid data
        mock_message = Mock()
        mock_message.topic = "media.text.transcribed.words"
        mock_message.partition = 0
        mock_message.offset = 123
        mock_message.value = {"invalid": "data"}
        
        # Set up async iteration
        async def mock_iter():
            yield mock_message
            kafka_consumer_manager.running = False
        
        mock_consumer.__aiter__ = mock_iter
        
        # Start consumer manager
        await kafka_consumer_manager.start()
        
        # Run consumption loop
        await kafka_consumer_manager.consume_messages()
        
        # Verify message was not sent and offset not committed
        mock_producer.send_and_wait.assert_not_called()
        mock_consumer.commit.assert_not_called()