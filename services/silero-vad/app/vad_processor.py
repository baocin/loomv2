"""Silero VAD processor for speech detection."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import numpy as np
import structlog
import torch
import torchaudio

from app.config import settings

logger = structlog.get_logger(__name__)


class VADProcessor:
    """Voice Activity Detection using Silero VAD model."""

    def __init__(self):
        self.model = None
        self.utils = None
        self.executor = ThreadPoolExecutor(max_workers=2)
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the VAD model asynchronously."""
        if self._initialized:
            return

        try:
            # Load model in thread pool to avoid blocking
            await asyncio.get_event_loop().run_in_executor(
                self.executor, self._load_model
            )
            self._initialized = True
            logger.info("VAD processor initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize VAD processor", error=str(e))
            raise

    def _load_model(self) -> None:
        """Load Silero VAD model from torch hub."""
        logger.info(
            "Loading Silero VAD model",
            model_name=settings.silero_model_name,
            version=settings.silero_model_version,
        )

        # Load model from torch hub
        model, utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=False,
            onnx=settings.silero_use_onnx,
        )

        self.model = model
        self.utils = utils

        # Get utility functions
        self.get_speech_timestamps = utils[0]
        self.save_audio = utils[1]
        self.read_audio = utils[2]
        self.VADIterator = utils[3]
        self.collect_chunks = utils[4]

        logger.info("Silero VAD model loaded successfully")

    async def process_audio(
        self, audio_data: bytes, sample_rate: int, channels: int
    ) -> list[dict[str, Any]]:
        """Process audio data and detect speech segments.

        Args:
            audio_data: Raw audio bytes
            sample_rate: Original sample rate
            channels: Number of channels

        Returns:
            List of speech segments with timestamps and confidence
        """
        if not self._initialized:
            await self.initialize()

        # Process in thread pool to avoid blocking
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, self._process_audio_sync, audio_data, sample_rate, channels
        )

    def _process_audio_sync(
        self, audio_data: bytes, sample_rate: int, channels: int
    ) -> list[dict[str, Any]]:
        """Synchronous audio processing."""
        try:
            # Convert bytes to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
            audio_array = audio_array / 32768.0  # Normalize to [-1, 1]

            # Handle multi-channel audio by averaging
            if channels > 1:
                audio_array = audio_array.reshape(-1, channels).mean(axis=1)

            # Convert to torch tensor
            audio_tensor = torch.from_numpy(audio_array)

            # Resample if necessary (Silero expects 16kHz)
            if sample_rate != settings.vad_sample_rate:
                resampler = torchaudio.transforms.Resample(
                    orig_freq=sample_rate, new_freq=settings.vad_sample_rate
                )
                audio_tensor = resampler(audio_tensor)

            # Get speech timestamps
            speech_timestamps = self.get_speech_timestamps(
                audio_tensor,
                self.model,
                threshold=settings.vad_threshold,
                min_speech_duration_ms=settings.vad_min_speech_duration_ms,
                min_silence_duration_ms=settings.vad_min_silence_duration_ms,
                window_size_samples=settings.vad_window_size_samples,
                sampling_rate=settings.vad_sample_rate,
            )

            # Convert timestamps to milliseconds
            segments = []
            for segment in speech_timestamps:
                start_ms = (segment["start"] / settings.vad_sample_rate) * 1000
                end_ms = (segment["end"] / settings.vad_sample_rate) * 1000

                # Extract speech segment
                start_sample = segment["start"]
                end_sample = segment["end"]
                speech_audio = audio_tensor[start_sample:end_sample]

                # Convert back to bytes
                speech_array = (speech_audio.numpy() * 32768).astype(np.int16)
                speech_bytes = speech_array.tobytes()

                segments.append(
                    {
                        "start_ms": start_ms,
                        "end_ms": end_ms,
                        "duration_ms": end_ms - start_ms,
                        "confidence": segment.get("confidence", 1.0),
                        "audio_data": speech_bytes,
                        "sample_rate": settings.vad_sample_rate,
                    }
                )

            logger.debug(
                "Processed audio chunk",
                segments_found=len(segments),
                total_duration_ms=len(audio_tensor) / settings.vad_sample_rate * 1000,
            )

            return segments

        except Exception as e:
            logger.error("Error processing audio", error=str(e))
            raise

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.executor.shutdown(wait=True)
        self._initialized = False
        logger.info("VAD processor cleaned up")
