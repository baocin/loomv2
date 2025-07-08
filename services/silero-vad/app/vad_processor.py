"""Silero VAD processor for speech detection using VADIterator."""

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import numpy as np
import structlog
import torch
import torchaudio

from app.config import settings

logger = structlog.get_logger(__name__)


class VADProcessor:
    """Voice Activity Detection using Silero VAD VADIterator for streaming."""

    def __init__(self):
        self.model = None
        self.vad_iterator = None
        self.executor = ThreadPoolExecutor(
            max_workers=1
        )  # Single worker to avoid concurrency
        self._initialized = False
        self._model_lock = asyncio.Lock()
        self._thread_lock = threading.Lock()  # Thread-safe lock for model access

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
        """Load Silero VAD ONNX model with persistent caching."""
        import os

        logger.info(
            "Loading Silero VAD ONNX model",
            model_name=settings.silero_model_name,
            version=settings.silero_model_version,
            use_onnx=settings.silero_use_onnx,
            cache_path=settings.silero_model_cache_path,
        )

        # Ensure cache directory exists
        os.makedirs(settings.silero_model_cache_path, exist_ok=True)

        # Set torch hub cache directory to our persistent location
        old_hub_dir = os.environ.get("TORCH_HUB", None)
        os.environ["TORCH_HUB"] = settings.silero_model_cache_path

        try:
            # Load ONNX model from torch hub (will use our cache directory)
            model, utils = torch.hub.load(
                repo_or_dir="snakers4/silero-vad",
                model="silero_vad",
                force_reload=False,  # Use cache when available
                onnx=True,  # Force ONNX usage
                force_onnx_cpu=True,  # Force CPU for stability
            )

            logger.info(
                "Successfully loaded Silero VAD ONNX model",
                model_type=type(model).__name__,
                cache_used=True,
            )

        finally:
            # Restore original torch hub directory
            if old_hub_dir is not None:
                os.environ["TORCH_HUB"] = old_hub_dir
            else:
                os.environ.pop("TORCH_HUB", None)

        self.model = model

        # Extract utility functions from utils
        self.get_speech_timestamps = utils[0]
        self.save_audio = utils[1]
        self.read_audio = utils[2]
        self.VADIterator = utils[3]
        self.collect_chunks = utils[4]

        # Initialize as None - we'll create fresh instances as needed
        self.vad_iterator = None

        logger.info("Silero VAD model and VADIterator initialized successfully")

    async def process_audio(
        self, audio_data: bytes, sample_rate: int, channels: int
    ) -> list[dict[str, Any]]:
        """Process audio data using VADIterator for streaming detection.

        Args:
            audio_data: Raw audio bytes
            sample_rate: Original sample rate
            channels: Number of channels

        Returns:
            List of speech events with timestamps and audio data
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
        """Synchronous audio processing using get_speech_timestamps (stable batch method)."""
        with self._thread_lock:  # Ensure thread-safe model access
            try:
                # Check if data starts with WAV header
                if audio_data[:4] == b"RIFF":
                    # Skip WAV header (44 bytes for standard WAV)
                    audio_data = audio_data[44:]

                # Convert bytes to numpy array
                audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(
                    np.float32
                )
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

                # Use the stable get_speech_timestamps function instead of VADIterator
                try:
                    # Always reset model states before processing to prevent corruption
                    if hasattr(self.model, "reset_states"):
                        self.model.reset_states()

                    # Log VAD settings for verification
                    logger.debug(
                        "Using VAD settings",
                        threshold=settings.vad_threshold,
                        min_speech_duration_ms=settings.vad_min_speech_duration_ms,
                        min_silence_duration_ms=settings.vad_min_silence_duration_ms,
                        window_size_samples=settings.vad_window_size_samples,
                    )

                    speech_timestamps = self.get_speech_timestamps(
                        audio_tensor,
                        self.model,
                        threshold=settings.vad_threshold,
                        min_speech_duration_ms=settings.vad_min_speech_duration_ms,
                        min_silence_duration_ms=settings.vad_min_silence_duration_ms,
                        window_size_samples=settings.vad_window_size_samples,
                        sampling_rate=settings.vad_sample_rate,
                        return_seconds=False,  # Return sample indices
                    )
                except RuntimeError as e:
                    if "index 1 out of range" in str(e):
                        logger.warning(
                            "VAD model state corrupted, skipping chunk", error=str(e)
                        )
                        return []
                    raise

                # Convert timestamps to milliseconds and extract audio segments
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
                    "Processed audio using get_speech_timestamps",
                    segments_found=len(segments),
                    total_duration_ms=len(audio_tensor)
                    / settings.vad_sample_rate
                    * 1000,
                )

                return segments

            except Exception as e:
                logger.error(
                    "Error processing audio with get_speech_timestamps", error=str(e)
                )
                raise

    def reset_states(self) -> None:
        """Reset model states for new audio stream."""
        if self.model and hasattr(self.model, "reset_states"):
            self.model.reset_states()
            logger.debug("VAD model states reset")

    async def cleanup(self) -> None:
        """Cleanup resources."""
        if self.model and hasattr(self.model, "reset_states"):
            self.model.reset_states()
        self.executor.shutdown(wait=True)
        self._initialized = False
        logger.info("VAD processor cleaned up")
