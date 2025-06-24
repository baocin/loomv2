"""Nomic Embed Vision processor for text and image embeddings."""

import asyncio
import base64
import io
import time
from typing import List, Optional, Union, Dict, Any
import gc

import numpy as np
import structlog
import torch
from PIL import Image
from sentence_transformers import SentenceTransformer
from transformers import AutoModel, AutoTokenizer

from .config import settings

logger = structlog.get_logger(__name__)


class NomicEmbeddingProcessor:
    """Nomic Embed Vision processor for unified text and image embeddings."""

    def __init__(self):
        """Initialize the embedding processor."""
        self.model: Optional[SentenceTransformer] = None
        self.tokenizer: Optional[AutoTokenizer] = None
        self.device: str = "cpu"
        self.model_loaded: bool = False
        self.processing_stats = {
            "total_text_processed": 0,
            "total_images_processed": 0,
            "total_processing_time": 0.0,
            "start_time": time.time(),
        }

    async def initialize(self) -> None:
        """Initialize and load the embedding model."""
        logger.info("Initializing Nomic Embed Vision processor")
        
        try:
            # Determine device
            if settings.device == "auto":
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
            else:
                self.device = settings.device
            
            logger.info(f"Using device: {self.device}")
            
            # Load the model using sentence-transformers for easier multimodal handling
            logger.info(f"Loading model: {settings.model_name}")
            
            self.model = SentenceTransformer(
                settings.model_name,
                device=self.device,
                cache_folder=settings.model_cache_dir,
                trust_remote_code=settings.trust_remote_code,
            )
            
            # Test the model with a simple input
            test_embedding = await self._embed_text("test")
            logger.info(f"Model loaded successfully. Embedding dimension: {len(test_embedding)}")
            
            self.model_loaded = True
            
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            raise

    async def _embed_text(self, text: str) -> List[float]:
        """Generate embedding for text."""
        if not self.model_loaded or self.model is None:
            raise RuntimeError("Model not loaded")
        
        start_time = time.time()
        
        try:
            # Truncate text if too long
            if len(text) > settings.max_text_length:
                text = text[:settings.max_text_length]
                logger.warning(f"Text truncated to {settings.max_text_length} characters")
            
            # Generate embedding in a thread to avoid blocking
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None, self._sync_embed_text, text
            )
            
            processing_time = (time.time() - start_time) * 1000
            self.processing_stats["total_text_processed"] += 1
            self.processing_stats["total_processing_time"] += processing_time
            
            logger.debug(f"Text embedding generated in {processing_time:.2f}ms")
            return embedding.tolist()
            
        except Exception as e:
            logger.error(f"Failed to generate text embedding: {e}")
            raise

    def _sync_embed_text(self, text: str) -> np.ndarray:
        """Synchronous text embedding generation."""
        with torch.no_grad():
            embedding = self.model.encode(
                text, 
                convert_to_tensor=True,
                device=self.device,
                show_progress_bar=False
            )
            if isinstance(embedding, torch.Tensor):
                embedding = embedding.cpu().numpy()
            return embedding

    async def _embed_image(
        self, 
        image_data: str, 
        generate_description: bool = False
    ) -> tuple[List[float], Optional[str]]:
        """Generate embedding for image."""
        if not self.model_loaded or self.model is None:
            raise RuntimeError("Model not loaded")
        
        start_time = time.time()
        
        try:
            # Decode base64 image
            image_bytes = base64.b64decode(image_data)
            image = Image.open(io.BytesIO(image_bytes))
            
            # Convert to RGB if needed
            if image.mode != "RGB":
                image = image.convert("RGB")
            
            # Resize if too large
            if max(image.size) > settings.max_image_size:
                ratio = settings.max_image_size / max(image.size)
                new_size = tuple(int(dim * ratio) for dim in image.size)
                image = image.resize(new_size, Image.Resampling.LANCZOS)
                logger.debug(f"Image resized to {new_size}")
            
            # Generate embedding in a thread
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None, self._sync_embed_image, image
            )
            
            # Generate description if requested
            description = None
            if generate_description:
                description = await self._generate_image_description(image)
            
            processing_time = (time.time() - start_time) * 1000
            self.processing_stats["total_images_processed"] += 1
            self.processing_stats["total_processing_time"] += processing_time
            
            logger.debug(f"Image embedding generated in {processing_time:.2f}ms")
            return embedding.tolist(), description
            
        except Exception as e:
            logger.error(f"Failed to generate image embedding: {e}")
            raise

    def _sync_embed_image(self, image: Image.Image) -> np.ndarray:
        """Synchronous image embedding generation."""
        with torch.no_grad():
            embedding = self.model.encode(
                image,
                convert_to_tensor=True,
                device=self.device,
                show_progress_bar=False
            )
            if isinstance(embedding, torch.Tensor):
                embedding = embedding.cpu().numpy()
            return embedding

    async def _generate_image_description(self, image: Image.Image) -> str:
        """Generate a text description of the image."""
        # For now, return a placeholder. This would require a vision-language model
        # like BLIP or similar for actual image captioning
        return "Image description not implemented yet"

    async def embed_batch_text(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts."""
        if not self.model_loaded or self.model is None:
            raise RuntimeError("Model not loaded")
        
        start_time = time.time()
        
        try:
            # Truncate texts if needed
            processed_texts = []
            for text in texts:
                if len(text) > settings.max_text_length:
                    processed_texts.append(text[:settings.max_text_length])
                else:
                    processed_texts.append(text)
            
            # Generate embeddings in batches
            batch_size = min(len(processed_texts), settings.max_batch_size)
            all_embeddings = []
            
            for i in range(0, len(processed_texts), batch_size):
                batch = processed_texts[i:i + batch_size]
                
                loop = asyncio.get_event_loop()
                batch_embeddings = await loop.run_in_executor(
                    None, self._sync_embed_batch_text, batch
                )
                all_embeddings.extend(batch_embeddings)
            
            processing_time = (time.time() - start_time) * 1000
            self.processing_stats["total_text_processed"] += len(texts)
            self.processing_stats["total_processing_time"] += processing_time
            
            logger.debug(f"Batch text embeddings generated in {processing_time:.2f}ms")
            return all_embeddings
            
        except Exception as e:
            logger.error(f"Failed to generate batch text embeddings: {e}")
            raise

    def _sync_embed_batch_text(self, texts: List[str]) -> List[List[float]]:
        """Synchronous batch text embedding generation."""
        with torch.no_grad():
            embeddings = self.model.encode(
                texts,
                convert_to_tensor=True,
                device=self.device,
                show_progress_bar=False,
                batch_size=min(len(texts), settings.max_batch_size)
            )
            if isinstance(embeddings, torch.Tensor):
                embeddings = embeddings.cpu().numpy()
            return embeddings.tolist()

    async def process_message(
        self, 
        message_data: Dict[str, Any], 
        source_topic: str
    ) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]:
        """Process a message and generate embeddings."""
        try:
            results = []
            
            # Check if message contains text
            text_fields = ["content", "text", "text_content", "transcribed_text", "note_content"]
            for field in text_fields:
                if field in message_data and message_data[field]:
                    text_embedding = await self._embed_text(message_data[field])
                    
                    result = {
                        "text_content": message_data[field],
                        "text_length": len(message_data[field]),
                        "embedding": text_embedding,
                        "embedding_model": settings.model_name,
                        "embedding_dimension": len(text_embedding),
                        "source_topic": source_topic,
                        "source_message_id": message_data.get("message_id", "unknown"),
                        "device_id": message_data.get("device_id", "unknown"),
                        "recorded_at": message_data.get("recorded_at"),
                        "metadata": {k: v for k, v in message_data.items() if k not in ["content", "text", "chunk_data", "image_data"]}
                    }
                    results.append(("text", result))
            
            # Check if message contains image data
            image_fields = ["image_data", "chunk_data"]  # chunk_data for audio, but we skip that
            for field in image_fields:
                if field in message_data and message_data[field] and field == "image_data":
                    image_embedding, description = await self._embed_image(
                        message_data[field], 
                        generate_description=True
                    )
                    
                    result = {
                        "image_format": message_data.get("format", "unknown"),
                        "image_width": message_data.get("width", 0),
                        "image_height": message_data.get("height", 0),
                        "image_size_bytes": message_data.get("file_size", 0),
                        "embedding": image_embedding,
                        "embedding_model": settings.model_name,
                        "embedding_dimension": len(image_embedding),
                        "source_topic": source_topic,
                        "source_message_id": message_data.get("message_id", "unknown"),
                        "device_id": message_data.get("device_id", "unknown"),
                        "recorded_at": message_data.get("recorded_at"),
                        "image_description": description,
                        "metadata": {k: v for k, v in message_data.items() if k not in ["image_data", "chunk_data"]}
                    }
                    results.append(("image", result))
            
            return results if results else None
            
        except Exception as e:
            logger.error(f"Failed to process message: {e}")
            return None

    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        uptime = time.time() - self.processing_stats["start_time"]
        total_processed = (
            self.processing_stats["total_text_processed"] + 
            self.processing_stats["total_images_processed"]
        )
        
        avg_processing_time = 0.0
        if total_processed > 0:
            avg_processing_time = self.processing_stats["total_processing_time"] / total_processed
        
        memory_usage = 0.0
        if torch.cuda.is_available() and self.device == "cuda":
            memory_usage = torch.cuda.memory_allocated() / 1024 / 1024  # MB
        
        return {
            "total_text_processed": self.processing_stats["total_text_processed"],
            "total_images_processed": self.processing_stats["total_images_processed"],
            "average_processing_time_ms": avg_processing_time,
            "model_memory_usage_mb": memory_usage,
            "uptime_seconds": uptime,
            "device": self.device,
            "model_loaded": self.model_loaded,
        }

    async def cleanup(self) -> None:
        """Clean up resources."""
        logger.info("Cleaning up embedding processor")
        
        if self.model is not None:
            del self.model
            self.model = None
        
        if self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        gc.collect()
        self.model_loaded = False