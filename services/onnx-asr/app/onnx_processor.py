"""ONNX-based ASR processor using nemo-parakeet-tdt-0.6b-v2."""

import asyncio
import base64
import io
import time
from typing import List, Optional

import numpy as np
import soundfile as sf
import structlog
import torch
import torchaudio
from pydub import AudioSegment

from app.config import settings
from app.models import AudioChunk, Transcript, Word

logger = structlog.get_logger()


class ONNXASRProcessor:
    """ONNX-based ASR processor using nemo-parakeet-tdt-0.6b-v2."""

    def __init__(self):
        """Initialize processor without loading model."""
        self.model = None
        self.processor = None
        self.tokenizer = None
        self.device = settings.model_device
        self.sample_rate = settings.target_sample_rate
        self.initialized = False

        # Batching
        self.batch_queue = []
        self.batch_lock = asyncio.Lock()

        logger.info(
            "ONNXASRProcessor initialized",
            device=self.device,
            sample_rate=self.sample_rate,
            batch_size=settings.batch_size,
        )

    async def initialize(self):
        """Load the ONNX model and required components."""
        if self.initialized:
            logger.info("Model already initialized")
            return

        try:
            logger.info("Loading ONNX ASR model", model=settings.model_name)

            # Import ONNX ASR components
            try:
                from onnx_asr import load_asr_model
            except ImportError:
                # Fallback: try direct model loading
                import onnxruntime as ort
                from huggingface_hub import hf_hub_download

                # Download model from HuggingFace
                model_path = hf_hub_download(
                    repo_id="nvidia/parakeet-tdt-0.6b",
                    filename="model.onnx",
                    cache_dir="/tmp/cache",  # nosec
                )

                # Create ONNX runtime session
                providers = (
                    ["CUDAExecutionProvider"]
                    if self.device == "cuda"
                    else ["CPUExecutionProvider"]
                )
                self.model = ort.InferenceSession(model_path, providers=providers)

                # Load tokenizer
                from transformers import AutoTokenizer

                self.tokenizer = AutoTokenizer.from_pretrained(
                    "nvidia/parakeet-tdt-0.6b"
                )

                logger.info("Loaded model using direct ONNX runtime")
            else:
                # Use onnx-asr library
                self.model = load_asr_model(
                    "nvidia/parakeet-tdt-0.6b", device=self.device
                )
                logger.info("Loaded model using onnx-asr library")

            self.initialized = True
            logger.info("ONNX ASR model loaded successfully")

        except Exception as e:
            logger.error("Failed to load ONNX ASR model", error=str(e))
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

    def _run_inference(self, audio_array: np.ndarray) -> tuple[str, List[dict]]:
        """Run ONNX inference on audio array."""
        try:
            if hasattr(self, "model") and hasattr(self.model, "transcribe"):
                # Using onnx-asr library
                result = self.model.transcribe(audio_array)
                if isinstance(result, dict):
                    text = result.get("text", "")
                    words = result.get("words", [])
                else:
                    text = str(result)
                    words = []
            else:
                # Direct ONNX runtime inference
                # Prepare input
                audio_tensor = torch.from_numpy(audio_array).float()
                if audio_tensor.dim() == 1:
                    audio_tensor = audio_tensor.unsqueeze(0)

                # Get model input name
                input_name = self.model.get_inputs()[0].name

                # Run inference
                outputs = self.model.run(None, {input_name: audio_tensor.numpy()})

                # Decode output (assuming CTC or similar)
                logits = outputs[0]
                predicted_ids = np.argmax(logits, axis=-1)

                # Decode tokens to text
                if self.tokenizer:
                    text = self.tokenizer.decode(
                        predicted_ids[0], skip_special_tokens=True
                    )
                else:
                    # Fallback: simple character-based decoding
                    text = "".join(
                        [chr(i + ord("a")) for i in predicted_ids[0] if i < 26]
                    )

                # Simple word extraction (split by spaces)
                words = []
                if text:
                    word_list = text.split()
                    time_per_word = (
                        len(audio_array) / self.sample_rate / max(len(word_list), 1)
                    )
                    for i, word in enumerate(word_list):
                        words.append(
                            {
                                "word": word,
                                "start": i * time_per_word,
                                "end": (i + 1) * time_per_word,
                            }
                        )

            return text, words

        except Exception as e:
            logger.error("Inference failed", error=str(e))
            raise

    async def process_audio_chunk(self, chunk: AudioChunk) -> Optional[Transcript]:
        """Process a single audio chunk."""
        if not self.initialized:
            await self.initialize()

        start_time = time.time()

        try:
            # Decode audio
            audio_array = self._decode_audio(chunk.audio_data, chunk.format)

            # Check audio length
            duration = len(audio_array) / self.sample_rate
            if duration > settings.max_audio_length_seconds:
                logger.warning(
                    "Audio too long, truncating",
                    duration=duration,
                    max_duration=settings.max_audio_length_seconds,
                )
                max_samples = int(settings.max_audio_length_seconds * self.sample_rate)
                audio_array = audio_array[:max_samples]

            # Run inference
            text, word_data = self._run_inference(audio_array)

            # Skip empty transcriptions
            if not text or not text.strip():
                logger.debug("Empty transcription, skipping")
                return None

            # Create word objects
            words = []
            for w in word_data:
                words.append(
                    Word(
                        word=w["word"],
                        start_time=w.get("start", 0.0),
                        end_time=w.get("end", 0.0),
                        confidence=w.get("confidence", 1.0),
                    )
                )

            # Calculate processing time
            processing_time_ms = (time.time() - start_time) * 1000

            # Create transcript
            transcript = Transcript(
                device_id=chunk.device_id,
                text=text,
                words=words,
                audio_chunk_id=f"{chunk.file_id}_{chunk.chunk_number}",
                processing_time_ms=processing_time_ms,
                model_name=settings.model_name,
            )

            logger.info(
                "Transcription completed",
                device_id=chunk.device_id,
                text_length=len(text),
                num_words=len(words),
                processing_time_ms=processing_time_ms,
            )

            return transcript

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
    ) -> List[Optional[Transcript]]:
        """Process a batch of audio chunks."""
        if not chunks:
            return []

        logger.info(f"Processing batch of {len(chunks)} audio chunks")

        # Process chunks concurrently
        tasks = [self.process_audio_chunk(chunk) for chunk in chunks]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle results
        transcripts = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "Batch processing failed for chunk",
                    error=str(result),
                    index=i,
                    device_id=chunks[i].device_id if i < len(chunks) else "unknown",
                )
                transcripts.append(None)
            else:
                transcripts.append(result)

        return transcripts
