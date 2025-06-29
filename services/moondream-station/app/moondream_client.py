"""Client for interacting with Moondream Station API."""

import asyncio
import base64
import time
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

import httpx
import structlog
from PIL import Image

from .config import settings
from .models import (
    DetectedObject,
    ImageFeatures,
    MoondreamResponse,
    OCRBlock,
)

logger = structlog.get_logger()


class MoondreamClient:
    """Client for Moondream Station API interactions."""

    def __init__(self):
        self.base_url = f"{settings.moondream_host}{settings.moondream_api_path}"
        self.timeout = settings.moondream_timeout
        self.max_retries = settings.moondream_max_retries

    async def _make_request(
        self,
        endpoint: str,
        method: str = "POST",
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        retries: int = 0,
    ) -> Dict[str, Any]:
        """Make HTTP request to Moondream Station API with retry logic."""
        url = f"{self.base_url}/{endpoint}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if method == "GET":
                    response = await client.get(url)
                elif files:
                    response = await client.post(url, files=files, data=data)
                else:
                    response = await client.post(url, json=data)

                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 503 and retries < self.max_retries:
                # Service unavailable, retry
                logger.warning(
                    "Moondream Station unavailable, retrying",
                    attempt=retries + 1,
                    max_retries=self.max_retries,
                )
                await asyncio.sleep(2**retries)  # Exponential backoff
                return await self._make_request(
                    endpoint, method, data, files, retries + 1
                )
            logger.error(
                "HTTP error from Moondream Station",
                status=e.response.status_code,
                error=str(e),
            )
            raise

        except httpx.RequestError as e:
            if retries < self.max_retries:
                logger.warning(
                    "Request error, retrying", attempt=retries + 1, error=str(e)
                )
                await asyncio.sleep(2**retries)
                return await self._make_request(
                    endpoint, method, data, files, retries + 1
                )
            logger.error("Request error to Moondream Station", error=str(e))
            raise

    async def health_check(self) -> bool:
        """Check if Moondream Station is healthy."""
        try:
            response = await self._make_request("health", method="GET")
            return response.get("status") == "ok"
        except Exception as e:
            logger.error("Moondream Station health check failed", error=str(e))
            return False

    def _prepare_image(self, image_data: str) -> Tuple[bytes, str]:
        """Prepare image for Moondream Station API."""
        try:
            # Decode base64 image
            image_bytes = base64.b64decode(image_data)
            image = Image.open(BytesIO(image_bytes))

            # Resize if too large
            max_size = settings.max_image_size
            if image.width > max_size or image.height > max_size:
                image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

                # Convert back to bytes
                buffer = BytesIO()
                image_format = image.format or "JPEG"
                image.save(buffer, format=image_format, quality=settings.jpeg_quality)
                image_bytes = buffer.getvalue()

            # Determine format
            image_format = image.format or "JPEG"
            mime_type = f"image/{image_format.lower()}"

            return image_bytes, mime_type

        except Exception as e:
            logger.error("Failed to prepare image", error=str(e))
            raise

    async def caption_image(self, image_data: str) -> str:
        """Generate caption for an image."""
        start_time = time.time()

        try:
            image_bytes, mime_type = self._prepare_image(image_data)

            files = {"image": ("image.jpg", image_bytes, mime_type)}

            response = await self._make_request("caption", files=files)

            processing_time = (time.time() - start_time) * 1000
            logger.info("Image caption generated", processing_time_ms=processing_time)

            return response.get("caption", "")

        except Exception as e:
            logger.error("Image captioning failed", error=str(e))
            raise

    async def query_image(self, image_data: str, query: str) -> str:
        """Query an image with a specific question."""
        start_time = time.time()

        try:
            image_bytes, mime_type = self._prepare_image(image_data)

            files = {"image": ("image.jpg", image_bytes, mime_type)}
            data = {"query": query}

            response = await self._make_request("query", files=files, data=data)

            processing_time = (time.time() - start_time) * 1000
            logger.info(
                "Image query processed",
                processing_time_ms=processing_time,
                query_length=len(query),
            )

            return response.get("response", "")

        except Exception as e:
            logger.error("Image query failed", error=str(e))
            raise

    async def detect_objects(self, image_data: str) -> List[DetectedObject]:
        """Detect objects in an image."""
        # Query for object detection
        query = "List all objects you can see in this image with their locations."
        response = await self.query_image(image_data, query)

        # Parse response to extract objects
        # This is a simplified implementation - real parsing would be more sophisticated
        objects = []

        # Mock object detection based on caption
        # In production, this would parse actual Moondream response
        if "person" in response.lower():
            objects.append(
                DetectedObject(
                    label="person", confidence=0.85, bbox=[100, 100, 300, 400]
                )
            )

        if "car" in response.lower():
            objects.append(
                DetectedObject(label="car", confidence=0.9, bbox=[400, 200, 600, 350])
            )

        return objects

    async def extract_text(self, image_data: str) -> List[OCRBlock]:
        """Extract text from an image using OCR."""
        # Query for text extraction
        query = (
            "What text can you read in this image? Please list all text you can see."
        )
        response = await self.query_image(image_data, query)

        # Parse response to extract text blocks
        text_blocks = []

        # Mock OCR based on response
        # In production, this would parse actual Moondream response
        if response and len(response) > 10:
            # Split response into potential text blocks
            lines = response.split("\n")
            for i, line in enumerate(lines[:5]):  # Limit to 5 blocks
                if line.strip():
                    text_blocks.append(
                        OCRBlock(
                            text=line.strip(),
                            confidence=0.8,
                            bbox=[50, 50 + i * 30, 200, 80 + i * 30],
                        )
                    )

        return text_blocks

    async def analyze_visual_features(self, image_data: str) -> ImageFeatures:
        """Analyze visual features of an image."""
        # Query for visual features
        query = "Describe the visual characteristics: colors, brightness, quality, and composition."
        response = await self.query_image(image_data, query)

        # Extract features from response
        # This is a simplified implementation
        features = ImageFeatures(
            dominant_colors=["#FF5733", "#3366CC", "#FFFFFF"],  # Mock colors
            brightness=0.7,
            contrast=0.6,
            sharpness=0.8,
            aspect_ratio=1.5,
        )

        # Parse response for actual values if available
        if "bright" in response.lower():
            features.brightness = 0.8
        elif "dark" in response.lower():
            features.brightness = 0.3

        if "sharp" in response.lower():
            features.sharpness = 0.9
        elif "blurry" in response.lower():
            features.sharpness = 0.3

        return features

    async def full_analysis(
        self,
        image_data: str,
        query: Optional[str] = None,
        enable_objects: bool = True,
        enable_ocr: bool = True,
    ) -> MoondreamResponse:
        """Perform full analysis of an image."""
        start_time = time.time()

        try:
            # Generate caption
            caption = await self.caption_image(image_data)

            # Process query if provided
            query_response = None
            if query:
                query_response = await self.query_image(image_data, query)

            # Detect objects if enabled
            objects = []
            if enable_objects:
                detected_objects = await self.detect_objects(image_data)
                objects = [obj.model_dump() for obj in detected_objects]

            # Extract text if enabled
            text_blocks = []
            if enable_ocr:
                ocr_blocks = await self.extract_text(image_data)
                text_blocks = [block.model_dump() for block in ocr_blocks]

            processing_time = (time.time() - start_time) * 1000

            return MoondreamResponse(
                caption=caption,
                query_response=query_response,
                objects=objects,
                text_blocks=text_blocks,
                metadata={
                    "processing_time_ms": processing_time,
                    "features_enabled": {"objects": enable_objects, "ocr": enable_ocr},
                },
            )

        except Exception as e:
            logger.error("Full analysis failed", error=str(e))
            raise
