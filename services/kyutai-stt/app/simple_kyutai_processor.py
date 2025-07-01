"""Simplified Kyutai STT processor using Whisper as a placeholder."""

import base64
import io
import time
from typing import Optional

import numpy as np
import structlog
import torch
import torchaudio
from transformers import KyutaiSpeechToTextProcessor, KyutaiSpeechToTextForConditionalGeneration

from app.config import settings
from app.models import AudioChunk, TranscribedText, TranscribedWord

logger = structlog.get_logger()


class SimpleKyutaiProcessor:
    """Simplified STT processor using Whisper until Kyutai Mimi is properly integrated."""

    def __init__(self):
        self.processor = None
        self.model = None
        self.device = settings.model_device
        logger.info(
            "Initializing Kyutai STT processor",
            device=self.device,
            model=settings.model_name
        )

    async def initialize(self):
        """Initialize the model."""
        try:
            logger.info("Loading Kyutai STT model", model=settings.model_name)
            
            # Determine device and torch dtype
            if self.device == "cuda" and torch.cuda.is_available():
                torch_dtype = torch.float16
                device_map = "cuda"
            else:
                torch_dtype = torch.float32
                device_map = "cpu"
                self.device = "cpu"
                print(f"Device set to use {self.device}")

            # Load Kyutai STT processor and model
            self.processor = KyutaiSpeechToTextProcessor.from_pretrained(
                settings.model_name,
                cache_dir=settings.model_cache_dir,
            )
            
            self.model = KyutaiSpeechToTextForConditionalGeneration.from_pretrained(
                settings.model_name,
                device_map=device_map,
                torch_dtype=torch_dtype,
                cache_dir=settings.model_cache_dir,
            )

            logger.info(
                "Kyutai STT processor initialized successfully",
                model=settings.model_name,
                device=self.device,
                cuda_available=torch.cuda.is_available(),
            )

        except Exception as e:
            logger.error("Failed to initialize STT processor", error=str(e))
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

            # Resample to 24kHz (Kyutai's expected rate)
            if sample_rate != 24000:
                resampler = torchaudio.transforms.Resample(sample_rate, 24000)
                audio_tensor = resampler(audio_tensor)
                sample_rate = 24000

            # Convert to numpy
            audio_array = audio_tensor.squeeze().numpy()

            return audio_array, sample_rate

        except Exception as e:
            logger.error("Failed to decode audio", error=str(e))
            raise

    def _extract_words_from_text(
        self, text: str, audio_duration: float
    ) -> list[TranscribedWord]:
        """Extract words with estimated timestamps from transcribed text."""
        words = []
        if not text:
            return words

        # Split text into words
        word_list = text.split()
        if not word_list:
            return words

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
                audio_duration * word_proportion * 0.9
            )  # 90% for words, 10% for gaps

            word = TranscribedWord(
                word=word_text,
                start_time=current_time,
                end_time=current_time + word_duration,
                confidence=0.9,  # Default confidence
            )
            words.append(word)

            # Add small gap between words
            current_time += word_duration + (audio_duration * 0.1 / len(word_list))

        return words

    async def process_audio_chunk(self, chunk: AudioChunk) -> TranscribedText | None:
        """Process a single audio chunk and return transcribed text with word timestamps."""
        start_time = time.time()

        try:
            # Decode audio
            audio_array, sample_rate = self._decode_audio(
                chunk.get_audio_data(), chunk.format
            )

            logger.info(
                "Raw audio decoded for STT",
                chunk_id=chunk.get_chunk_id(),
                device_id=chunk.device_id,
                duration=len(audio_array) / sample_rate,
                sample_rate=sample_rate,
                file_id=chunk.file_id,
                duration_ms=chunk.get_duration_ms(),
            )

            # Transcribe using Kyutai processor and model
            inputs = self.processor(audio_array)
            
            # Move inputs to device if needed
            if self.device == "cuda" and torch.cuda.is_available():
                inputs = {k: v.to("cuda") if isinstance(v, torch.Tensor) else v for k, v in inputs.items()}
            
            # Generate transcription
            output_tokens = self.model.generate(**inputs)
            transcription_result = self.processor.batch_decode(output_tokens, skip_special_tokens=True)
            
            if not transcription_result or len(transcription_result) == 0:
                logger.warning("No text transcribed", chunk_id=chunk.get_chunk_id())
                return None

            transcribed_text = transcription_result[0].strip()
            if not transcribed_text:
                logger.warning("Empty transcription", chunk_id=chunk.get_chunk_id())
                return None

            # Extract words with estimated timestamps
            audio_duration = len(audio_array) / sample_rate
            words = self._extract_words_from_text(transcribed_text, audio_duration)

            # Calculate processing time
            processing_time_ms = (time.time() - start_time) * 1000

            # Create transcribed text message
            transcribed = TranscribedText(
                device_id=chunk.device_id,
                recorded_at=chunk.recorded_at,
                timestamp=chunk.timestamp,
                message_id=f"{chunk.message_id or 'stt'}_transcribed",
                trace_id=chunk.trace_id,
                services_encountered=(chunk.services_encountered or []) + ["kyutai-stt"],
                content_hash=chunk.content_hash,
                chunk_id=chunk.get_chunk_id(),
                words=words,
                text=transcribed_text,
                processing_time_ms=processing_time_ms,
                model_version=settings.model_name,
            )

            logger.info(
                "🎤 TRANSCRIPTION COMPLETE",
                chunk_id=chunk.get_chunk_id(),
                device_id=chunk.device_id,
                word_count=len(words),
                text_length=len(transcribed_text),
                full_text=transcribed_text,
                text_preview=transcribed_text[:100] + '...' if len(transcribed_text) > 100 else transcribed_text,
                processing_time_ms=round(processing_time_ms, 2),
                input_duration_ms=chunk.get_duration_ms(),
                realtime_factor=round(processing_time_ms / max(chunk.get_duration_ms(), 1), 2),
                device=self.device,
                model=settings.model_name,
                word_details=[{"word": w.word, "start": w.start_time, "end": w.end_time, "confidence": w.confidence} for w in words[:5]] if words else [],
            )

            return transcribed

        except Exception as e:
            logger.error(
                "Failed to process audio chunk", 
                chunk_id=chunk.get_chunk_id(), 
                device_id=chunk.device_id,
                error=str(e),
                error_type=type(e).__name__,
                duration_ms=chunk.get_duration_ms(),
            )
            return None