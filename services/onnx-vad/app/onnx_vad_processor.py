"""ONNX-based VAD processor."""

import asyncio
import base64
import io
import time
from typing import List, Optional, Tuple

import numpy as np
import onnxruntime as ort
import soundfile as sf
import structlog
import torch
import torchaudio
from huggingface_hub import hf_hub_download
from pydub import AudioSegment

from app.config import settings
from app.models import AudioChunk, VADResult

logger = structlog.get_logger()


class ONNXVADProcessor:
    """ONNX-based VAD processor using Silero VAD or similar models."""

    def __init__(self):
        """Initialize processor without loading model."""
        self.model = None
        self.device = settings.model_device
        self.sample_rate = settings.vad_sample_rate
        self.initialized = False

        # VAD parameters
        self.threshold = settings.vad_threshold
        self.min_speech_duration_ms = settings.vad_min_speech_duration_ms
        self.min_silence_duration_ms = settings.vad_min_silence_duration_ms
        self.window_size_samples = settings.vad_window_size_samples

        logger.info(
            "ONNXVADProcessor initialized",
            device=self.device,
            sample_rate=self.sample_rate,
            threshold=self.threshold,
        )

    async def initialize(self):
        """Load the ONNX VAD model."""
        if self.initialized:
            logger.info("Model already initialized")
            return

        try:
            logger.info("Loading ONNX VAD model", model=settings.model_name)

            # Try to load Silero VAD ONNX model
            try:
                # Download model from HuggingFace or use local cache
                model_path = hf_hub_download(
                    repo_id="snakers4/silero-vad",
                    filename="silero_vad.onnx",
                    cache_dir="/tmp/cache",  # nosec
                )
            except Exception:
                # Fallback: Try direct torch hub loading and export
                logger.info("Downloading Silero VAD via torch hub")
                model, utils = torch.hub.load(
                    repo_or_dir="snakers4/silero-vad",
                    model="silero_vad",
                    force_reload=False,
                    onnx=True,
                )

                # If we get the model directly, use it
                if hasattr(model, "to_onnx"):
                    model_path = "/tmp/cache/silero_vad.onnx"  # nosec
                    model.to_onnx(model_path)
                else:
                    # Assume model is already ONNX
                    model_path = model

            # Create ONNX runtime session
            providers = (
                ["CUDAExecutionProvider"]
                if self.device == "cuda"
                else ["CPUExecutionProvider"]
            )
            self.model = ort.InferenceSession(str(model_path), providers=providers)

            # Get model info
            self.input_name = self.model.get_inputs()[0].name
            self.output_name = self.model.get_outputs()[0].name

            self.initialized = True
            logger.info("ONNX VAD model loaded successfully")

        except Exception as e:
            logger.error("Failed to load ONNX VAD model", error=str(e))
            raise

    def _decode_audio(self, audio_b64: str, format: str) -> np.ndarray:
        """Decode base64 audio to numpy array."""
        try:
            # Decode base64
            audio_bytes = base64.b64decode(audio_b64)

            # Convert to audio array based on format
            if format in ["mp3", "aac", "m4a"]:
                # Use pydub for compressed formats
                audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format=format)
                # Convert to mono if needed
                if audio.channels > 1:
                    audio = audio.set_channels(1)
                # Resample if needed
                if audio.frame_rate != self.sample_rate:
                    audio = audio.set_frame_rate(self.sample_rate)
                # Convert to numpy array
                samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
                samples = samples / 32768.0  # Normalize to [-1, 1]
            else:
                # Use soundfile for WAV/raw formats
                audio_data, sr = sf.read(io.BytesIO(audio_bytes))
                # Resample if needed
                if sr != self.sample_rate:
                    audio_tensor = torch.from_numpy(audio_data).float()
                    if audio_tensor.dim() == 1:
                        audio_tensor = audio_tensor.unsqueeze(0)
                    resampler = torchaudio.transforms.Resample(sr, self.sample_rate)
                    audio_tensor = resampler(audio_tensor)
                    samples = audio_tensor.squeeze().numpy()
                else:
                    samples = audio_data

                # Convert to mono if needed
                if samples.ndim > 1:
                    samples = samples.mean(axis=1)

            return samples

        except Exception as e:
            logger.error("Failed to decode audio", error=str(e), format=format)
            raise

    def _encode_audio(self, audio_array: np.ndarray, format: str) -> str:
        """Encode numpy array to base64 audio."""
        try:
            # Convert to appropriate format
            if format in ["mp3", "aac", "m4a"]:
                # Use pydub for compressed formats
                # Convert to int16
                audio_int16 = (audio_array * 32768).astype(np.int16)
                audio = AudioSegment(
                    audio_int16.tobytes(),
                    frame_rate=self.sample_rate,
                    sample_width=2,
                    channels=1,
                )
                # Export to format
                buffer = io.BytesIO()
                audio.export(buffer, format=format)
                audio_bytes = buffer.getvalue()
            else:
                # Use soundfile for WAV
                buffer = io.BytesIO()
                sf.write(buffer, audio_array, self.sample_rate, format="WAV")
                audio_bytes = buffer.getvalue()

            # Encode to base64
            return base64.b64encode(audio_bytes).decode("utf-8")

        except Exception as e:
            logger.error("Failed to encode audio", error=str(e))
            raise

    def _run_vad(self, audio_array: np.ndarray) -> Tuple[List[dict], float]:
        """Run VAD on audio and return speech segments and average probability."""
        try:
            # Process audio in windows
            window_size = self.window_size_samples
            step_size = window_size // 2  # 50% overlap

            probabilities = []
            for i in range(0, len(audio_array) - window_size + 1, step_size):
                window = audio_array[i : i + window_size]

                # Prepare input
                input_tensor = window.astype(np.float32)
                if input_tensor.ndim == 1:
                    input_tensor = input_tensor.reshape(1, -1)

                # Run inference
                outputs = self.model.run(
                    [self.output_name], {self.input_name: input_tensor}
                )
                prob = outputs[0][0]  # Assuming single probability output
                probabilities.append(float(prob))

            # Convert probabilities to speech segments
            segments = []
            in_speech = False
            start_idx = 0

            for i, prob in enumerate(probabilities):
                timestamp = (i * step_size) / self.sample_rate

                if prob >= self.threshold and not in_speech:
                    # Start of speech
                    in_speech = True
                    start_idx = i
                elif prob < self.threshold and in_speech:
                    # End of speech
                    start_time = (start_idx * step_size) / self.sample_rate
                    end_time = timestamp
                    duration_ms = (end_time - start_time) * 1000

                    # Check minimum duration
                    if duration_ms >= self.min_speech_duration_ms:
                        segments.append({"start": start_time, "end": end_time})
                    in_speech = False

            # Handle speech extending to end
            if in_speech:
                start_time = (start_idx * step_size) / self.sample_rate
                end_time = len(audio_array) / self.sample_rate
                duration_ms = (end_time - start_time) * 1000

                if duration_ms >= self.min_speech_duration_ms:
                    segments.append({"start": start_time, "end": end_time})

            # Calculate average probability
            avg_prob = sum(probabilities) / len(probabilities) if probabilities else 0.0

            return segments, avg_prob

        except Exception as e:
            logger.error("VAD processing failed", error=str(e))
            raise

    def _extract_speech_audio(
        self, audio_array: np.ndarray, segments: List[dict]
    ) -> np.ndarray:
        """Extract only speech segments from audio."""
        if not segments:
            return np.array([], dtype=np.float32)

        speech_parts = []
        for segment in segments:
            start_sample = int(segment["start"] * self.sample_rate)
            end_sample = int(segment["end"] * self.sample_rate)
            speech_parts.append(audio_array[start_sample:end_sample])

        # Concatenate all speech parts
        return (
            np.concatenate(speech_parts)
            if speech_parts
            else np.array([], dtype=np.float32)
        )

    async def process_audio_chunk(self, chunk: AudioChunk) -> Optional[VADResult]:
        """Process a single audio chunk."""
        if not self.initialized:
            await self.initialize()

        start_time = time.time()

        try:
            # Decode audio
            audio_array = self._decode_audio(chunk.audio_data, chunk.format)

            # Run VAD
            segments, avg_probability = self._run_vad(audio_array)

            # Check if speech detected
            speech_detected = len(segments) > 0 and avg_probability >= self.threshold

            if not speech_detected:
                logger.debug("No speech detected in chunk", device_id=chunk.device_id)
                return None

            # Extract speech audio
            speech_audio = self._extract_speech_audio(audio_array, segments)

            # Calculate total speech duration
            total_speech_duration = sum(seg["end"] - seg["start"] for seg in segments)

            # Encode filtered audio
            filtered_audio_b64 = self._encode_audio(speech_audio, chunk.format)

            # Calculate processing time
            processing_time_ms = (time.time() - start_time) * 1000

            # Create VAD result
            result = VADResult(
                device_id=chunk.device_id,
                audio_data=filtered_audio_b64,
                format=chunk.format,
                sample_rate=chunk.sample_rate,
                duration_seconds=len(speech_audio) / self.sample_rate,
                channels=chunk.channels,
                chunk_number=chunk.chunk_number,
                file_id=chunk.file_id,
                speech_detected=True,
                speech_probability=avg_probability,
                speech_segments=segments,
                total_speech_duration=total_speech_duration,
                processing_time_ms=processing_time_ms,
                original_chunk_id=f"{chunk.file_id}_{chunk.chunk_number}",
            )

            logger.info(
                "VAD processing completed",
                device_id=chunk.device_id,
                num_segments=len(segments),
                total_speech_duration=total_speech_duration,
                processing_time_ms=processing_time_ms,
            )

            return result

        except Exception as e:
            logger.error(
                "Failed to process audio chunk",
                error=str(e),
                device_id=chunk.device_id,
                chunk_number=chunk.chunk_number,
            )
            return None

    async def process_batch(
        self, chunks: List[AudioChunk]
    ) -> List[Optional[VADResult]]:
        """Process a batch of audio chunks."""
        if not chunks:
            return []

        logger.info(f"Processing batch of {len(chunks)} audio chunks")

        # Process chunks concurrently
        tasks = [self.process_audio_chunk(chunk) for chunk in chunks]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle results
        vad_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "Batch processing failed for chunk",
                    error=str(result),
                    index=i,
                    device_id=chunks[i].device_id if i < len(chunks) else "unknown",
                )
                vad_results.append(None)
            else:
                vad_results.append(result)

        return vad_results
