"""ASR processing using NVIDIA Parakeet-TDT model."""

import base64
import io
import time

import numpy as np
import structlog
import torch
import torchaudio
from transformers import AutoModelForCTC, AutoProcessor, pipeline

from app.config import settings
from app.models import AudioChunk, TranscribedText, TranscribedWord

logger = structlog.get_logger()


class ASRProcessor:
    """Processes audio using NVIDIA Parakeet-TDT for speech-to-text."""

    def __init__(self):
        self.model = None
        self.processor = None
        self.pipeline = None
        self.device = settings.model_device
        logger.info("Initializing ASR processor", device=self.device, model=settings.model_name)

    async def initialize(self):
        """Initialize the model and processor."""
        try:
            logger.info("Loading Parakeet-TDT model", model=settings.model_name)

            # Load processor and model
            self.processor = AutoProcessor.from_pretrained(settings.model_name, cache_dir=settings.model_cache_dir)

            self.model = AutoModelForCTC.from_pretrained(settings.model_name, cache_dir=settings.model_cache_dir)

            # Move model to device
            if self.device == "cuda" and torch.cuda.is_available():
                self.model = self.model.cuda()
                logger.info("Model loaded on GPU")
            else:
                self.device = "cpu"
                logger.info("Model loaded on CPU")

            # Create pipeline for easier inference
            self.pipeline = pipeline(
                "automatic-speech-recognition",
                model=self.model,
                tokenizer=self.processor,
                feature_extractor=self.processor.feature_extractor,
                device=0 if self.device == "cuda" else -1,
                chunk_length_s=30,  # Process in 30-second chunks
                stride_length_s=5,  # 5-second overlap between chunks
            )

            logger.info("ASR processor initialized successfully")

        except Exception as e:
            logger.error("Failed to initialize ASR processor", error=str(e))
            raise

    def _decode_audio(self, audio_data: str, format: str) -> tuple[np.ndarray, int]:
        """Decode base64 audio data to numpy array."""
        try:
            # Decode base64
            audio_bytes = base64.b64decode(audio_data)

            # Load audio using torchaudio
            audio_tensor, sample_rate = torchaudio.load(io.BytesIO(audio_bytes), format=format)

            # Convert to mono if stereo
            if audio_tensor.shape[0] > 1:
                audio_tensor = torch.mean(audio_tensor, dim=0, keepdim=True)

            # Resample if necessary
            if sample_rate != settings.target_sample_rate:
                resampler = torchaudio.transforms.Resample(sample_rate, settings.target_sample_rate)
                audio_tensor = resampler(audio_tensor)
                sample_rate = settings.target_sample_rate

            # Convert to numpy
            audio_array = audio_tensor.squeeze().numpy()

            return audio_array, sample_rate

        except Exception as e:
            logger.error("Failed to decode audio", error=str(e))
            raise

    def _extract_word_timestamps(self, audio_array: np.ndarray, sample_rate: int) -> list[TranscribedWord]:
        """Extract word-level timestamps using the model."""
        try:
            # Process through the model
            inputs = self.processor(
                audio_array,
                sampling_rate=sample_rate,
                return_tensors="pt",
                padding=True,
            )

            # Move inputs to device
            if self.device == "cuda":
                inputs = {k: v.cuda() for k, v in inputs.items()}

            # Get model outputs with attention
            with torch.no_grad():
                outputs = self.model(**inputs, output_attentions=True)

            # Get predictions
            pred_ids = torch.argmax(outputs.logits, dim=-1)

            # Decode predictions with timestamps
            transcription = self.processor.batch_decode(pred_ids, output_word_offsets=True, output_char_offsets=False)

            # Extract words with timestamps
            words = []
            if transcription and len(transcription) > 0:
                result = transcription[0]

                # If word offsets are available
                if hasattr(result, "word_offsets") and result.word_offsets:
                    for word_info in result.word_offsets:
                        word = TranscribedWord(
                            word=word_info["word"],
                            start_time=word_info["start_offset"] / sample_rate,
                            end_time=word_info["end_offset"] / sample_rate,
                            confidence=word_info.get("confidence", 0.9),
                        )
                        words.append(word)
                else:
                    # Fallback: use pipeline for transcription with timestamps
                    pipeline_result = self.pipeline(
                        audio_array,
                        return_timestamps="word",
                        generate_kwargs={"language": "en"},
                    )

                    if "chunks" in pipeline_result:
                        for chunk in pipeline_result["chunks"]:
                            word = TranscribedWord(
                                word=chunk["text"].strip(),
                                start_time=(chunk["timestamp"][0] if chunk["timestamp"] else 0.0),
                                end_time=(chunk["timestamp"][1] if chunk["timestamp"] else 0.0),
                                confidence=0.9,  # Default confidence
                            )
                            words.append(word)

            return words

        except Exception as e:
            logger.error("Failed to extract word timestamps", error=str(e))
            # Fallback to simple transcription without timestamps
            return self._simple_transcribe(audio_array, sample_rate)

    def _simple_transcribe(self, audio_array: np.ndarray, sample_rate: int) -> list[TranscribedWord]:
        """Simple transcription without word-level timestamps as fallback."""
        try:
            # Use pipeline for simple transcription
            result = self.pipeline(audio_array)
            text = result["text"] if isinstance(result, dict) else str(result)

            # Split into words and create dummy timestamps
            words = []
            current_time = 0.0
            for word_text in text.split():
                # Estimate word duration based on length
                word_duration = len(word_text) * 0.1  # 0.1 seconds per character (rough estimate)

                word = TranscribedWord(
                    word=word_text,
                    start_time=current_time,
                    end_time=current_time + word_duration,
                    confidence=0.8,  # Lower confidence for estimated timestamps
                )
                words.append(word)
                current_time += word_duration + 0.1  # Add small gap between words

            return words

        except Exception as e:
            logger.error("Failed in simple transcribe", error=str(e))
            return []

    async def process_audio_chunk(self, chunk: AudioChunk) -> TranscribedText | None:
        """Process a single audio chunk and return transcribed text with word timestamps."""
        start_time = time.time()

        try:
            # Decode audio
            audio_array, sample_rate = self._decode_audio(chunk.audio_data, chunk.format)

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
            logger.error("Failed to process audio chunk", chunk_id=chunk.chunk_id, error=str(e))
            return None
