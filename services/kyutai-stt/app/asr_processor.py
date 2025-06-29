"""ASR processing using Whisper model."""

import base64
import io
import time

import numpy as np
import structlog
import torch
import torchaudio
from transformers import pipeline

from app.config import settings
from app.models import AudioChunk, TranscribedText, TranscribedWord

logger = structlog.get_logger()


class ASRProcessor:
    """Processes audio using Whisper for speech-to-text."""

    def __init__(self):
        self.pipe = None
        self.device = settings.model_device
        logger.info(
            "Initializing ASR processor", device=self.device, model=settings.model_name
        )

    async def initialize(self):
        """Initialize the model and processor."""
        try:
            logger.info("Loading Whisper model", model=settings.model_name)

            # Determine device
            if self.device == "cuda" and torch.cuda.is_available():
                device = 0
                torch_dtype = torch.float16
            else:
                device = -1
                torch_dtype = torch.float32
                self.device = "cpu"

            # Create pipeline for ASR
            self.pipe = pipeline(
                "automatic-speech-recognition",
                model=settings.model_name,
                device=device,
                torch_dtype=torch_dtype,
                trust_remote_code=True,
                model_kwargs={
                    "cache_dir": settings.model_cache_dir,
                },
            )

            logger.info(f"ASR processor initialized successfully on {self.device}")

        except Exception as e:
            logger.error("Failed to initialize ASR processor", error=str(e))
            raise

    def _decode_audio(self, audio_data: str, format: str) -> tuple[np.ndarray, int]:
        """Decode base64 audio data to numpy array."""
        try:
            # Decode base64
            audio_bytes = base64.b64decode(audio_data)

            # Load audio using torchaudio
            audio_tensor, sample_rate = torchaudio.load(
                io.BytesIO(audio_bytes), format=format
            )

            # Convert to mono if stereo
            if audio_tensor.shape[0] > 1:
                audio_tensor = torch.mean(audio_tensor, dim=0, keepdim=True)

            # Resample if necessary
            if sample_rate != settings.target_sample_rate:
                resampler = torchaudio.transforms.Resample(
                    sample_rate, settings.target_sample_rate
                )
                audio_tensor = resampler(audio_tensor)
                sample_rate = settings.target_sample_rate

            # Convert to numpy
            audio_array = audio_tensor.squeeze().numpy()

            return audio_array, sample_rate

        except Exception as e:
            logger.error("Failed to decode audio", error=str(e))
            raise

    def _extract_word_timestamps(
        self, audio_array: np.ndarray, sample_rate: int
    ) -> list[TranscribedWord]:
        """Extract word-level timestamps using the Whisper model."""
        try:
            # Run inference with the pipeline
            result = self.pipe(
                audio_array,
                generate_kwargs={
                    "task": "transcribe",
                    "language": "en",
                },
                return_timestamps="word",
            )

            # Extract words with timestamps if available
            words = []
            if "chunks" in result:
                # Pipeline returned word-level chunks
                for chunk in result["chunks"]:
                    word = TranscribedWord(
                        word=chunk["text"].strip(),
                        start_time=chunk["timestamp"][0] if chunk["timestamp"] else 0.0,
                        end_time=chunk["timestamp"][1] if chunk["timestamp"] else 0.0,
                        confidence=0.9,  # Default confidence for Whisper
                    )
                    words.append(word)
            elif "text" in result:
                # No word timestamps, create estimated ones
                words = self._create_word_timestamps(
                    result["text"], audio_array, sample_rate
                )

            return words

        except Exception as e:
            logger.error("Failed to extract word timestamps", error=str(e))
            # Fallback to simple transcription
            return self._simple_transcribe(audio_array, sample_rate)

    def _create_word_timestamps(
        self, text: str, audio_array: np.ndarray, sample_rate: int
    ) -> list[TranscribedWord]:
        """Create estimated word timestamps from transcribed text."""
        words = []
        if not text:
            return words

        # Split text into words
        word_list = text.split()
        if not word_list:
            return words

        # Calculate total duration
        total_duration = len(audio_array) / sample_rate

        # Estimate word durations based on character count
        total_chars = sum(len(word) for word in word_list)

        current_time = 0.0
        for word_text in word_list:
            # Estimate duration proportional to word length
            word_proportion = (
                len(word_text) / total_chars
                if total_chars > 0
                else 1.0 / len(word_list)
            )
            word_duration = (
                total_duration * word_proportion * 0.9
            )  # 90% for words, 10% for gaps

            word = TranscribedWord(
                word=word_text,
                start_time=current_time,
                end_time=current_time + word_duration,
                confidence=0.85,  # Default confidence estimate
            )
            words.append(word)

            # Add small gap between words
            current_time += word_duration + (total_duration * 0.1 / len(word_list))

        return words

    def _simple_transcribe(
        self, audio_array: np.ndarray, sample_rate: int
    ) -> list[TranscribedWord]:
        """Simple transcription without word-level timestamps as fallback."""
        try:
            # Run basic transcription
            result = self.pipe(
                audio_array,
                generate_kwargs={
                    "task": "transcribe",
                    "language": "en",
                },
            )

            if result and "text" in result:
                return self._create_word_timestamps(
                    result["text"], audio_array, sample_rate
                )
            else:
                return []

        except Exception as e:
            logger.error("Failed in simple transcribe", error=str(e))
            return []

    async def process_audio_chunk(self, chunk: AudioChunk) -> TranscribedText | None:
        """Process a single audio chunk and return transcribed text with word timestamps."""
        start_time = time.time()

        try:
            # Decode audio
            audio_array, sample_rate = self._decode_audio(
                chunk.audio_data, chunk.format
            )

            logger.debug(
                "Audio decoded",
                chunk_id=chunk.chunk_id,
                duration=len(audio_array) / sample_rate,
                sample_rate=sample_rate,
            )

            # Extract words with timestamps
            words = self._extract_word_timestamps(audio_array, sample_rate)

            if not words:
                logger.warning("No words transcribed", chunk_id=chunk.chunk_id)
                return None

            # Create full text from words
            full_text = " ".join(word.word for word in words)

            # Calculate processing time
            processing_time_ms = (time.time() - start_time) * 1000

            # Create transcribed text message
            transcribed = TranscribedText(
                device_id=chunk.device_id,
                recorded_at=chunk.recorded_at,
                chunk_id=chunk.chunk_id,
                words=words,
                full_text=full_text,
                processing_time_ms=processing_time_ms,
                model_version=settings.model_name,
            )

            logger.info(
                "Audio chunk transcribed",
                chunk_id=chunk.chunk_id,
                word_count=len(words),
                processing_time_ms=processing_time_ms,
                device=self.device,
            )

            return transcribed

        except Exception as e:
            logger.error(
                "Failed to process audio chunk", chunk_id=chunk.chunk_id, error=str(e)
            )
            return None
