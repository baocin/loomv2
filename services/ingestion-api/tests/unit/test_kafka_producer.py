"""Unit tests for Kafka producer service."""

import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

import pytest
from aiokafka.errors import KafkaError

from app.kafka_producer import KafkaProducerService
from app.config import Settings
from app.models import AudioChunk, GPSReading, SensorReading


@pytest.fixture
def mock_settings():
    """Mock settings fixture."""
    settings = MagicMock(spec=Settings)
    settings.kafka_bootstrap_servers = "localhost:9092"
    settings.kafka_audio_topic = "device.audio.raw"
    settings.kafka_sensor_topic = "device.sensor.{type}.raw"
    settings.kafka_compression_type = "lz4"
    settings.kafka_batch_size = 16384
    settings.kafka_linger_ms = 10
    settings.kafka_retry_backoff_ms = 100
    settings.kafka_max_retries = 3
    return settings


@pytest.fixture
def mock_producer():
    """Mock aiokafka producer fixture."""
    with patch('app.kafka_producer.AIOKafkaProducer') as mock:
        producer_instance = AsyncMock()
        mock.return_value = producer_instance
        yield producer_instance


@pytest.fixture
def kafka_service(mock_settings):
    """Kafka producer service fixture."""
    return KafkaProducerService(mock_settings)


class TestKafkaProducerInitialization:
    """Test Kafka producer initialization."""
    
    def test_init_with_settings(self, mock_settings):
        """Test initialization with settings."""
        service = KafkaProducerService(mock_settings)
        
        assert service.settings == mock_settings
        assert service.producer is None
        assert service.is_connected is False
    
    def test_init_creates_producer_config(self, mock_settings):
        """Test producer configuration creation."""
        service = KafkaProducerService(mock_settings)
        
        # Verify settings are stored
        assert service.settings.kafka_bootstrap_servers == "localhost:9092"
        assert service.settings.kafka_compression_type == "lz4"
        assert service.settings.kafka_batch_size == 16384


class TestKafkaProducerConnection:
    """Test Kafka producer connection management."""
    
    @pytest.mark.asyncio
    async def test_start_success(self, kafka_service, mock_producer):
        """Test successful producer startup."""
        mock_producer.start = AsyncMock()
        
        with patch('app.kafka_producer.AIOKafkaProducer', return_value=mock_producer):
            await kafka_service.start()
        
        mock_producer.start.assert_called_once()
        assert kafka_service.producer == mock_producer
        assert kafka_service.is_connected is True
    
    @pytest.mark.asyncio
    async def test_start_failure(self, kafka_service, mock_producer):
        """Test producer startup failure."""
        mock_producer.start = AsyncMock(side_effect=KafkaError("Connection failed"))
        
        with patch('app.kafka_producer.AIOKafkaProducer', return_value=mock_producer):
            with pytest.raises(KafkaError, match="Connection failed"):
                await kafka_service.start()
        
        assert kafka_service.is_connected is False
    
    @pytest.mark.asyncio
    async def test_stop_success(self, kafka_service, mock_producer):
        """Test successful producer shutdown."""
        mock_producer.stop = AsyncMock()
        kafka_service.producer = mock_producer
        kafka_service.is_connected = True
        
        await kafka_service.stop()
        
        mock_producer.stop.assert_called_once()
        assert kafka_service.producer is None
        assert kafka_service.is_connected is False
    
    @pytest.mark.asyncio
    async def test_stop_when_not_connected(self, kafka_service):
        """Test stop when not connected."""
        kafka_service.producer = None
        kafka_service.is_connected = False
        
        # Should not raise error
        await kafka_service.stop()
        
        assert kafka_service.producer is None
        assert kafka_service.is_connected is False
    
    @pytest.mark.asyncio
    async def test_stop_with_error(self, kafka_service, mock_producer):
        """Test stop with error."""
        mock_producer.stop = AsyncMock(side_effect=Exception("Stop failed"))
        kafka_service.producer = mock_producer
        kafka_service.is_connected = True
        
        # Should handle error gracefully
        await kafka_service.stop()
        
        assert kafka_service.producer is None
        assert kafka_service.is_connected is False


