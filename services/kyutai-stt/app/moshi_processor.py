"""
Kyutai Moshi STT processor with streaming capabilities.
Based on the official Kyutai delayed-streams-modeling example.
"""

from dataclasses import dataclass
import time
from typing import Optional, List, Dict, Any
import numpy as np
import sentencepiece
import torch
import sphn
import structlog

from moshi.models import loaders, MimiModel, LMModel, LMGen

from app.models import AudioChunk, TranscribedWord

logger = structlog.get_logger()


@dataclass
class InferenceState:
    """State for streaming inference with Moshi models."""
    
    mimi: MimiModel
    text_tokenizer: sentencepiece.SentencePieceProcessor
    lm_gen: LMGen
    device: str | torch.device
    frame_size: int
    batch_size: int
    
    def __init__(
        self,
        mimi: MimiModel,
        text_tokenizer: sentencepiece.SentencePieceProcessor,
        lm: LMModel,
        batch_size: int = 1,
        device: str | torch.device = "cuda",
    ):
        self.mimi = mimi
        self.text_tokenizer = text_tokenizer
        self.lm_gen = LMGen(lm, temp=0, temp_text=0, use_sampling=False)
        self.device = device
        self.frame_size = int(self.mimi.sample_rate / self.mimi.frame_rate)
        self.batch_size = batch_size
        self.mimi.streaming_forever(batch_size)
        self.lm_gen.streaming_forever(batch_size)
        
    def process_chunk(self, audio_chunk: torch.Tensor) -> List[str]:
        """Process a single audio chunk and return transcribed tokens."""
        tokens_text = []
        
        # Split into frame-sized chunks
        chunks = [
            c for c in audio_chunk.split(self.frame_size, dim=-1)
            if c.shape[-1] == self.frame_size
        ]
        
        for chunk in chunks:
            # Encode audio to codes
            codes = self.mimi.encode(chunk.unsqueeze(0))
            
            # Generate text tokens
            tokens = self.lm_gen.step(codes)
            if tokens is None:
                continue
                
            assert tokens.shape[1] == 1
            token_id = tokens[0, 0].cpu().item()
            
            # Skip special tokens (0=PAD, 3=EOS)
            if token_id not in [0, 3]:
                text = self.text_tokenizer.id_to_piece(token_id)
                text = text.replace("▁", " ")
                tokens_text.append(text)
                
        return tokens_text


class MoshiProcessor:
    """Moshi-based STT processor with streaming support."""
    
    def __init__(self, model_name: str = "kyutai/stt-1b-en_fr", device: str = "cuda"):
        self.model_name = model_name
        self.device = device if torch.cuda.is_available() else "cpu"
        self.model_loaded = False
        
        # Model components
        self.checkpoint_info: Optional[loaders.CheckpointInfo] = None
        self.inference_state: Optional[InferenceState] = None
        self.stt_config: Optional[Dict[str, Any]] = None
        
        logger.info(
            "Initializing Moshi STT processor",
            model=model_name,
            device=self.device
        )
        
    def load_model(self):
        """Load Moshi models lazily on first use."""
        if self.model_loaded:
            return
            
        try:
            logger.info("Loading Moshi models from HuggingFace", model=self.model_name)
            
            # Load checkpoint info
            self.checkpoint_info = loaders.CheckpointInfo.from_hf_repo(self.model_name)
            
            # Load model components
            mimi = self.checkpoint_info.get_mimi(device=self.device)
            text_tokenizer = self.checkpoint_info.get_text_tokenizer()
            lm = self.checkpoint_info.get_moshi(device=self.device)
            
            # Get STT config for padding
            self.stt_config = self.checkpoint_info.stt_config
            
            # Initialize inference state
            self.inference_state = InferenceState(
                mimi=mimi,
                text_tokenizer=text_tokenizer,
                lm=lm,
                batch_size=1,
                device=self.device
            )
            
            self.model_loaded = True
            logger.info(
                "Moshi models loaded successfully",
                sample_rate=mimi.sample_rate,
                frame_rate=mimi.frame_rate,
                frame_size=self.inference_state.frame_size
            )
            
        except Exception as e:
            logger.error("Failed to load Moshi models", error=str(e))
            raise
            
    def process_audio_chunk(self, chunk: AudioChunk) -> List[TranscribedWord]:
        """Process an audio chunk and return transcribed words with timing."""
        if not self.model_loaded:
            self.load_model()
            
        start_time = time.time()
        
        try:
            # Convert base64 audio to numpy array
            audio_np = chunk.get_audio_array()
            
            # Convert to torch tensor
            audio_tensor = torch.from_numpy(audio_np).to(self.device)
            
            # Apply STT padding configuration
            pad_left = int(self.stt_config.get("audio_silence_prefix_seconds", 0.0) * self.inference_state.mimi.sample_rate)
            pad_right = int((self.stt_config.get("audio_delay_seconds", 0.0) + 1.0) * self.inference_state.mimi.sample_rate)
            
            if pad_left > 0 or pad_right > 0:
                audio_tensor = torch.nn.functional.pad(
                    audio_tensor, 
                    (pad_left, pad_right), 
                    mode="constant"
                )
            
            # Process through Moshi
            tokens = self.inference_state.process_chunk(audio_tensor)
            
            # Convert tokens to words with timing
            words = []
            if tokens:
                # Calculate timing based on token position
                chunk_duration_ms = chunk.get_duration_ms()
                time_per_token = chunk_duration_ms / max(len(tokens), 1)
                
                current_word = []
                word_start_time = 0.0
                
                for i, token in enumerate(tokens):
                    if token.strip():  # Non-whitespace token
                        if token.startswith(" ") and current_word:
                            # Complete previous word
                            word_text = "".join(current_word).strip()
                            if word_text:
                                words.append(TranscribedWord(
                                    word=word_text,
                                    start_time=word_start_time / 1000.0,  # Convert to seconds
                                    end_time=(i * time_per_token) / 1000.0,
                                    confidence=0.95  # Moshi doesn't provide confidence scores
                                ))
                            current_word = [token.lstrip()]
                            word_start_time = i * time_per_token
                        else:
                            current_word.append(token)
                
                # Handle last word
                if current_word:
                    word_text = "".join(current_word).strip()
                    if word_text:
                        words.append(TranscribedWord(
                            word=word_text,
                            start_time=word_start_time / 1000.0,
                            end_time=chunk_duration_ms / 1000.0,
                            confidence=0.95
                        ))
            
            processing_time_ms = (time.time() - start_time) * 1000
            realtime_factor = processing_time_ms / chunk.get_duration_ms() if chunk.get_duration_ms() > 0 else 0
            
            logger.info(
                "🎤 MOSHI TRANSCRIPTION COMPLETE",
                chunk_id=chunk.get_chunk_id(),
                device_id=chunk.device_id,
                word_count=len(words),
                token_count=len(tokens),
                processing_time_ms=round(processing_time_ms, 2),
                realtime_factor=round(realtime_factor, 2),
                transcribed_text=" ".join(w.word for w in words)
            )
            
            return words
            
        except Exception as e:
            logger.error(
                "Failed to process audio chunk",
                chunk_id=chunk.get_chunk_id(),
                error=str(e)
            )
            return []