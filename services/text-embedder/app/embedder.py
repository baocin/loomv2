"""Text embedding using sentence transformers."""

import os
import logging
from typing import List, Dict, Any

# Set the cache directory before importing sentence_transformers
os.environ["SENTENCE_TRANSFORMERS_HOME"] = "/home/appuser/.cache/sentence-transformers"
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class TextEmbedder:
    """Handles text embedding using sentence transformers."""

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        device: str = "cpu",
    ):
        """Initialize the embedder with specified model."""
        self.device = device
        self.model_name = model_name
        self.model = None

    async def load_model(self):
        """Load the sentence transformer model."""
        logger.info(
            f"Loading embedding model: {self.model_name} on device: {self.device}"
        )
        self.model = SentenceTransformer(self.model_name, device=self.device)
        logger.info(
            f"Model loaded successfully. Embedding dimension: {self.model.get_sentence_embedding_dimension()}"
        )

    def embed_text(self, text: str) -> List[float]:
        """Embed a single text."""
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Embed a batch of texts."""
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        embeddings = self.model.encode(
            texts, batch_size=batch_size, convert_to_numpy=True
        )
        return embeddings.tolist()

    def prepare_email_text(self, email_data: Dict[str, Any]) -> str:
        """Prepare email data for embedding."""
        parts = []

        # Handle both direct fields and Kafka message format with 'data' wrapper
        data = email_data.get("data", email_data)

        # Add sender info - handle "Name <email@domain.com>" format
        sender_raw = data.get("sender") or data.get("sender_email") or data.get("from_address")
        if sender_raw:
            parts.append(f"From: {sender_raw}")

        # Add subject
        if data.get("subject"):
            parts.append(f"Subject: {data['subject']}")

        # Add body
        if data.get("body"):  # Primary field name from actual data
            parts.append(f"\n{data['body']}")
        elif data.get("body_text"):
            parts.append(f"\n{data['body_text']}")
        elif data.get("body_html"):
            # Basic HTML stripping - in production, use proper HTML parser
            import re

            text = re.sub("<[^<]+?>", "", data["body_html"])
            parts.append(f"\n{text}")

        return "\n".join(parts)

    def prepare_twitter_text(self, tweet_data: Dict[str, Any]) -> str:
        """Prepare Twitter data for embedding."""
        parts = []

        # Add author info
        if tweet_data.get("author_username"):
            parts.append(f"@{tweet_data['author_username']}")
        elif tweet_data.get("profileLink"):
            # Extract username from profile link
            username = tweet_data["profileLink"].split("/")[-1]
            parts.append(f"@{username}")

        # Add tweet text
        if tweet_data.get("text"):
            parts.append(tweet_data["text"])
        elif tweet_data.get("content"):
            parts.append(tweet_data["content"])

        return " ".join(parts)
