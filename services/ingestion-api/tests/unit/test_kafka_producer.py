"""Unit tests for Kafka producer service."""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiokafka.errors import KafkaError

from app.config import Settings
from app.kafka_producer import KafkaProducerService
from app.models import AudioChunk, GPSReading, SensorReading


@pytest.fixture()
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


@pytest.fixture()
def mock_producer():
    """Mock aiokafka producer fixture."""
    with patch("app.kafka_producer.AIOKafkaProducer") as mock:
        producer_instance = AsyncMock()
        mock.return_value = producer_instance
        yield producer_instance


@pytest.fixture()
def kafka_service():
    """Kafka producer service fixture."""
    return KafkaProducerService()


class TestKafkaProducerInitialization:
    """Test Kafka producer initialization."""

    def test_init_without_settings(self):
        """Test initialization without settings parameter."""
        service = KafkaProducerService()

        assert service._producer is None
        assert service.is_connected is False


class TestKafkaProducerConnection:
    """Test Kafka producer connection management."""

    @pytest.mark.asyncio()
    async def test_start_success(self, kafka_service, mock_producer):
        """Test successful producer startup."""
        mock_producer.start = AsyncMock()

        with patch("app.kafka_producer.AIOKafkaProducer", return_value=mock_producer):
            await kafka_service.start()

        mock_producer.start.assert_called_once()
        assert kafka_service._producer == mock_producer
        assert kafka_service.is_connected is True

    @pytest.mark.asyncio()
    async def test_start_failure(self, kafka_service, mock_producer):
        """Test producer startup failure."""
        mock_producer.start = AsyncMock(side_effect=KafkaError("Connection failed"))

        with patch("app.kafka_producer.AIOKafkaProducer", return_value=mock_producer):
            with pytest.raises(KafkaError, match="Connection failed"):
                await kafka_service.start()

        assert kafka_service.is_connected is False

    @pytest.mark.asyncio()
    async def test_stop_success(self, kafka_service, mock_producer):
        """Test successful producer shutdown."""
        mock_producer.stop = AsyncMock()
        kafka_service._producer = mock_producer
        kafka_service._is_connected = True

        await kafka_service.stop()

        mock_producer.stop.assert_called_once()
        assert kafka_service.is_connected is False

    @pytest.mark.asyncio()
    async def test_stop_when_not_connected(self, kafka_service):
        """Test stop when not connected."""
        kafka_service._producer = None
        kafka_service._is_connected = False

        # Should not raise error
        await kafka_service.stop()

        assert kafka_service._producer is None
        assert kafka_service.is_connected is False

    @pytest.mark.asyncio()
    async def test_stop_with_error(self, kafka_service, mock_producer):
        """Test stop with error."""
        mock_producer.stop = AsyncMock(side_effect=Exception("Stop failed"))
        kafka_service._producer = mock_producer
        kafka_service._is_connected = True

        # Should handle error gracefully
        await kafka_service.stop()

        assert kafka_service.is_connected is False


class TestKafkaMessageSending:
    """Test message sending functionality."""

    @pytest.mark.asyncio()
    async def test_send_audio_chunk_success(self, kafka_service, mock_producer):
        """Test successful audio chunk sending."""
        kafka_service._producer = mock_producer
        kafka_service._is_connected = True
        mock_producer.send = AsyncMock()

        audio_chunk = AudioChunk(
            device_id="12345678-1234-8234-1234-123456789012",
            recorded_at=datetime.now(UTC),
            chunk_data=b"test audio",
            sample_rate=44100,
            duration_ms=1000,
        )

        with patch("app.kafka_producer.settings") as mock_settings:
            mock_settings.topic_device_audio_raw = "device.audio.raw"
            await kafka_service.send_audio_chunk(audio_chunk)

        mock_producer.send.assert_called_once()
        call_args = mock_producer.send.call_args
        assert call_args[1]["topic"] == "device.audio.raw"
        assert call_args[1]["value"] == audio_chunk
        assert call_args[1]["key"] == "12345678-1234-8234-1234-123456789012"

    @pytest.mark.asyncio()
    async def test_send_sensor_data_success(self, kafka_service, mock_producer):
        """Test successful sensor data sending."""
        kafka_service._producer = mock_producer
        kafka_service._is_connected = True
        mock_producer.send = AsyncMock()

        gps_reading = GPSReading(
            device_id="12345678-1234-8234-1234-123456789012",
            recorded_at=datetime.now(UTC),
            latitude=37.7749,
            longitude=-122.4194,
        )

        with patch("app.kafka_producer.settings") as mock_settings:
            mock_settings.topic_device_sensor_raw = "device.sensor.{sensor_type}.raw"
            await kafka_service.send_sensor_data(gps_reading, "gps")

        mock_producer.send.assert_called_once()
        call_args = mock_producer.send.call_args
        assert call_args[1]["topic"] == "device.sensor.gps.raw"
        assert call_args[1]["value"] == gps_reading
        assert call_args[1]["key"] == "12345678-1234-8234-1234-123456789012"

    @pytest.mark.asyncio()
    async def test_send_when_not_connected(self, kafka_service):
        """Test sending when not connected."""
        kafka_service._is_connected = False

        audio_chunk = AudioChunk(
            device_id="12345678-1234-8234-1234-123456789012",
            recorded_at=datetime.now(UTC),
            chunk_data=b"test",
            sample_rate=44100,
            duration_ms=1000,
        )

        with pytest.raises(RuntimeError, match="Kafka producer not connected"):
            await kafka_service.send_audio_chunk(audio_chunk)

    @pytest.mark.asyncio()
    async def test_send_with_kafka_error(self, kafka_service, mock_producer):
        """Test sending with Kafka error."""
        kafka_service._producer = mock_producer
        kafka_service._is_connected = True
        mock_producer.send = AsyncMock(side_effect=KafkaError("Send failed"))

        audio_chunk = AudioChunk(
            device_id="12345678-1234-8234-1234-123456789012",
            recorded_at=datetime.now(UTC),
            chunk_data=b"test",
            sample_rate=44100,
            duration_ms=1000,
        )

        with patch("app.kafka_producer.settings") as mock_settings:
            mock_settings.topic_device_audio_raw = "device.audio.raw"
            with pytest.raises(KafkaError, match="Send failed"):
                await kafka_service.send_audio_chunk(audio_chunk)


