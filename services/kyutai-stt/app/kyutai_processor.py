"""ASR processing using Kyutai Mimi model following the Colab example."""

import base64
import io
import time
from typing import Optional

import numpy as np
import sentencepiece
import sphn
import structlog
import torch
import torchaudio
from moshi.models import loaders, MimiModel, LMModel, LMGen

from app.config import settings
from app.models import AudioChunk, TranscribedText, TranscribedWord

logger = structlog.get_logger()


class InferenceState:
    """Inference state for speech transcription following the Colab example."""
    
    def __init__(
        self,
        mimi: MimiModel,
        text_tokenizer: sentencepiece.SentencePieceProcessor,
        lm: LMModel,
        batch_size: int,
        device: str | torch.device,
    ):
        self.mimi = mimi
        self.text_tokenizer = text_tokenizer
        self.lm = lm
        self.lm_gen = LMGen(
            lm, 
            temp=settings.temp, 
            temp_text=settings.temp_text, 
            use_sampling=settings.use_sampling
        )
        self.batch_size = batch_size
        self.device = device
        
        # Initialize streaming state
        self._reset_state()
        
    def _reset_state(self):
        """Reset the inference state for new audio."""
        self.transcribed_tokens = []
        self.audio_buffer = []
        
    def run(self, in_pcms: torch.Tensor) -> str:
        """Run transcription on audio following the Colab implementation."""
        # Convert audio to Mimi tokens
        with torch.no_grad():
            # Ensure audio is on the correct device
            in_pcms = in_pcms.to(self.device)
            
            # Add batch dimension if needed
            if in_pcms.dim() == 1:
                in_pcms = in_pcms.unsqueeze(0).unsqueeze(0)  # [B=1, C=1, T]
            elif in_pcms.dim() == 2:
                in_pcms = in_pcms.unsqueeze(0)  # [B=1, C, T]
                
            # Encode audio to tokens using Mimi
            codes = self.mimi.encode(in_pcms)
            
            # Process through language model
            # The LMGen handles the decoding process
            out = self.lm_gen.generate(
                codes,
                max_new_tokens=1024,  # Reasonable limit for transcription
            )
            
            # Decode the text tokens
            text_tokens = out.text_codes.squeeze(0).cpu().numpy()
            text = self.text_tokenizer.decode(text_tokens.tolist())
            
            return text.strip()


class KyutaiASRProcessor:
    """Processes audio using Kyutai Mimi model for speech-to-text."""

    def __init__(self):
        self.mimi: Optional[MimiModel] = None
        self.text_tokenizer: Optional[sentencepiece.SentencePieceProcessor] = None
        self.lm: Optional[LMModel] = None
        self.device = settings.model_device
        logger.info(
            "Initializing Kyutai ASR processor", 
            device=self.device, 
            model=settings.model_name
        )

    async def initialize(self):
        """Initialize the Kyutai models following the Colab example."""
        try:
            logger.info("Loading Kyutai models", model=settings.model_name)
            
            # Load checkpoint info from HuggingFace
            checkpoint_info = loaders.CheckpointInfo.from_hf_repo(settings.model_name)
            
            # Initialize models
            self.mimi = checkpoint_info.get_mimi(device=self.device)
            self.text_tokenizer = checkpoint_info.get_text_tokenizer()
            self.lm = checkpoint_info.get_moshi(device=self.device)
            
            # Set models to eval mode
            self.mimi.eval()
            self.lm.eval()
            
            logger.info(
                f"Kyutai ASR processor initialized successfully on {self.device}",
                sample_rate=self.mimi.sample_rate
            )

        except Exception as e:
            logger.error("Failed to initialize Kyutai ASR processor", error=str(e))
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

            # Resample to Mimi's expected sample rate (24kHz)
            if sample_rate != self.mimi.sample_rate:
                resampler = torchaudio.transforms.Resample(
                    sample_rate, self.mimi.sample_rate
                )
                audio_tensor = resampler(audio_tensor)
                sample_rate = self.mimi.sample_rate

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
                confidence=0.95,  # High confidence for Kyutai model
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

            # Convert numpy array to torch tensor
            in_pcms = torch.from_numpy(audio_array).float()
            
            # Create inference state
            state = InferenceState(
                mimi=self.mimi,
                text_tokenizer=self.text_tokenizer,
                lm=self.lm,
                batch_size=settings.batch_size,
                device=self.device
            )
            
            # Run transcription
            transcribed_text = state.run(in_pcms)
            
            if not transcribed_text:
                logger.warning("No text transcribed", chunk_id=chunk.get_chunk_id())
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
                "Raw audio chunk transcribed",
                chunk_id=chunk.get_chunk_id(),
                device_id=chunk.device_id,
                word_count=len(words),
                text_length=len(transcribed_text),
                text_preview=transcribed_text[:100] + '...' if len(transcribed_text) > 100 else transcribed_text,
                processing_time_ms=processing_time_ms,
                input_duration_ms=chunk.get_duration_ms(),
                device=self.device,
                model=settings.model_name,
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