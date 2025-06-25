"""Tests for VAD processor."""

import base64
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.models import AudioChunk, VADResult
from app.processor import VADProcessor


@pytest.fixture
def sample_audio_chunk():
    """Create a sample audio chunk."""
    # Generate a simple sine wave as test audio
    import numpy as np

    sample_rate = 16000
    duration = 1.0  # 1 second
    frequency = 440  # A4 note

    t = np.linspace(0, duration, int(sample_rate * duration))
    audio = (np.sin(2 * np.pi * frequency * t) * 32767).astype(np.int16)
    audio_bytes = audio.tobytes()

    return AudioChunk(
        device_id="test-device-001",
        timestamp=datetime.utcnow(),
        chunk_number=1,
        audio_data=base64.b64encode(audio_bytes).decode("utf-8"),
        format="pcm16",
        sample_rate=sample_rate,
        channels=1,
        duration_ms=int(duration * 1000),
        metadata={"test": True},
    )


@pytest.mark.asyncio
async def test_vad_processor_initialization():
    """Test VAD processor initialization."""
    processor = VADProcessor()
    assert processor.consumer is None
    assert processor.producer is None
    assert processor.db_pool is None
    assert processor.vad_model is None
    assert processor._running is False


@pytest.mark.asyncio
async def test_process_audio_chunk(sample_audio_chunk):
    """Test processing an audio chunk."""
    processor = VADProcessor()

    # Mock the VAD model
    with patch("app.processor.SileroVAD") as mock_vad_class:
        mock_vad = MagicMock()
        mock_vad.process_audio.return_value = [
            (
                MagicMock(start_ms=100, end_ms=900, confidence=0.95),
                b"fake_audio_segment",
            )
        ]
        mock_vad_class.return_value = mock_vad

        processor.vad_model = mock_vad

        # Process the chunk
        results = await processor._process_audio_chunk(sample_audio_chunk)

        assert len(results) == 1
        result = results[0]
        assert isinstance(result, VADResult)
        assert result.device_id == sample_audio_chunk.device_id
        assert result.has_speech is True
        assert result.confidence == 0.95
        assert result.segment_start_ms == 100
        assert result.segment_duration_ms == 800