class TestMessageSerialization:
    """Test message serialization functionality."""

    def test_serialize_audio_chunk(self, kafka_service):
        """Test audio chunk serialization."""
        audio_chunk = AudioChunk(
            device_id="12345678-1234-8234-1234-123456789012",
            recorded_at=datetime.now(UTC),
            chunk_data=b"test audio data",
            sample_rate=44100,
            channels=2,
            format="wav",
            duration_ms=1000,
        )

        serialized = kafka_service._serialize_message(audio_chunk)
        parsed = json.loads(serialized)

        assert parsed["device_id"] == "12345678-1234-8234-1234-123456789012"
        assert parsed["sample_rate"] == 44100
        assert parsed["channels"] == 2
        assert parsed["format"] == "wav"
        assert parsed["duration_ms"] == 1000
        assert "chunk_data" in parsed  # String serialized
        assert "timestamp" in parsed

    def test_serialize_sensor_reading(self, kafka_service):
        """Test sensor reading serialization."""
        sensor_reading = SensorReading(
            device_id="12345678-1234-8234-1234-123456789012",
            recorded_at=datetime.now(UTC),
            sensor_type="temperature",
            value={"temp": 23.5},
            unit="celsius",
        )

        serialized = kafka_service._serialize_message(sensor_reading)
        parsed = json.loads(serialized)

        assert parsed["device_id"] == "12345678-1234-8234-1234-123456789012"
        assert parsed["sensor_type"] == "temperature"
        assert parsed["value"]["temp"] == 23.5
        assert parsed["unit"] == "celsius"
        assert "timestamp" in parsed

    def test_serialize_datetime_handling(self, kafka_service):
        """Test datetime serialization."""
        audio_chunk = AudioChunk(
            device_id="12345678-1234-8234-1234-123456789012",
            recorded_at=datetime.now(UTC),
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
            device_id="12345678-1234-8234-1234-123456789012",
            recorded_at=datetime.now(UTC),
            chunk_data=b"binary data",
            sample_rate=44100,
            duration_ms=1000,
        )

        serialized = kafka_service._serialize_message(audio_chunk)
        parsed = json.loads(serialized)

        # Should serialize bytes as string (Pydantic JSON mode behavior)
        chunk_data = parsed["chunk_data"]
        assert isinstance(chunk_data, str)
        assert chunk_data == "binary data"


# Topic generation is now handled through settings, not instance methods


class TestErrorHandling:
    """Test error handling and logging."""

    @pytest.mark.asyncio()
    async def test_connection_error_logging(self, kafka_service):
        """Test connection error logging."""
        with patch("app.kafka_producer.logger") as mock_logger:
            with patch("app.kafka_producer.AIOKafkaProducer") as mock_producer_cls:
                mock_producer = AsyncMock()
                mock_producer.start = AsyncMock(
                    side_effect=KafkaError("Connection failed"),
                )
                mock_producer_cls.return_value = mock_producer

                with pytest.raises(KafkaError):
                    await kafka_service.start()

                mock_logger.error.assert_called()

    @pytest.mark.asyncio()
    async def test_send_error_logging(self, kafka_service, mock_producer):
        """Test send error logging."""
        kafka_service._producer = mock_producer
        kafka_service._is_connected = True
        mock_producer.send = AsyncMock(side_effect=KafkaError("Send failed"))

        audio_chunk = AudioChunk(
            device_id="12345678-1234-8234-1234-123456789012",
            recorded_at=datetime.now(UTC),
            chunk_data=b"test",
            sample_rate=44100,
            duration_ms=1000,
        )

        with patch("app.kafka_producer.logger") as mock_logger:
            with patch("app.kafka_producer.settings") as mock_settings:
                mock_settings.topic_device_audio_raw = "device.audio.raw"
                with pytest.raises(KafkaError):
                    await kafka_service.send_audio_chunk(audio_chunk)

                mock_logger.error.assert_called()


# Producer configuration is now handled through the start() method
