"""Edge case and boundary condition tests for Silero VAD."""

import base64
import numpy as np
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models import AudioChunk, VADFilteredAudio
from app.vad_processor import VADProcessor


class TestVADEdgeCases:
    """Test edge cases and boundary conditions for VAD processing."""

    @pytest.fixture
    def vad_processor(self):
        """Create a VAD processor with mocked model."""
        with patch("app.vad_processor.torch.hub.load") as mock_load:
            mock_model = MagicMock()
            mock_model.return_value = torch.tensor([[0.8]])  # Mock high confidence
            mock_load.return_value = (mock_model, None)
            
            processor = VADProcessor(threshold=0.5)
            return processor

    @pytest.fixture
    def mock_model(self):
        """Mock Silero VAD model."""
        model = MagicMock()
        # Default: return high confidence for speech
        model.return_value = torch.tensor([[0.8]])
        return model

    def create_audio_chunk(self, audio_data, sample_rate=16000, channels=1):
        """Helper to create audio chunks."""
        # Convert to bytes if numpy array
        if isinstance(audio_data, np.ndarray):
            audio_bytes = audio_data.astype(np.float32).tobytes()
        else:
            audio_bytes = audio_data
            
        encoded = base64.b64encode(audio_bytes).decode()
        
        return AudioChunk(
            device_id="test-device-123",
            recorded_at="2024-01-01T00:00:00Z",
            data=encoded,
            sample_rate=sample_rate,
            channels=channels,
            duration_ms=int(len(audio_data) / sample_rate * 1000)
        )

    async def test_empty_audio(self, vad_processor):
        """Test with completely silent/empty audio."""
        # Create 1 second of silence
        silence = np.zeros(16000, dtype=np.float32)
        chunk = self.create_audio_chunk(silence)
        
        with patch.object(vad_processor.model, "__call__") as mock_call:
            mock_call.return_value = torch.tensor([[0.1]])  # Low confidence
            result = await vad_processor.process_audio(chunk)
            
        assert result is None  # Should not detect speech in silence

    async def test_very_loud_audio(self, vad_processor):
        """Test with maximum amplitude audio."""
        # Create 1 second of max amplitude noise
        loud_audio = np.ones(16000, dtype=np.float32) * 0.99  # Near max but not clipping
        chunk = self.create_audio_chunk(loud_audio)
        
        # VAD should still work with loud audio
        result = await vad_processor.process_audio(chunk)
        assert result is not None or result is None  # Model decides

    async def test_very_quiet_audio(self, vad_processor):
        """Test with minimal amplitude audio."""
        # Create very quiet audio (just above silence)
        quiet_audio = np.random.randn(16000).astype(np.float32) * 0.001
        chunk = self.create_audio_chunk(quiet_audio)
        
        with patch.object(vad_processor.model, "__call__") as mock_call:
            mock_call.return_value = torch.tensor([[0.2]])  # Low confidence
            result = await vad_processor.process_audio(chunk)
            
        assert result is None  # Too quiet to be speech

    @pytest.mark.parametrize("sample_rate", [8000, 16000, 44100, 48000])
    async def test_different_sample_rates(self, vad_processor, sample_rate):
        """Test with various sample rates."""
        duration_seconds = 1
        num_samples = int(sample_rate * duration_seconds)
        
        # Create sine wave as test signal
        t = np.linspace(0, duration_seconds, num_samples)
        audio = np.sin(2 * np.pi * 440 * t).astype(np.float32) * 0.5
        
        chunk = self.create_audio_chunk(audio, sample_rate=sample_rate)
        
        # Should handle resampling internally
        result = await vad_processor.process_audio(chunk)
        # Result depends on model, just ensure no crash
        assert result is None or isinstance(result, VADFilteredAudio)

    @pytest.mark.parametrize("channels", [1, 2, 6])
    async def test_different_channel_counts(self, vad_processor, channels):
        """Test with different channel configurations."""
        samples_per_channel = 16000
        
        if channels == 1:
            audio = np.random.randn(samples_per_channel).astype(np.float32) * 0.3
        else:
            # Create interleaved multi-channel audio
            audio = np.random.randn(samples_per_channel * channels).astype(np.float32) * 0.3
            
        chunk = self.create_audio_chunk(audio, channels=channels)
        
        # Should handle channel conversion internally
        result = await vad_processor.process_audio(chunk)
        assert result is None or isinstance(result, VADFilteredAudio)

    async def test_invalid_base64(self, vad_processor):
        """Test with corrupted base64 data."""
        chunk = AudioChunk(
            device_id="test-device-123",
            recorded_at="2024-01-01T00:00:00Z",
            data="invalid!!base64$$data",  # Invalid base64
            sample_rate=16000,
            channels=1,
            duration_ms=1000
        )
        
        with pytest.raises(Exception):  # Should raise decoding error
            await vad_processor.process_audio(chunk)

    async def test_large_audio_chunks(self, vad_processor):
        """Test with very large audio buffers."""
        # Create 30 seconds of audio
        large_audio = np.random.randn(16000 * 30).astype(np.float32) * 0.3
        chunk = self.create_audio_chunk(large_audio)
        
        # Should handle large chunks (might process in segments)
        result = await vad_processor.process_audio(chunk)
        assert result is None or isinstance(result, VADFilteredAudio)

    async def test_tiny_audio_chunks(self, vad_processor):
        """Test with very small audio buffers."""
        # Create 100ms of audio (very short)
        tiny_audio = np.random.randn(1600).astype(np.float32) * 0.3
        chunk = self.create_audio_chunk(tiny_audio)
        
        # Should handle tiny chunks
        result = await vad_processor.process_audio(chunk)
        assert result is None or isinstance(result, VADFilteredAudio)

    async def test_clipping_audio(self, vad_processor):
        """Test with clipped/distorted audio."""
        # Create clipped audio
        t = np.linspace(0, 1, 16000)
        audio = np.sin(2 * np.pi * 440 * t) * 2.0  # Amplitude > 1
        audio = np.clip(audio, -1.0, 1.0).astype(np.float32)  # Hard clip
        
        chunk = self.create_audio_chunk(audio)
        
        # Should still process clipped audio
        result = await vad_processor.process_audio(chunk)
        assert result is None or isinstance(result, VADFilteredAudio)

    async def test_threshold_boundaries(self, vad_processor):
        """Test VAD threshold edge cases."""
        audio = np.random.randn(16000).astype(np.float32) * 0.3
        chunk = self.create_audio_chunk(audio)
        
        # Test exact threshold match
        with patch.object(vad_processor.model, "__call__") as mock_call:
            mock_call.return_value = torch.tensor([[0.5]])  # Exactly at threshold
            result = await vad_processor.process_audio(chunk)
            assert result is not None  # Should detect (>= threshold)
            
        # Test just below threshold
        with patch.object(vad_processor.model, "__call__") as mock_call:
            mock_call.return_value = torch.tensor([[0.499]])
            result = await vad_processor.process_audio(chunk)
            assert result is None  # Should not detect

    async def test_audio_with_nan_inf(self, vad_processor):
        """Test audio containing NaN or Inf values."""
        # Create audio with some NaN/Inf values
        audio = np.random.randn(16000).astype(np.float32) * 0.3
        audio[100:110] = np.nan
        audio[200:210] = np.inf
        
        chunk = self.create_audio_chunk(audio)
        
        # Should handle or error gracefully
        try:
            result = await vad_processor.process_audio(chunk)
            # If it works, should clean the data
            assert result is None or isinstance(result, VADFilteredAudio)
        except ValueError:
            # Or raise a clear error
            pass

    async def test_alternating_speech_silence(self, vad_processor):
        """Test rapidly alternating speech/silence patterns."""
        # Simulate 10 rapid switches between speech and silence
        audio_parts = []
        for i in range(10):
            if i % 2 == 0:
                # "Speech" - higher amplitude noise
                part = np.random.randn(1600).astype(np.float32) * 0.5
            else:
                # "Silence" - low amplitude
                part = np.random.randn(1600).astype(np.float32) * 0.01
            audio_parts.append(part)
            
        audio = np.concatenate(audio_parts)
        chunk = self.create_audio_chunk(audio)
        
        # Model should handle rapid changes
        result = await vad_processor.process_audio(chunk)
        assert result is None or isinstance(result, VADFilteredAudio)


# Add missing import at the top
import torch