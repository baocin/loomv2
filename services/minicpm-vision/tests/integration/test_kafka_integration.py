"""Integration tests for Kafka message processing."""

import asyncio
import json
import base64
from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer

from app.kafka_consumer import KafkaImageConsumer
from app.models import ImageMessage, VisionAnalysisResult


@pytest.fixture
def mock_vision_processor():
    """Mock vision processor."""
    processor = Mock()
    processor.load_model = Mock(return_value=asyncio.Future())
    processor.load_model.return_value.set_result(None)
    
    async def mock_analyze(base64_image, device_id, recorded_at):
        return VisionAnalysisResult(
            device_id=device_id,
            recorded_at=recorded_at,
            scene_description="A test scene",
            scene_categories=["test"],
            detected_objects=[],
            ocr_results=[],
            processing_time_ms=100.0,
        )
    
    processor.analyze_image = mock_analyze
    return processor


@pytest.mark.asyncio
async def test_kafka_consumer_initialization():
    """Test Kafka consumer initialization."""
    consumer = KafkaImageConsumer(
        bootstrap_servers="localhost:9092",
        input_topics=["test.input"],
        output_topic="test.output",
        consumer_group="test-group",
    )
    
    assert consumer.bootstrap_servers == "localhost:9092"
    assert consumer.input_topics == ["test.input"]
    assert consumer.output_topic == "test.output"
    assert consumer.consumer_group == "test-group"
    assert not consumer.running


@pytest.mark.asyncio
async def test_process_message(mock_vision_processor):
    """Test processing a single message."""
    consumer = KafkaImageConsumer(
        bootstrap_servers="localhost:9092",
        input_topics=["test.input"],
        output_topic="test.output",
    )
    consumer.vision_processor = mock_vision_processor
    
    # Create test message
    test_message = {
        "device_id": "test-device",
        "recorded_at": datetime.utcnow().isoformat(),
        "schema_version": "v1",
        "data": base64.b64encode(b"fake image data").decode(),
    }
    
    # Process message
    result = await consumer.process_message(test_message)
    
    assert result is not None
    assert result.device_id == "test-device"
    assert result.scene_description == "A test scene"
    assert result.processing_time_ms == 100.0


@pytest.mark.asyncio
async def test_process_invalid_message(mock_vision_processor):
    """Test processing an invalid message."""
    consumer = KafkaImageConsumer(
        bootstrap_servers="localhost:9092",
        input_topics=["test.input"],
        output_topic="test.output",
    )
    consumer.vision_processor = mock_vision_processor
    
    # Invalid message (missing required fields)
    invalid_message = {
        "device_id": "test-device",
        # Missing recorded_at and data
    }
    
    result = await consumer.process_message(invalid_message)
    assert result is None  # Should return None on error


@pytest.mark.asyncio
@patch('app.kafka_consumer.AIOKafkaConsumer')
@patch('app.kafka_consumer.AIOKafkaProducer')
async def test_start_stop(mock_producer_class, mock_consumer_class, mock_vision_processor):
    """Test starting and stopping the consumer."""
    # Create mocks
    mock_consumer = Mock()
    mock_consumer.start = Mock(return_value=asyncio.Future())
    mock_consumer.start.return_value.set_result(None)
    mock_consumer.stop = Mock(return_value=asyncio.Future())
    mock_consumer.stop.return_value.set_result(None)
    
    mock_producer = Mock()
    mock_producer.start = Mock(return_value=asyncio.Future())
    mock_producer.start.return_value.set_result(None)
    mock_producer.stop = Mock(return_value=asyncio.Future())
    mock_producer.stop.return_value.set_result(None)
    
    mock_consumer_class.return_value = mock_consumer
    mock_producer_class.return_value = mock_producer
    
    # Create consumer
    consumer = KafkaImageConsumer(
        bootstrap_servers="localhost:9092",
        input_topics=["test.input"],
        output_topic="test.output",
    )
    consumer.vision_processor = mock_vision_processor
    
    # Start
    await consumer.start()
    assert consumer.running
    mock_consumer.start.assert_called_once()
    mock_producer.start.assert_called_once()
    
    # Stop
    await consumer.stop()
    assert not consumer.running
    mock_consumer.stop.assert_called_once()
    mock_producer.stop.assert_called_once()