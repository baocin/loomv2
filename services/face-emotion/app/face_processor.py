"""Face emotion recognition using Laion Empathic-Insight-Face."""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
import structlog
import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModelForImageClassification, pipeline

from app.config import settings
from app.models import (
    FaceBoundingBox,
    FaceEmotionAnalysis,
    FacialLandmarks,
    VisionAnnotation,
)

logger = structlog.get_logger(__name__)


class FaceEmotionProcessor:
    """Face emotion recognition using Empathic-Insight-Face model."""

    def __init__(self):
        self.model = None
        self.processor = None
        self.pipeline = None
        self.face_cascade = None
        self.device = settings.model_device
        self.executor = ThreadPoolExecutor(
            max_workers=settings.max_concurrent_processes
        )
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the face emotion recognition model."""
        if self._initialized:
            return

        try:
            logger.info(
                "Loading face emotion model",
                model_name=settings.model_name,
                device=self.device,
            )

            # Load model in thread pool to avoid blocking
            await asyncio.get_event_loop().run_in_executor(
                self.executor, self._load_model
            )

            self._initialized = True
            logger.info("Face emotion processor initialized successfully")

        except Exception as e:
            logger.error("Failed to initialize face emotion processor", error=str(e))
            raise

    def _load_model(self) -> None:
        """Load the Empathic-Insight-Face model and components."""
        try:
            # Load model components with cache_dir for detailed analysis
            self.processor = AutoImageProcessor.from_pretrained(
                settings.model_name, cache_dir=settings.model_cache_dir
            )

            self.model = AutoModelForImageClassification.from_pretrained(
                settings.model_name, cache_dir=settings.model_cache_dir
            )

            # Create image classification pipeline using the loaded model
            # Note: pipeline doesn't accept cache_dir, but will use the already cached model
            self.pipeline = pipeline(
                "image-classification",
                model=self.model,
                image_processor=self.processor,
                device=0 if self.device == "cuda" and torch.cuda.is_available() else -1,
            )

            # Move to device if available
            if self.device == "cuda" and torch.cuda.is_available():
                self.model = self.model.cuda()
                self.device = "cuda"
                logger.info("Model loaded on GPU")
            else:
                self.device = "cpu"
                logger.info("Model loaded on CPU")

            # Load OpenCV face cascade for face detection fallback
            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )

            logger.info("Face emotion model loaded successfully")

        except Exception as e:
            logger.error("Failed to load face emotion model", error=str(e))
            raise

    async def process_vision_annotation(
        self, annotation: VisionAnnotation
    ) -> Optional[List[FaceEmotionAnalysis]]:
        """Process vision annotation for face emotion recognition."""
        if not self._initialized:
            await self.initialize()

        # Only process annotations that contain faces or people
        if not self._contains_faces(annotation):
            logger.debug(
                "Annotation does not contain faces, skipping",
                device_id=annotation.device_id,
                object_class=annotation.object_class,
            )
            return None

        # Process in thread pool to avoid blocking
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, self._process_annotation_sync, annotation
        )

    def _contains_faces(self, annotation: VisionAnnotation) -> bool:
        """Check if annotation likely contains faces."""
        face_classes = ["person", "face", "human", "people"]
        return any(
            face_class in annotation.object_class.lower() for face_class in face_classes
        )

    def _process_annotation_sync(
        self, annotation: VisionAnnotation
    ) -> Optional[List[FaceEmotionAnalysis]]:
        """Synchronous face emotion processing."""
        start_time = time.time()

        try:
            logger.debug(
                "Processing annotation for face emotion",
                device_id=annotation.device_id,
                annotation_id=annotation.annotation_id,
                object_class=annotation.object_class,
            )

            # Extract image from annotation (this is a placeholder - actual implementation
            # would need to get the original image data, possibly from metadata or
            # by reconstructing from the vision processing pipeline)
            image = self._extract_image_from_annotation(annotation)
            if image is None:
                logger.warning(
                    "Could not extract image from annotation",
                    annotation_id=annotation.annotation_id,
                )
                return None

            # Detect faces in the image
            faces = self._detect_faces(image, annotation.bounding_box)

            if not faces:
                logger.debug(
                    "No faces detected in annotation",
                    annotation_id=annotation.annotation_id,
                )
                return None

            # Process emotion for each detected face
            results = []
            for i, face_info in enumerate(faces):
                face_image, face_bbox, landmarks = face_info

                # Analyze emotion for this face
                emotion_result = self._analyze_face_emotion(face_image)
                if emotion_result is None:
                    continue

                # Calculate processing time
                processing_time_ms = (time.time() - start_time) * 1000

                # Create face emotion analysis
                face_analysis = FaceEmotionAnalysis(
                    device_id=annotation.device_id,
                    timestamp=annotation.timestamp,
                    message_id=annotation.message_id,
                    face_id=f"{annotation.annotation_id}_face_{i}",
                    emotion_label=emotion_result["emotion"],
                    confidence_score=emotion_result["confidence"],
                    face_bounding_box=face_bbox,
                    facial_landmarks=landmarks,
                    emotion_intensities=emotion_result["all_emotions"],
                    face_quality_score=emotion_result.get("quality_score"),
                    face_size_pixels=int(face_bbox.width * face_bbox.height),
                    processing_duration_ms=processing_time_ms,
                    model_version=settings.model_name,
                    source_annotation_id=annotation.annotation_id,
                    source_object_class=annotation.object_class,
                    source_bounding_box=annotation.bounding_box,
                    metadata={
                        **annotation.metadata,
                        "face_index": i,
                        "total_faces": len(faces),
                    },
                )

                results.append(face_analysis)

                logger.info(
                    "Face emotion analysis completed",
                    device_id=annotation.device_id,
                    face_id=face_analysis.face_id,
                    predicted_emotion=face_analysis.emotion_label,
                    confidence=face_analysis.confidence_score,
                )

            return results if results else None

        except Exception as e:
            logger.error(
                "Error processing face emotion",
                device_id=annotation.device_id,
                annotation_id=annotation.annotation_id,
                error=str(e),
            )
            return None

    def _extract_image_from_annotation(
        self, annotation: VisionAnnotation
    ) -> Optional[np.ndarray]:
        """Extract image data from vision annotation.

        Note: This is a placeholder implementation. In practice, we would need
        to either:
        1. Store the original image data in the annotation metadata
        2. Reconstruct the image from the vision processing pipeline
        3. Access the original image from a shared storage location
        """
        # For now, return None to indicate image extraction is not implemented
        logger.warning(
            "Image extraction not implemented - using placeholder",
            annotation_id=annotation.annotation_id,
        )

        # Placeholder: create a dummy image for testing
        # In production, this would extract the actual image
        if annotation.image_width and annotation.image_height:
            dummy_image = np.zeros(
                (annotation.image_height, annotation.image_width, 3), dtype=np.uint8
            )
            return dummy_image

        return None

    def _detect_faces(
        self, image: np.ndarray, annotation_bbox: Optional[Dict[str, float]] = None
    ) -> List[Tuple[np.ndarray, FaceBoundingBox, Optional[FacialLandmarks]]]:
        """Detect faces in the image using OpenCV."""
        try:
            # Convert to grayscale for face detection
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

            # Detect faces
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(settings.min_face_size, settings.min_face_size),
                flags=cv2.CASCADE_SCALE_IMAGE,
            )

            results = []
            for i, (x, y, w, h) in enumerate(faces[: settings.max_faces_per_image]):
                # Extract face region
                face_image = image[y : y + h, x : x + w]

                # Create bounding box
                face_bbox = FaceBoundingBox(
                    x=float(x),
                    y=float(y),
                    width=float(w),
                    height=float(h),
                    confidence=settings.face_detection_confidence,
                )

                # Extract simple landmarks (placeholder)
                landmarks = self._extract_facial_landmarks(face_image, x, y, w, h)

                results.append((face_image, face_bbox, landmarks))

            return results

        except Exception as e:
            logger.error("Failed to detect faces", error=str(e))
            return []

    def _extract_facial_landmarks(
        self, face_image: np.ndarray, x: int, y: int, w: int, h: int
    ) -> Optional[FacialLandmarks]:
        """Extract facial landmarks (simplified implementation)."""
        try:
            # Simplified landmark estimation based on face geometry
            # In production, this would use a proper landmark detection model
            landmarks = FacialLandmarks(
                left_eye={"x": x + w * 0.35, "y": y + h * 0.35},
                right_eye={"x": x + w * 0.65, "y": y + h * 0.35},
                nose={"x": x + w * 0.5, "y": y + h * 0.5},
                mouth={"x": x + w * 0.5, "y": y + h * 0.7},
            )
            return landmarks

        except Exception as e:
            logger.error("Failed to extract facial landmarks", error=str(e))
            return None

    def _analyze_face_emotion(self, face_image: np.ndarray) -> Optional[Dict[str, Any]]:
        """Analyze emotion for a single face."""
        try:
            # Convert numpy array to PIL Image
            if face_image.dtype != np.uint8:
                face_image = (face_image * 255).astype(np.uint8)

            pil_image = Image.fromarray(face_image)

            # Resize if necessary
            if max(pil_image.size) > settings.max_image_size:
                pil_image.thumbnail((settings.max_image_size, settings.max_image_size))

            # Process through emotion model
            emotion_results = self.pipeline(pil_image)

            if not emotion_results:
                return None

            # Get primary emotion
            primary_emotion = emotion_results[0]
            predicted_emotion = primary_emotion["label"]
            confidence_score = primary_emotion["score"]

            # Build emotion probabilities dict
            all_emotions = {
                result["label"]: result["score"] for result in emotion_results
            }

            # Calculate quality score (simplified)
            quality_score = min(
                confidence_score * 1.2, 1.0
            )  # Boost confidence slightly

            return {
                "emotion": predicted_emotion,
                "confidence": confidence_score,
                "all_emotions": all_emotions,
                "quality_score": quality_score,
            }

        except Exception as e:
            logger.error("Failed to analyze face emotion", error=str(e))
            return None

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.executor.shutdown(wait=True)
        self._initialized = False
        logger.info("Face emotion processor cleaned up")
