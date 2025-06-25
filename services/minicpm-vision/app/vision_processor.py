"""Vision processing logic using MiniCPM-Llama3-V 2.5."""

import base64
import time
from io import BytesIO
from typing import Any, Dict, Optional

import outlines
import structlog
import torch
from PIL import Image
from transformers import AutoModel, AutoTokenizer

from app.models import (
    DetectedObject,
    OCRResult,
    VisionAnalysisResult,
)
from app.schemas import (
    OCR_ANALYSIS_PROMPT,
    SCENE_ANALYSIS_PROMPT,
    StructuredOCRAnalysis,
    StructuredSceneAnalysis,
)

logger = structlog.get_logger()


class VisionProcessor:
    """Processes images using MiniCPM-Llama3-V 2.5 model."""

    def __init__(self, device: Optional[str] = None):
        """Initialize the vision processor.

        Args:
            device: Device to run on ('cuda', 'cpu', or None for auto-detect)
        """
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.tokenizer = None
        self.model_loaded = False

        logger.info(
            "Initializing VisionProcessor",
            device=self.device,
            cuda_available=torch.cuda.is_available(),
        )

    async def load_model(self) -> None:
        """Load the MiniCPM-V model and tokenizer."""
        if self.model_loaded:
            return

        try:
            logger.info("Loading MiniCPM-Llama3-V-2.5 model...")

            # Load tokenizer and model
            self.tokenizer = AutoTokenizer.from_pretrained(
                "openbmb/MiniCPM-Llama3-V-2_5",
                trust_remote_code=True,
            )

            self.model = AutoModel.from_pretrained(
                "openbmb/MiniCPM-Llama3-V-2_5",
                trust_remote_code=True,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map=self.device,
            )

            self.model.eval()
            self.model_loaded = True

            logger.info(
                "Model loaded successfully",
                device=self.device,
                model_class=type(self.model).__name__,
            )

        except Exception as e:
            logger.error("Failed to load model", error=str(e))
            raise

    def _decode_image(self, base64_data: str) -> Image.Image:
        """Decode base64 image data to PIL Image.

        Args:
            base64_data: Base64 encoded image string

        Returns:
            PIL Image object
        """
        try:
            # Remove data URL prefix if present
            if "," in base64_data:
                base64_data = base64_data.split(",")[1]

            image_data = base64.b64decode(base64_data)
            image = Image.open(BytesIO(image_data))

            # Convert to RGB if necessary
            if image.mode not in ("RGB", "L"):
                image = image.convert("RGB")

            return image

        except Exception as e:
            logger.error("Failed to decode image", error=str(e))
            raise

    async def _generate_structured(
        self,
        image: Image.Image,
        prompt: str,
        schema: type,
        max_tokens: int = 1024,
    ) -> Any:
        """Generate structured output using the model with outlines.

        Args:
            image: PIL Image to analyze
            prompt: Prompt for the model
            schema: Pydantic schema for structured output
            max_tokens: Maximum tokens to generate

        Returns:
            Structured output matching the schema
        """
        try:
            # Prepare inputs
            inputs = self.tokenizer(
                [prompt],
                images=[image],
                return_tensors="pt",
            ).to(self.device)

            # Generate with outlines for structured output
            generator = outlines.generate.json(self.model, schema)

            with torch.no_grad():
                output = generator(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=0.7,
                    do_sample=True,
                )

            return output

        except Exception as e:
            logger.error(
                "Failed to generate structured output",
                error=str(e),
                prompt_length=len(prompt),
            )
            # Fallback to unstructured generation
            return await self._generate_unstructured(image, prompt, max_tokens)

    async def _generate_unstructured(
        self,
        image: Image.Image,
        prompt: str,
        max_tokens: int = 1024,
    ) -> str:
        """Generate unstructured text output.

        Args:
            image: PIL Image to analyze
            prompt: Prompt for the model
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text
        """
        inputs = self.tokenizer(
            [prompt],
            images=[image],
            return_tensors="pt",
        ).to(self.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=0.7,
                do_sample=True,
            )

        response = self.tokenizer.decode(
            outputs[0][inputs.input_ids.shape[1] :],
            skip_special_tokens=True,
        )

        return response

    async def analyze_image(
        self,
        base64_image: str,
        device_id: str,
        recorded_at: str,
    ) -> VisionAnalysisResult:
        """Analyze an image and return structured results.

        Args:
            base64_image: Base64 encoded image
            device_id: Device ID that captured the image
            recorded_at: Timestamp when image was captured

        Returns:
            VisionAnalysisResult with comprehensive analysis
        """
        start_time = time.time()

        try:
            # Ensure model is loaded
            await self.load_model()

            # Decode image
            image = self._decode_image(base64_image)

            logger.info(
                "Processing image",
                device_id=device_id,
                image_size=image.size,
                image_mode=image.mode,
            )

            # Perform scene analysis
            scene_result = await self._generate_structured(
                image,
                SCENE_ANALYSIS_PROMPT,
                StructuredSceneAnalysis,
            )

            # Perform OCR analysis
            ocr_result = await self._generate_structured(
                image,
                OCR_ANALYSIS_PROMPT,
                StructuredOCRAnalysis,
            )

            # Convert to output format
            detected_objects = [
                DetectedObject(
                    label=obj.get("label", "unknown"),
                    confidence=obj.get("confidence", 0.0),
                )
                for obj in scene_result.objects
            ]

            ocr_results = [
                OCRResult(
                    text=block.get("text", ""),
                    confidence=block.get("confidence", 0.0),
                )
                for block in ocr_result.text_blocks
            ]

            processing_time = (time.time() - start_time) * 1000

            result = VisionAnalysisResult(
                device_id=device_id,
                recorded_at=recorded_at,
                scene_description=scene_result.description,
                scene_categories=scene_result.categories,
                detected_objects=detected_objects,
                ocr_results=ocr_results,
                full_text=ocr_result.full_text if ocr_result.full_text else None,
                processing_time_ms=processing_time,
            )

            logger.info(
                "Image analysis completed",
                device_id=device_id,
                processing_time_ms=processing_time,
                num_objects=len(detected_objects),
                has_text=bool(ocr_result.full_text),
            )

            return result

        except Exception as e:
            logger.error(
                "Failed to analyze image",
                device_id=device_id,
                error=str(e),
                error_type=type(e).__name__,
            )

            # Return minimal result on error
            processing_time = (time.time() - start_time) * 1000
            return VisionAnalysisResult(
                device_id=device_id,
                recorded_at=recorded_at,
                scene_description=f"Error analyzing image: {str(e)}",
                scene_categories=[],
                detected_objects=[],
                ocr_results=[],
                processing_time_ms=processing_time,
            )

    async def answer_visual_question(
        self,
        base64_image: str,
        question: str,
    ) -> Dict[str, Any]:
        """Answer a specific question about an image.

        Args:
            base64_image: Base64 encoded image
            question: Question to answer about the image

        Returns:
            Dictionary with question, answer, and metadata
        """
        try:
            await self.load_model()
            image = self._decode_image(base64_image)

            prompt = f"Question: {question}\nAnswer:"
            answer = await self._generate_unstructured(image, prompt, max_tokens=256)

            return {
                "question": question,
                "answer": answer.strip(),
                "status": "success",
            }

        except Exception as e:
            logger.error(
                "Failed to answer visual question",
                question=question,
                error=str(e),
            )
            return {
                "question": question,
                "answer": f"Error: {str(e)}",
                "status": "error",
            }