class TestKafkaMessageSending:
    """Test message sending functionality."""
    
    @pytest.mark.asyncio
    async def test_send_audio_chunk_success(self, kafka_service, mock_producer):
        """Test successful audio chunk sending."""
        kafka_service.producer = mock_producer
        kafka_service.is_connected = True
        mock_producer.send = AsyncMock()
        
        audio_chunk = AudioChunk(
            device_id="test-device",
            chunk_data=b"test audio",
            sample_rate=44100,
            duration_ms=1000,
        )
        
        await kafka_service.send_audio_chunk(audio_chunk)
        
        mock_producer.send.assert_called_once()
        call_args = mock_producer.send.call_args
        assert call_args[0][0] == "device.audio.raw"  # topic
        
        # Verify message content
        message_value = call_args[1]["value"]
        parsed_message = json.loads(message_value)
        assert parsed_message["device_id"] == "test-device"
        assert parsed_message["sample_rate"] == 44100
    
    @pytest.mark.asyncio
    async def test_send_sensor_reading_success(self, kafka_service, mock_producer):
        """Test successful sensor reading sending."""
        kafka_service.producer = mock_producer
        kafka_service.is_connected = True
        mock_producer.send = AsyncMock()
        
        gps_reading = GPSReading(
            device_id="test-device",
            latitude=37.7749,
            longitude=-122.4194,
        )
        
        await kafka_service.send_sensor_reading(gps_reading, "gps")
        
        mock_producer.send.assert_called_once()
        call_args = mock_producer.send.call_args
        assert call_args[0][0] == "device.sensor.gps.raw"  # topic with type
        
        # Verify message content
        message_value = call_args[1]["value"]
        parsed_message = json.loads(message_value)
        assert parsed_message["device_id"] == "test-device"
        assert parsed_message["latitude"] == 37.7749
    
    @pytest.mark.asyncio
    async def test_send_when_not_connected(self, kafka_service):
        """Test sending when not connected."""
        kafka_service.is_connected = False
        
        audio_chunk = AudioChunk(
            device_id="test-device",
            chunk_data=b"test",
            sample_rate=44100,
            duration_ms=1000,
        )
        
        with pytest.raises(RuntimeError, match="Producer not connected"):
            await kafka_service.send_audio_chunk(audio_chunk)
    
    @pytest.mark.asyncio
    async def test_send_with_kafka_error(self, kafka_service, mock_producer):
        """Test sending with Kafka error."""
        kafka_service.producer = mock_producer
        kafka_service.is_connected = True
        mock_producer.send = AsyncMock(side_effect=KafkaError("Send failed"))
        
        audio_chunk = AudioChunk(
            device_id="test-device",
            chunk_data=b"test",
            sample_rate=44100,
            duration_ms=1000,
        )
        
        with pytest.raises(KafkaError, match="Send failed"):
            await kafka_service.send_audio_chunk(audio_chunk)


class TestMessageSerialization:
    """Test message serialization functionality."""
    
    def test_serialize_audio_chunk(self, kafka_service):
        """Test audio chunk serialization."""
        audio_chunk = AudioChunk(
            device_id="test-device",
            chunk_data=b"test audio data",
            sample_rate=44100,
            channels=2,
            format="wav",
            duration_ms=1000,
        )
        
        serialized = kafka_service._serialize_message(audio_chunk)
        parsed = json.loads(serialized)
        
        assert parsed["device_id"] == "test-device"
        assert parsed["sample_rate"] == 44100
        assert parsed["channels"] == 2
        assert parsed["format"] == "wav"
        assert parsed["duration_ms"] == 1000
        assert "chunk_data" in parsed  # Base64 encoded
        assert "timestamp" in parsed
        assert "message_id" in parsed
    
    def test_serialize_sensor_reading(self, kafka_service):
        """Test sensor reading serialization."""
        sensor_reading = SensorReading(
            device_id="test-device",
            sensor_type="temperature",
            value={"temp": 23.5},
            unit="celsius",
        )
        
        serialized = kafka_service._serialize_message(sensor_reading)
        parsed = json.loads(serialized)
        
        assert parsed["device_id"] == "test-device"
        assert parsed["sensor_type"] == "temperature"
        assert parsed["value"]["temp"] == 23.5
        assert parsed["unit"] == "celsius"
        assert "timestamp" in parsed
    
    def test_serialize_datetime_handling(self, kafka_service):
        """Test datetime serialization."""
        audio_chunk = AudioChunk(
            device_id="test-device",
            chunk_data=b"test",
            sample_rate=44100,
            duration_ms=1000,
        )
        
        serialized = kafka_service._serialize_message(audio_chunk)
        parsed = json.loads(serialized)
        
        # Should serialize datetime as ISO string
        timestamp = parsed["timestamp"]
        assert isinstance(timestamp, str)
        assert "T" in timestamp  # ISO format
    
    def test_serialize_bytes_handling(self, kafka_service):
        """Test bytes serialization."""
        audio_chunk = AudioChunk(
            device_id="test-device",
            chunk_data=b"binary data",
            sample_rate=44100,
            duration_ms=1000,
        )
        
        serialized = kafka_service._serialize_message(audio_chunk)
        parsed = json.loads(serialized)
        
        # Should serialize bytes as base64
        chunk_data = parsed["chunk_data"]
        assert isinstance(chunk_data, str)
        
        # Verify it's valid base64
        import base64
        decoded = base64.b64decode(chunk_data)
        assert decoded == b"binary data"


