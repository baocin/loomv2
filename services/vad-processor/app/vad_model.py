"""Silero VAD model wrapper."""

import torch
import torchaudio
import numpy as np
from typing import List, Tuple, Optional
import structlog
from io import BytesIO

from .models import VADSegment

logger = structlog.get_logger(__name__)


class SileroVAD:
    """Wrapper for Silero Voice Activity Detection model."""

    def __init__(self, threshold: float = 0.5, sampling_rate: int = 16000):
        """Initialize VAD model.
        
        Args:
            threshold: Confidence threshold for speech detection
            sampling_rate: Expected audio sampling rate
        """
        self.threshold = threshold
        self.sampling_rate = sampling_rate
        self.model = None
        self.utils = None
        self._load_model()

    def _load_model(self) -> None:
        """Load Silero VAD model from torch hub."""
        try:
            logger.info("Loading Silero VAD model...")
            self.model, self.utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                onnx=False
            )
            self.model.eval()
            logger.info("Silero VAD model loaded successfully")
        except Exception as e:
            logger.error("Failed to load VAD model", error=str(e))
            raise

    def process_audio(
        self,
        audio_bytes: bytes,
        sample_rate: int,
        min_speech_duration_ms: int = 250,
        max_speech_duration_ms: int = 30000,
        padding_ms: int = 100
    ) -> List[Tuple[VADSegment, bytes]]:
        """Process audio and extract speech segments.
        
        Args:
            audio_bytes: Raw audio data
            sample_rate: Audio sample rate
            min_speech_duration_ms: Minimum speech duration to keep
            max_speech_duration_ms: Maximum speech duration per segment
            padding_ms: Padding to add before/after speech
            
        Returns:
            List of (VADSegment, audio_bytes) tuples
        """
        try:
            # Load audio from bytes
            audio_tensor = self._load_audio_from_bytes(audio_bytes, sample_rate)
            
            # Resample if necessary
            if sample_rate != self.sampling_rate:
                resampler = torchaudio.transforms.Resample(
                    orig_freq=sample_rate,
                    new_freq=self.sampling_rate
                )
                audio_tensor = resampler(audio_tensor)
            
            # Ensure mono audio
            if audio_tensor.shape[0] > 1:
                audio_tensor = torch.mean(audio_tensor, dim=0, keepdim=True)
            
            # Get speech timestamps
            speech_timestamps = self.utils[0](
                audio_tensor,
                self.model,
                threshold=self.threshold,
                sampling_rate=self.sampling_rate,
                min_speech_duration_ms=min_speech_duration_ms,
                max_speech_duration_ms=max_speech_duration_ms,
                return_seconds=False  # Return sample indices
            )
            
            # Extract speech segments
            segments = []
            for timestamp in speech_timestamps:
                start_sample = max(0, timestamp['start'] - int(padding_ms * self.sampling_rate / 1000))
                end_sample = min(
                    audio_tensor.shape[1],
                    timestamp['end'] + int(padding_ms * self.sampling_rate / 1000)
                )
                
                # Extract segment
                segment_tensor = audio_tensor[:, start_sample:end_sample]
                segment_bytes = self._tensor_to_bytes(segment_tensor, self.sampling_rate)
                
                # Create VAD segment
                vad_segment = VADSegment(
                    start_ms=int(start_sample * 1000 / self.sampling_rate),
                    end_ms=int(end_sample * 1000 / self.sampling_rate),
                    confidence=timestamp.get('confidence', 1.0)
                )
                
                segments.append((vad_segment, segment_bytes))
            
            return segments
            
        except Exception as e:
            logger.error("Error processing audio", error=str(e))
            raise

    def _load_audio_from_bytes(self, audio_bytes: bytes, sample_rate: int) -> torch.Tensor:
        """Load audio tensor from bytes."""
        # Assume PCM16 format for now
        audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
        audio_tensor = torch.from_numpy(audio_array).float() / 32768.0  # Normalize to [-1, 1]
        return audio_tensor.unsqueeze(0)  # Add channel dimension

    def _tensor_to_bytes(self, audio_tensor: torch.Tensor, sample_rate: int) -> bytes:
        """Convert audio tensor back to bytes."""
        # Convert to PCM16
        audio_array = (audio_tensor.squeeze(0).numpy() * 32768.0).astype(np.int16)
        return audio_array.tobytes()