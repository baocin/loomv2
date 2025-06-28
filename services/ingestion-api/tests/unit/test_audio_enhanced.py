"""Enhanced unit tests for audio ingestion endpoints."""

import base64
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.models import AudioChunk


@pytest.fixture()
def mock_kafka_producer():
    """Mock Kafka producer."""
    with patch("app.routers.audio.kafka_producer") as mock:
        mock.send_audio_chunk = AsyncMock()
        yield mock


@pytest.fixture()
def sample_audio_data():
    """Sample audio data for testing."""
    from ..test_helpers import create_audio_test_data

    # Add additional test-specific fields
    audio_data = create_audio_test_data()
    audio_data.update(
        {"channels": 2, "file_id": "audio_session_123"},  # Override default
    )
    return audio_data


class TestAudioUploadEnhanced:
    """Enhanced tests for audio upload endpoint."""

    def test_upload_audio_success(self, client, mock_kafka_producer, sample_audio_data):
        """Test successful audio upload."""
        response = client.post("/audio/upload", json=sample_audio_data)

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert data["topic"] == "device.audio.raw"
        assert "message_id" in data

    def test_upload_audio_different_formats(
        self,
        client,
        mock_kafka_producer,
        sample_audio_data,
    ):
        """Test audio upload with different formats."""
        formats = ["wav", "mp3", "aac", "flac"]

        for fmt in formats:
            sample_audio_data["format"] = fmt
            response = client.post("/audio/upload", json=sample_audio_data)
            assert response.status_code == 201

    def test_upload_audio_different_sample_rates(
        self,
        client,
        mock_kafka_producer,
        sample_audio_data,
    ):
        """Test audio upload with different sample rates."""
        sample_rates = [8000, 16000, 22050, 44100, 48000]

        for rate in sample_rates:
            sample_audio_data["sample_rate"] = rate
            response = client.post("/audio/upload", json=sample_audio_data)
            assert response.status_code == 201

    def test_upload_audio_mono_stereo(
        self,
        client,
        mock_kafka_producer,
        sample_audio_data,
    ):
        """Test audio upload with mono and stereo channels."""
        for channels in [1, 2]:
            sample_audio_data["channels"] = channels
            response = client.post("/audio/upload", json=sample_audio_data)
            assert response.status_code == 201

    def test_upload_audio_invalid_sample_rate(
        self,
        client,
        mock_kafka_producer,
        sample_audio_data,
    ):
        """Test audio upload with negative sample rate succeeds (no validation)."""
        sample_audio_data["sample_rate"] = -1
        response = client.post("/audio/upload", json=sample_audio_data)
        assert response.status_code == 201

    def test_upload_audio_invalid_channels(
        self,
        client,
        mock_kafka_producer,
        sample_audio_data,
    ):
        """Test audio upload with zero channels succeeds (no validation)."""
        sample_audio_data["channels"] = 0
        response = client.post("/audio/upload", json=sample_audio_data)
        assert response.status_code == 201

    def test_upload_audio_missing_chunk_data(
        self,
        client,
        mock_kafka_producer,
        sample_audio_data,
    ):
        """Test audio upload without chunk data fails."""
        del sample_audio_data["chunk_data"]
        response = client.post("/audio/upload", json=sample_audio_data)
        assert response.status_code == 422

    def test_upload_audio_large_chunk(self, client, mock_kafka_producer):
        """Test audio upload with large chunk."""
        # Create a larger audio chunk (simulate 10 seconds of audio)
        large_audio_bytes = b"x" * (
            44100 * 2 * 2 * 10
        )  # 44.1kHz, 2 channels, 2 bytes, 10 seconds
        encoded_audio = base64.b64encode(large_audio_bytes).decode("utf-8")

        audio_data = {
            "device_id": "12345678-1234-8234-1234-123456789012",
            "chunk_data": encoded_audio,
            "recorded_at": datetime.now(UTC).isoformat(),
            "sample_rate": 44100,
            "channels": 2,
            "format": "wav",
            "duration_ms": 10000,
        }

        response = client.post("/audio/upload", json=audio_data)
        assert response.status_code == 201

    def test_upload_audio_minimal_data(self, client, mock_kafka_producer):
        """Test audio upload with minimal required data."""
        from ..test_helpers import create_base_test_data

        test_audio_bytes = b"minimal_audio"
        encoded_audio = base64.b64encode(test_audio_bytes).decode("utf-8")

        minimal_audio = create_base_test_data()
        minimal_audio.update(
            {"chunk_data": encoded_audio, "sample_rate": 44100, "duration_ms": 100},
        )

        response = client.post("/audio/upload", json=minimal_audio)
        assert response.status_code == 201

    def test_upload_audio_with_file_id(
        self,
        client,
        mock_kafka_producer,
        sample_audio_data,
    ):
        """Test audio upload with file ID for chunking."""
        sample_audio_data["file_id"] = "session_recording_456"

        response = client.post("/audio/upload", json=sample_audio_data)
        assert response.status_code == 201

        # Verify file_id was included in the message
        call_args = mock_kafka_producer.send_audio_chunk.call_args
        audio_message = call_args[0][0]  # First positional argument
        assert audio_message.file_id == "session_recording_456"


class TestAudioDataModel:
    """Test AudioChunk model validation."""

    def test_audio_chunk_validation(self, sample_audio_data):
        """Test valid audio chunk model creation."""
        audio = AudioChunk(**sample_audio_data)
        assert audio.sample_rate == 44100
        assert audio.channels == 2
        assert audio.format == "wav"
        assert audio.duration_ms == 1000
        assert audio.file_id == "audio_session_123"

    def test_audio_chunk_defaults(self):
        """Test default values for optional fields."""
        test_audio_bytes = b"test_audio"
        encoded_audio = base64.b64encode(test_audio_bytes).decode("utf-8")

        audio_data = {
            "device_id": "12345678-1234-8234-1234-123456789012",
            "chunk_data": encoded_audio,
            "recorded_at": datetime.now(UTC),
            "sample_rate": 44100,
            "duration_ms": 100,
        }

        audio = AudioChunk(**audio_data)
        assert audio.channels == 1  # Default
        assert audio.format == "wav"  # Default
        assert audio.file_id is None

    def test_audio_chunk_bytes_field(self):
        """Test that chunk_data properly handles bytes."""
        test_audio_bytes = b"test_audio_data"
        encoded_audio = base64.b64encode(test_audio_bytes).decode("utf-8")

        audio_data = {
            "device_id": "12345678-1234-8234-1234-123456789012",
            "chunk_data": encoded_audio,
            "recorded_at": datetime.now(UTC),
            "sample_rate": 44100,
            "duration_ms": 100,
        }

        audio = AudioChunk(**audio_data)
        # The field should store as bytes
        assert isinstance(audio.chunk_data, (str, bytes))