class TestTopicNameGeneration:
    """Test topic name generation."""
    
    def test_get_audio_topic(self, kafka_service):
        """Test audio topic name generation."""
        topic = kafka_service._get_audio_topic()
        assert topic == "device.audio.raw"
    
    def test_get_sensor_topic(self, kafka_service):
        """Test sensor topic name generation."""
        topic = kafka_service._get_sensor_topic("gps")
        assert topic == "device.sensor.gps.raw"
        
        topic = kafka_service._get_sensor_topic("accelerometer")
        assert topic == "device.sensor.accelerometer.raw"
    
    def test_get_sensor_topic_special_chars(self, kafka_service):
        """Test sensor topic with special characters."""
        # Topic names should handle special characters
        topic = kafka_service._get_sensor_topic("heart-rate")
        assert topic == "device.sensor.heart-rate.raw"


class TestErrorHandling:
    """Test error handling and logging."""
    
    @pytest.mark.asyncio
    async def test_connection_error_logging(self, kafka_service):
        """Test connection error logging."""
        with patch('app.kafka_producer.logger') as mock_logger:
            with patch('app.kafka_producer.AIOKafkaProducer') as mock_producer_cls:
                mock_producer = AsyncMock()
                mock_producer.start = AsyncMock(side_effect=KafkaError("Connection failed"))
                mock_producer_cls.return_value = mock_producer
                
                with pytest.raises(KafkaError):
                    await kafka_service.start()
                
                mock_logger.error.assert_called()
    
    @pytest.mark.asyncio
    async def test_send_error_logging(self, kafka_service, mock_producer):
        """Test send error logging."""
        kafka_service.producer = mock_producer
        kafka_service.is_connected = True
        mock_producer.send = AsyncMock(side_effect=KafkaError("Send failed"))
        
        audio_chunk = AudioChunk(
            device_id="test-device",
            chunk_data=b"test",
            sample_rate=44100,
            duration_ms=1000,
        )
        
        with patch('app.kafka_producer.logger') as mock_logger:
            with pytest.raises(KafkaError):
                await kafka_service.send_audio_chunk(audio_chunk)
            
            mock_logger.error.assert_called()


class TestKafkaProducerConfiguration:
    """Test Kafka producer configuration."""
    
    def test_producer_configuration_values(self, kafka_service, mock_settings):
        """Test producer is configured with correct values."""
        with patch('app.kafka_producer.AIOKafkaProducer') as mock_producer_cls:
            kafka_service._create_producer()
            
            # Verify producer was created with correct configuration
            mock_producer_cls.assert_called_once()
            call_kwargs = mock_producer_cls.call_args[1]
            
            assert call_kwargs["bootstrap_servers"] == "localhost:9092"
            assert call_kwargs["compression_type"] == "lz4"
            assert call_kwargs["batch_size"] == 16384
            assert call_kwargs["linger_ms"] == 10
            assert call_kwargs["retry_backoff_ms"] == 100
            assert call_kwargs["max_retries"] == 3 