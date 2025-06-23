"""Unit tests for VAD processor."""

import pytest
import numpy as np
from unittest.mock import Mock, patch, AsyncMock
import asyncio

from app.vad_processor import VADProcessor


@pytest.mark.asyncio
class TestVADProcessor:
    """Test VAD processor functionality."""
    
    async def test_initialization(self):
        """Test VAD processor initialization."""
        processor = VADProcessor()
        assert processor.model is None
        assert processor._initialized is False
        
        # Mock torch.hub.load to avoid downloading model in tests
        with patch("torch.hub.load") as mock_load:
            mock_model = Mock()
            mock_utils = [Mock(), Mock(), Mock(), Mock(), Mock()]
            mock_load.return_value = (mock_model, mock_utils)
            
            await processor.initialize()
            
            assert processor._initialized is True
            assert processor.model is mock_model
            mock_load.assert_called_once()
    
    async def test_process_audio_not_initialized(self):
        """Test processing audio when not initialized."""
        processor = VADProcessor()
        
        # Mock the initialization
        processor.initialize = AsyncMock()
        processor._process_audio_sync = Mock(return_value=[])
        
        audio_data = b"\x00\x00" * 1000  # Silent audio
        await processor.process_audio(audio_data, 16000, 1)
        
        processor.initialize.assert_called_once()
    
    def test_process_audio_sync_mono(self):
        """Test synchronous audio processing with mono audio."""
        processor = VADProcessor()
        
        # Mock the model and utilities
        processor.model = Mock()
        processor.get_speech_timestamps = Mock(return_value=[
            {"start": 160, "end": 480, "confidence": 0.95}
        ])
        
        # Create test audio data (mono, 16-bit PCM)
        audio_data = np.random.randint(-32768, 32767, size=1600, dtype=np.int16).tobytes()
        
        with patch("torchaudio.transforms.Resample"):
            segments = processor._process_audio_sync(audio_data, 16000, 1)
        
        assert len(segments) == 1
        assert segments[0]["start_ms"] == 10.0  # 160 / 16000 * 1000
        assert segments[0]["end_ms"] == 30.0    # 480 / 16000 * 1000
        assert segments[0]["duration_ms"] == 20.0
        assert segments[0]["confidence"] == 0.95
        assert segments[0]["sample_rate"] == 16000
    
    def test_process_audio_sync_stereo(self):
        """Test synchronous audio processing with stereo audio."""
        processor = VADProcessor()
        
        # Mock the model and utilities
        processor.model = Mock()
        processor.get_speech_timestamps = Mock(return_value=[])
        
        # Create test audio data (stereo, 16-bit PCM)
        audio_data = np.random.randint(-32768, 32767, size=3200, dtype=np.int16).tobytes()
        
        with patch("torchaudio.transforms.Resample"):
            segments = processor._process_audio_sync(audio_data, 16000, 2)
        
        # Should convert to mono by averaging channels
        assert len(segments) == 0  # No speech detected in mock
    
    def test_process_audio_sync_resample(self):
        """Test audio resampling when sample rate differs."""
        processor = VADProcessor()
        
        # Mock the model and utilities
        processor.model = Mock()
        processor.get_speech_timestamps = Mock(return_value=[])
        
        # Create test audio data at 48kHz
        audio_data = np.random.randint(-32768, 32767, size=4800, dtype=np.int16).tobytes()
        
        with patch("torchaudio.transforms.Resample") as mock_resample:
            mock_resampler = Mock()
            mock_resample.return_value = mock_resampler
            mock_resampler.return_value = Mock()
            
            segments = processor._process_audio_sync(audio_data, 48000, 1)
            
            # Should create resampler for 48kHz to 16kHz
            mock_resample.assert_called_once_with(orig_freq=48000, new_freq=16000)
    
    async def test_cleanup(self):
        """Test cleanup of resources."""
        processor = VADProcessor()
        processor._initialized = True
        
        await processor.cleanup()
        
        assert processor._initialized is False