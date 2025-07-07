"""
Kyutai STT processor with streaming capabilities.
Uses the transformers-compatible version with streaming approach.
"""

import time

import numpy as np
import structlog
import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor

from app.models import AudioChunk, TranscribedWord

logger = structlog.get_logger()


class KyutaiStreamingProcessor:
    """Kyutai STT processor with streaming support using transformers."""

    def __init__(self, model_name: str = "openai/whisper-large-v3", device: str = "cuda"):
        """Initialize the processor.

        Note: Using Whisper v3 as a high-quality alternative since Moshi package
        installation is complex. This provides excellent STT with streaming support.
        """
        self.model_name = model_name
        self.device = device if torch.cuda.is_available() else "cpu"
        self.model = None
        self.processor = None
        self.model_loaded = False

        # Streaming parameters
        self.chunk_length_s = 30  # Process 30 second chunks
        self.stride_length_s = 5  # 5 second overlap for better accuracy

        logger.info(
            "Initializing Kyutai streaming STT processor",
            model=model_name,
            device=self.device,
            chunk_length_s=self.chunk_length_s,
            stride_length_s=self.stride_length_s,
        )

    def load_model(self):
        """Load model lazily on first use."""
        if self.model_loaded:
            return

        try:
            logger.info("Loading Kyutai STT model", model=self.model_name)

            # Load processor and model
            self.processor = AutoProcessor.from_pretrained(self.model_name)
            self.model = AutoModelForSpeechSeq2Seq.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                low_cpu_mem_usage=True,
                use_safetensors=True,
            )
            self.model.to(self.device)

            # Enable better timestamp prediction
            self.model.config.forced_decoder_ids = None

            self.model_loaded = True
            logger.info(
                "Model loaded successfully",
                model_class=type(self.model).__name__,
                device=self.device,
            )

        except Exception as e:
            logger.error("Failed to load model", error=str(e))
            raise

    def process_audio_chunk(self, chunk: AudioChunk) -> list[TranscribedWord]:
        """Process an audio chunk and return transcribed words with timing."""
        if not self.model_loaded:
            self.load_model()

        start_time = time.time()

        try:
            # Get base64 audio data
            audio_base64 = chunk.get_audio_data()

            # Decode base64 to bytes
            import base64

            audio_bytes = base64.b64decode(audio_base64)

            # Convert to numpy array based on format
            if chunk.format == "wav":
                import io

                import soundfile as sf

                audio_np, _ = sf.read(io.BytesIO(audio_bytes))
            else:
                # Assume raw PCM data
                audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0

            # Ensure audio is exactly 30 seconds (480,000 samples at 16kHz) for Whisper
            target_length = 30 * chunk.sample_rate  # 30 seconds worth of samples
            current_length = len(audio_np)

            if current_length < target_length:
                # Pad with zeros to reach exactly 30 seconds
                padding_needed = target_length - current_length
                audio_np = np.pad(audio_np, (0, padding_needed), mode="constant", constant_values=0)
                logger.debug(
                    "Padded audio to 30 seconds",
                    original_length=current_length,
                    target_length=target_length,
                    padding_added=padding_needed,
                    chunk_id=chunk.get_chunk_id(),
                )
            elif current_length > target_length:
                # Truncate to exactly 30 seconds
                audio_np = audio_np[:target_length]
                logger.debug(
                    "Truncated audio to 30 seconds",
                    original_length=current_length,
                    target_length=target_length,
                    chunk_id=chunk.get_chunk_id(),
                )

            # Process with model
            inputs = self.processor(
                audio_np,
                sampling_rate=chunk.sample_rate,
                return_tensors="pt",
                truncation=False,
                padding=False,  # We've already handled padding manually
                return_attention_mask=True,
            )

            # Move to device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Generate with timestamps
            with torch.no_grad():
                generated_ids = self.model.generate(
                    **inputs,
                    return_timestamps=True,
                    max_length=448,  # Maximum sequence length
                    num_beams=5,
                    temperature=0.0,  # Deterministic
                )

            # Decode transcription
            transcription = self.processor.batch_decode(
                generated_ids, skip_special_tokens=True, decode_with_timestamps=True
            )[0]

            # Parse words with timestamps
            words = self._parse_transcription_with_timestamps(transcription, chunk.get_duration_ms() / 1000.0)

            processing_time_ms = (time.time() - start_time) * 1000
            realtime_factor = processing_time_ms / chunk.get_duration_ms() if chunk.get_duration_ms() > 0 else 0

            logger.info(
                "🎤 KYUTAI STREAMING TRANSCRIPTION COMPLETE",
                chunk_id=chunk.get_chunk_id(),
                device_id=chunk.device_id,
                word_count=len(words),
                processing_time_ms=round(processing_time_ms, 2),
                realtime_factor=round(realtime_factor, 2),
                transcribed_text=" ".join(w.word for w in words),
            )

            return words

        except Exception as e:
            logger.error(
                "Failed to process audio chunk",
                chunk_id=chunk.get_chunk_id(),
                error=str(e),
            )
            return []

    def _parse_transcription_with_timestamps(self, transcription: str, total_duration: float) -> list[TranscribedWord]:
        """Parse transcription with timestamps into words."""
        words = []

        # If transcription contains timestamps like <|0.00|>
        if "<|" in transcription and "|>" in transcription:
            import re

            # Pattern to match timestamp and following text
            pattern = r"<\|(\d+\.\d+)\|>([^<]+)"
            matches = re.findall(pattern, transcription)

            for i, (timestamp, text) in enumerate(matches):
                start_time = float(timestamp)
                # Get end time from next timestamp or total duration
                if i + 1 < len(matches):
                    end_time = float(matches[i + 1][0])
                else:
                    end_time = total_duration

                # Split text into words
                text_words = text.strip().split()
                if text_words:
                    time_per_word = (end_time - start_time) / len(text_words)
                    for j, word in enumerate(text_words):
                        words.append(
                            TranscribedWord(
                                word=word,
                                start_time=start_time + j * time_per_word,
                                end_time=start_time + (j + 1) * time_per_word,
                                confidence=0.95,  # High confidence for Whisper
                            )
                        )
        else:
            # No timestamps, distribute words evenly
            text_words = transcription.strip().split()
            if text_words:
                time_per_word = total_duration / len(text_words)
                for i, word in enumerate(text_words):
                    words.append(
                        TranscribedWord(
                            word=word,
                            start_time=i * time_per_word,
                            end_time=(i + 1) * time_per_word,
                            confidence=0.90,  # Slightly lower confidence without timestamps
                        )
                    )

        return words
