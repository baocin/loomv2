"""Test data models."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.models import AudioChunk, BaseMessage, TranscribedText, TranscribedWord


class TestBaseMessage:
    """Test BaseMessage model."""

    def test_base_message_creation(self):
        """Test creating a base message."""
        msg = BaseMessage(device_id="test-device", recorded_at=datetime.utcnow())
        assert msg.device_id == "test-device"
        assert msg.schema_version == "1.0"
        assert msg.received_at is not None

    def test_base_message_validation(self):
        """Test base message validation."""
        with pytest.raises(ValidationError):
            BaseMessage(device_id="", recorded_at=datetime.utcnow())


class TestAudioChunk:
    """Test AudioChunk model."""

    def test_audio_chunk_creation(self):
        """Test creating an audio chunk."""
        chunk = AudioChunk(
            device_id="test-device",
            recorded_at=datetime.utcnow(),
            audio_data="base64encodeddata",
            duration_seconds=1.5,
            chunk_id="chunk-123",
            sequence_number=1,
        )
        assert chunk.sample_rate == 16000
        assert chunk.format == "wav"
        assert chunk.chunk_id == "chunk-123"

    def test_audio_chunk_custom_values(self):
        """Test audio chunk with custom values."""
        chunk = AudioChunk(
            device_id="test-device",
            recorded_at=datetime.utcnow(),
            audio_data="base64encodeddata",
            sample_rate=44100,
            format="mp3",
            duration_seconds=2.0,
            chunk_id="chunk-456",
            sequence_number=2,
        )
        assert chunk.sample_rate == 44100
        assert chunk.format == "mp3"


class TestTranscribedWord:
    """Test TranscribedWord model."""

    def test_transcribed_word_creation(self):
        """Test creating a transcribed word."""
        word = TranscribedWord(
            word="hello", start_time=0.0, end_time=0.5, confidence=0.95
        )
        assert word.word == "hello"
        assert word.start_time == 0.0
        assert word.end_time == 0.5
        assert word.confidence == 0.95

    def test_transcribed_word_validation(self):
        """Test transcribed word validation."""
        # Test confidence bounds
        with pytest.raises(ValidationError):
            TranscribedWord(
                word="test",
                start_time=0.0,
                end_time=0.5,
                confidence=1.5,  # > 1.0
            )

        with pytest.raises(ValidationError):
            TranscribedWord(
                word="test",
                start_time=0.0,
                end_time=0.5,
                confidence=-0.1,  # < 0.0
            )


class TestTranscribedText:
    """Test TranscribedText model."""

    def test_transcribed_text_creation(self):
        """Test creating transcribed text."""
        words = [
            TranscribedWord(
                word="hello", start_time=0.0, end_time=0.5, confidence=0.95
            ),
            TranscribedWord(
                word="world", start_time=0.6, end_time=1.0, confidence=0.90
            ),
        ]

        transcript = TranscribedText(
            device_id="test-device",
            recorded_at=datetime.utcnow(),
            chunk_id="chunk-123",
            words=words,
            full_text="hello world",
            processing_time_ms=150.5,
        )

        assert transcript.chunk_id == "chunk-123"
        assert len(transcript.words) == 2
        assert transcript.full_text == "hello world"
        assert transcript.language == "en"
        assert transcript.model_version == "nvidia/parakeet-tdt_ctc-1.1b"

    def test_transcribed_text_empty_words(self):
        """Test transcribed text with empty words list."""
        transcript = TranscribedText(
            device_id="test-device",
            recorded_at=datetime.utcnow(),
            chunk_id="chunk-123",
            words=[],
            full_text="",
            processing_time_ms=50.0,
        )
        assert len(transcript.words) == 0
        assert transcript.full_text == ""
