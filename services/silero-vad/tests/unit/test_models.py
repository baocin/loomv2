"""Unit tests for data models."""

import base64
from datetime import datetime

import pytest

from app.models import AudioChunk, BaseMessage, VADFilteredAudio


class TestBaseMessage:
    """Test BaseMessage model."""

    def test_base_message_creation(self):
        """Test creating a base message."""
        msg = BaseMessage(
            device_id="test-device",
            recorded_at=datetime.utcnow(),
        )
        assert msg.device_id == "test-device"
        assert isinstance(msg.recorded_at, datetime)
        assert isinstance(msg.received_at, datetime)
        assert msg.metadata == {}

    def test_base_message_with_metadata(self):
        """Test base message with metadata."""
        metadata = {"key": "value", "count": 42}
        msg = BaseMessage(
            device_id="test-device",
            recorded_at=datetime.utcnow(),
            metadata=metadata,
        )
        assert msg.metadata == metadata


class TestAudioChunk:
    """Test AudioChunk model."""

    def test_audio_chunk_creation(self):
        """Test creating an audio chunk."""
        audio_data = base64.b64encode(b"test audio data").decode("utf-8")
        chunk = AudioChunk(
            device_id="test-device",
            recorded_at=datetime.utcnow(),
            audio_data=audio_data,
            sample_rate=16000,
            channels=1,
        )
        assert chunk.audio_data == audio_data
        assert chunk.sample_rate == 16000
        assert chunk.channels == 1
        assert chunk.format == "pcm"

    def test_audio_chunk_invalid_base64(self):
        """Test audio chunk with invalid base64."""
        with pytest.raises(ValueError, match="Invalid base64"):
            AudioChunk(
                device_id="test-device",
                recorded_at=datetime.utcnow(),
                audio_data="not-valid-base64!@#$",
                sample_rate=16000,
                channels=1,
            )

    def test_decode_audio(self):
        """Test decoding audio data."""
        original_data = b"test audio data"
        audio_data = base64.b64encode(original_data).decode("utf-8")
        chunk = AudioChunk(
            device_id="test-device",
            recorded_at=datetime.utcnow(),
            audio_data=audio_data,
            sample_rate=16000,
            channels=1,
        )
        decoded = chunk.decode_audio()
        assert decoded == original_data


class TestVADFilteredAudio:
    """Test VADFilteredAudio model."""

    def test_vad_filtered_audio_creation(self):
        """Test creating VAD filtered audio."""
        audio_data = base64.b64encode(b"speech data").decode("utf-8")
        filtered = VADFilteredAudio(
            device_id="test-device",
            recorded_at=datetime.utcnow(),
            audio_data=audio_data,
            sample_rate=16000,
            channels=1,
            duration_ms=1000.0,
            vad_confidence=0.95,
            speech_start_ms=100.0,
            speech_end_ms=900.0,
        )
        assert filtered.vad_confidence == 0.95
        assert filtered.speech_start_ms == 100.0
        assert filtered.speech_end_ms == 900.0
        assert filtered.duration_ms == 1000.0

    def test_encode_audio(self):
        """Test encoding audio data."""
        filtered = VADFilteredAudio(
            device_id="test-device",
            recorded_at=datetime.utcnow(),
            audio_data="",
            sample_rate=16000,
            channels=1,
            duration_ms=1000.0,
            vad_confidence=0.95,
            speech_start_ms=0.0,
            speech_end_ms=1000.0,
        )

        audio_bytes = b"speech audio data"
        filtered.encode_audio(audio_bytes)

        expected = base64.b64encode(audio_bytes).decode("utf-8")
        assert filtered.audio_data == expected
