"""Audio emotion recognition using Laion BUD-E-Whisper."""

import asyncio
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional, Tuple

import librosa
import numpy as np
import structlog
import torch
from transformers import (
    AutoModelForAudioClassification,
    AutoProcessor,
    pipeline,
)

from app.config import settings
from app.models import AudioEmotionAnalysis, VADFilteredAudio

logger = structlog.get_logger(__name__)


class EmotionProcessor:
    """Audio emotion recognition using BUD-E-Whisper model."""

    def __init__(self):
        self.model = None
        self.processor = None
        self.pipeline = None
        self.device = settings.model_device
        self.executor = ThreadPoolExecutor(
            max_workers=settings.max_concurrent_processes
        )
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the emotion recognition model."""
        if self._initialized:
            return

        try:
            logger.info(
                "Loading BUD-E emotion model",
                model_name=settings.model_name,
                device=self.device,
            )

            # Load model in thread pool to avoid blocking
            await asyncio.get_event_loop().run_in_executor(
                self.executor, self._load_model
            )

            self._initialized = True
            logger.info("Emotion processor initialized successfully")

        except Exception as e:
            logger.error("Failed to initialize emotion processor", error=str(e))
            raise

    def _load_model(self) -> None:
        """Load the BUD-E model and processor."""
        try:
            # Create audio classification pipeline
            self.pipeline = pipeline(
                "audio-classification",
                model=settings.model_name,
                device=0 if self.device == "cuda" and torch.cuda.is_available() else -1,
                cache_dir=settings.model_cache_dir,
            )

            # Also load model components for detailed analysis
            self.processor = AutoProcessor.from_pretrained(
                settings.model_name, cache_dir=settings.model_cache_dir
            )

            self.model = AutoModelForAudioClassification.from_pretrained(
                settings.model_name, cache_dir=settings.model_cache_dir
            )

            # Move to device if available
            if self.device == "cuda" and torch.cuda.is_available():
                self.model = self.model.cuda()
                self.device = "cuda"
                logger.info("Model loaded on GPU")
            else:
                self.device = "cpu"
                logger.info("Model loaded on CPU")

            logger.info("BUD-E emotion model loaded successfully")

        except Exception as e:
            logger.error("Failed to load BUD-E model", error=str(e))
            raise

    async def process_audio(
        self, vad_audio: VADFilteredAudio
    ) -> Optional[AudioEmotionAnalysis]:
        """Process audio segment for emotion recognition."""
        if not self._initialized:
            await self.initialize()

        # Process in thread pool to avoid blocking
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, self._process_audio_sync, vad_audio
        )

    def _process_audio_sync(
        self, vad_audio: VADFilteredAudio
    ) -> Optional[AudioEmotionAnalysis]:
        """Synchronous audio emotion processing."""
        start_time = time.time()

        try:
            # Decode audio data
            audio_bytes = vad_audio.decode_audio()
            audio_array, sample_rate = self._load_audio_from_bytes(
                audio_bytes, vad_audio.sample_rate
            )

            logger.debug(
                "Processing audio for emotion",
                device_id=vad_audio.device_id,
                duration_ms=vad_audio.duration_ms,
                sample_rate=sample_rate,
            )

            # Extract emotion using pipeline
            emotion_results = self.pipeline(audio_array, sampling_rate=sample_rate)

            # Get detailed features and scores
            detailed_analysis = self._extract_detailed_features(
                audio_array, sample_rate
            )

            # Process results
            if not emotion_results:
                logger.warning("No emotion results", device_id=vad_audio.device_id)
                return None

            # Get primary emotion
            primary_emotion = emotion_results[0]
            predicted_emotion = primary_emotion["label"]
            confidence_score = primary_emotion["score"]

            # Build emotion probabilities dict
            emotion_probabilities = {
                result["label"]: result["score"] for result in emotion_results
            }

            # Calculate dimensional scores (simplified mapping)
            dimensional_scores = self._calculate_dimensional_scores(
                predicted_emotion, emotion_probabilities
            )

            # Calculate processing time
            processing_time_ms = (time.time() - start_time) * 1000

            # Create analysis result
            analysis = AudioEmotionAnalysis(
                device_id=vad_audio.device_id,
                timestamp=vad_audio.timestamp,
                message_id=vad_audio.message_id,
                segment_id=str(uuid.uuid4()),
                predicted_emotion=predicted_emotion,
                confidence_score=confidence_score,
                valence_score=dimensional_scores.get("valence"),
                arousal_score=dimensional_scores.get("arousal"),
                dominance_score=dimensional_scores.get("dominance"),
                emotion_probabilities=emotion_probabilities,
                audio_features=detailed_analysis,
                processing_duration_ms=processing_time_ms,
                model_version=settings.model_name,
                source_start_ms=vad_audio.speech_start_ms,
                source_end_ms=vad_audio.speech_end_ms,
                source_duration_ms=vad_audio.duration_ms,
                metadata={
                    **vad_audio.metadata,
                    "vad_confidence": vad_audio.vad_confidence,
                },
            )

            logger.info(
                "Audio emotion analysis completed",
                device_id=vad_audio.device_id,
                predicted_emotion=predicted_emotion,
                confidence=confidence_score,
                processing_time_ms=processing_time_ms,
            )

            return analysis

        except Exception as e:
            logger.error(
                "Error processing audio emotion",
                device_id=vad_audio.device_id,
                error=str(e),
            )
            return None

    def _load_audio_from_bytes(
        self, audio_bytes: bytes, sample_rate: int
    ) -> Tuple[np.ndarray, int]:
        """Load audio from bytes and prepare for processing."""
        try:
            # Convert bytes to numpy array (assuming 16-bit PCM)
            audio_array = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
            audio_array = audio_array / 32768.0  # Normalize to [-1, 1]

            # Resample if necessary
            if sample_rate != settings.target_sample_rate:
                audio_array = librosa.resample(
                    audio_array,
                    orig_sr=sample_rate,
                    target_sr=settings.target_sample_rate,
                )
                sample_rate = settings.target_sample_rate

            # Ensure audio is not too long
            max_samples = settings.max_audio_length_seconds * sample_rate
            if len(audio_array) > max_samples:
                audio_array = audio_array[:max_samples]

            return audio_array, sample_rate

        except Exception as e:
            logger.error("Failed to load audio from bytes", error=str(e))
            raise

    def _extract_detailed_features(
        self, audio_array: np.ndarray, sample_rate: int
    ) -> Dict[str, Any]:
        """Extract additional audio features for analysis."""
        try:
            features = {}

            # Basic audio statistics
            features["rms_energy"] = float(np.sqrt(np.mean(audio_array**2)))
            features["zero_crossing_rate"] = float(
                np.mean(librosa.feature.zero_crossing_rate(audio_array)[0])
            )

            # Spectral features
            spectral_centroids = librosa.feature.spectral_centroid(
                y=audio_array, sr=sample_rate
            )[0]
            features["spectral_centroid_mean"] = float(np.mean(spectral_centroids))
            features["spectral_centroid_std"] = float(np.std(spectral_centroids))

            # MFCC features (first 13 coefficients)
            mfccs = librosa.feature.mfcc(y=audio_array, sr=sample_rate, n_mfcc=13)
            features["mfcc_mean"] = mfccs.mean(axis=1).tolist()
            features["mfcc_std"] = mfccs.std(axis=1).tolist()

            # Tempo and rhythm
            try:
                tempo, _ = librosa.beat.beat_track(y=audio_array, sr=sample_rate)
                features["tempo"] = float(tempo)
            except Exception:
                features["tempo"] = None

            return features

        except Exception as e:
            logger.error("Failed to extract audio features", error=str(e))
            return {}

    def _calculate_dimensional_scores(
        self, predicted_emotion: str, emotion_probabilities: Dict[str, float]
    ) -> Dict[str, float]:
        """Calculate valence, arousal, and dominance scores from emotion predictions."""
        # Simplified emotion-to-dimension mapping
        # In practice, this could be more sophisticated
        emotion_dimensions = {
            "happiness": {"valence": 0.8, "arousal": 0.6, "dominance": 0.5},
            "joy": {"valence": 0.8, "arousal": 0.6, "dominance": 0.5},
            "excitement": {"valence": 0.7, "arousal": 0.9, "dominance": 0.6},
            "anger": {"valence": -0.7, "arousal": 0.8, "dominance": 0.7},
            "sadness": {"valence": -0.6, "arousal": -0.5, "dominance": -0.3},
            "fear": {"valence": -0.5, "arousal": 0.7, "dominance": -0.6},
            "disgust": {"valence": -0.6, "arousal": 0.2, "dominance": 0.2},
            "surprise": {"valence": 0.2, "arousal": 0.8, "dominance": 0.0},
            "neutral": {"valence": 0.0, "arousal": 0.0, "dominance": 0.0},
        }

        # Calculate weighted average of dimensional scores
        dimensions = {"valence": 0.0, "arousal": 0.0, "dominance": 0.0}

        total_weight = 0.0
        for emotion, probability in emotion_probabilities.items():
            if emotion.lower() in emotion_dimensions:
                emotion_dims = emotion_dimensions[emotion.lower()]
                weight = probability

                for dim in dimensions:
                    dimensions[dim] += emotion_dims[dim] * weight

                total_weight += weight

        # Normalize by total weight
        if total_weight > 0:
            for dim in dimensions:
                dimensions[dim] /= total_weight

        return dimensions

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.executor.shutdown(wait=True)
        self._initialized = False
        logger.info("Emotion processor cleaned up")
