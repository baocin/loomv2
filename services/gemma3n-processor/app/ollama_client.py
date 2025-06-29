"""Ollama client for Gemma 3N model interaction."""

import base64
import time
from io import BytesIO
from typing import Any, Dict, List, Optional

import httpx
import structlog
from PIL import Image

from .config import settings
from .models import MultimodalRequest

logger = structlog.get_logger()


class OllamaClient:
    """Client for interacting with Ollama server."""

    def __init__(self):
        self.base_url = settings.ollama_host
        self.model = settings.ollama_model
        self.timeout = settings.ollama_timeout
        self.keep_alive = settings.ollama_keep_alive

    async def _make_request(
        self, endpoint: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Make HTTP request to Ollama API."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/{endpoint}",
                    json=data,
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                return response.json()
            except httpx.RequestError as e:
                logger.error("Request error to Ollama", error=str(e))
                raise
            except httpx.HTTPStatusError as e:
                logger.error(
                    "HTTP error from Ollama",
                    status=e.response.status_code,
                    error=str(e),
                )
                raise

    async def health_check(self) -> bool:
        """Check if Ollama server is healthy."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception as e:
            logger.error("Ollama health check failed", error=str(e))
            return False

    async def list_models(self) -> List[str]:
        """List available models."""
        try:
            response = await self._make_request("api/tags", {})
            models = response.get("models", [])
            return [model["name"] for model in models]
        except Exception as e:
            logger.error("Failed to list models", error=str(e))
            return []

    async def pull_model(self, model_name: Optional[str] = None) -> bool:
        """Pull/download a model."""
        model = model_name or self.model
        try:
            data = {"name": model}
            await self._make_request("api/pull", data)
            logger.info("Model pulled successfully", model=model)
            return True
        except Exception as e:
            logger.error("Failed to pull model", model=model, error=str(e))
            return False

    def _prepare_image(self, image_data: str) -> str:
        """Prepare image data for Ollama (resize if needed)."""
        try:
            # Decode base64 image
            image_bytes = base64.b64decode(image_data)
            image = Image.open(BytesIO(image_bytes))

            # Resize if too large (Gemma 3N supports up to 768x768)
            max_size = settings.max_image_size
            if image.width > max_size or image.height > max_size:
                image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

                # Convert back to base64
                buffer = BytesIO()
                image.save(buffer, format="PNG")
                return base64.b64encode(buffer.getvalue()).decode()

            return image_data
        except Exception as e:
            logger.error("Failed to prepare image", error=str(e))
            raise

    async def generate_text(
        self,
        prompt: str,
        context: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """Generate text using Gemma 3N."""
        start_time = time.time()

        try:
            full_prompt = f"{context}\n{prompt}" if context else prompt

            data = {
                "model": self.model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens or settings.model_max_tokens,
                    "temperature": temperature or settings.model_temperature,
                    "top_p": settings.model_top_p,
                },
                "keep_alive": self.keep_alive,
            }

            response = await self._make_request("api/generate", data)

            processing_time = (time.time() - start_time) * 1000
            logger.info(
                "Text generation completed",
                processing_time_ms=processing_time,
                prompt_length=len(prompt),
            )

            return response.get("response", "")

        except Exception as e:
            logger.error("Text generation failed", error=str(e))
            raise

    async def analyze_image(
        self,
        image_data: str,
        prompt: str = "Describe this image in detail.",
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """Analyze image using Gemma 3N vision capabilities."""
        start_time = time.time()

        try:
            # Prepare image data
            processed_image = self._prepare_image(image_data)

            data = {
                "model": self.model,
                "prompt": prompt,
                "images": [processed_image],
                "stream": False,
                "options": {
                    "num_predict": max_tokens or settings.model_max_tokens,
                    "temperature": temperature or settings.model_temperature,
                    "top_p": settings.model_top_p,
                },
                "keep_alive": self.keep_alive,
            }

            response = await self._make_request("api/generate", data)

            processing_time = (time.time() - start_time) * 1000
            logger.info(
                "Image analysis completed",
                processing_time_ms=processing_time,
                prompt_length=len(prompt),
            )

            return response.get("response", "")

        except Exception as e:
            logger.error("Image analysis failed", error=str(e))
            raise

    async def process_multimodal(self, request: MultimodalRequest) -> str:
        """Process multimodal input (text + image + audio)."""
        start_time = time.time()

        try:
            # Build prompt based on available modalities
            full_prompt = request.prompt

            if request.text:
                full_prompt += f"\n\nText content: {request.text}"

            # Handle image if provided
            images = []
            if request.image_data:
                processed_image = self._prepare_image(request.image_data)
                images.append(processed_image)
                full_prompt += "\n\nImage provided for analysis."

            # Handle audio if provided (note: Gemma 3N may not directly support audio)
            if request.audio_data:
                # For now, mention audio is provided (future enhancement needed)
                full_prompt += "\n\nAudio data provided for analysis."

            data = {
                "model": self.model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "num_predict": request.max_tokens or settings.model_max_tokens,
                    "temperature": request.temperature or settings.model_temperature,
                    "top_p": settings.model_top_p,
                },
                "keep_alive": self.keep_alive,
            }

            if images:
                data["images"] = images

            response = await self._make_request("api/generate", data)

            processing_time = (time.time() - start_time) * 1000
            logger.info(
                "Multimodal processing completed",
                processing_time_ms=processing_time,
                has_text=bool(request.text),
                has_image=bool(request.image_data),
                has_audio=bool(request.audio_data),
            )

            return response.get("response", "")

        except Exception as e:
            logger.error("Multimodal processing failed", error=str(e))
            raise
