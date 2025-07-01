#!/usr/bin/env python3
"""Moondream OCR service for processing Twitter screenshots."""

import base64
import json
import logging
import os
import time
import threading
from io import BytesIO
from pathlib import Path
from typing import Optional

import torch
import uvicorn
from PIL import Image
from transformers import AutoModelForCausalLM, AutoTokenizer
from kafka import KafkaConsumer, KafkaProducer
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - moondream-ocr - %(levelname)s - %(message)s",
)

# FastAPI app
app = FastAPI(title="Moondream OCR Service", version="1.0.0")


class MoondreamOCR:
    """Moondream-based OCR processor for Twitter images."""

    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.tokenizer = None
        # Set up model cache directory
        self.model_cache_dir = Path(
            os.getenv("MOONDREAM_MODEL_CACHE", "~/.loom/moondream")
        ).expanduser()
        self.model_cache_dir.mkdir(parents=True, exist_ok=True)

    def load_model(self):
        """Load Moondream model and tokenizer."""
        logging.info("Loading Moondream model...")
        logging.info(f"Using model cache directory: {self.model_cache_dir}")

        model_id = "vikhyatk/moondream2"

        # Set HuggingFace cache directory
        os.environ["HF_HOME"] = str(self.model_cache_dir)
        os.environ["TRANSFORMERS_CACHE"] = str(self.model_cache_dir)

        self.tokenizer = AutoTokenizer.from_pretrained(
            model_id, trust_remote_code=True, cache_dir=str(self.model_cache_dir)
        )
        self.model = AutoModelForCausalLM.from_pretrained(
            model_id,
            trust_remote_code=True,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            cache_dir=str(self.model_cache_dir),
        )
        if self.device == "cuda":
            self.model = self.model.to(self.device)
        self.model.eval()

        logging.info(f"Moondream model loaded on {self.device}")

    def process_image(self, image_data: str) -> dict:
        """Process image and extract text using Moondream."""
        try:
            # Decode base64 image
            if "," in image_data:
                image_data = image_data.split(",")[1]

            image_bytes = base64.b64decode(image_data)
            image = Image.open(BytesIO(image_bytes))

            # Convert to RGB if needed
            if image.mode != "RGB":
                image = image.convert("RGB")

            # Prepare OCR prompt
            prompt = "Extract all text from this image. Include tweets, usernames, timestamps, and any other visible text."

            # Encode the image
            enc_image = self.model.encode_image(image)

            # Generate response
            response = self.model.answer_question(enc_image, prompt, self.tokenizer)

            # Also get a general description
            desc_prompt = "Describe what you see in this image."
            description = self.model.answer_question(
                enc_image, desc_prompt, self.tokenizer
            )

            return {"ocr_text": response, "description": description, "success": True}

        except Exception as e:
            logging.error(f"Error processing image: {e}")
            return {
                "ocr_text": "",
                "description": "",
                "success": False,
                "error": str(e),
            }


# Global OCR instance
ocr_processor: Optional[MoondreamOCR] = None


# Pydantic models for API
class OCRRequest(BaseModel):
    image_data: str  # Base64 encoded image
    prompt: Optional[str] = (
        "Extract all text from this image. Include tweets, usernames, timestamps, and any other visible text."
    )


class OCRResponse(BaseModel):
    ocr_text: str
    description: str
    success: bool
    error: Optional[str] = None
    processing_time_ms: float


@app.on_event("startup")
async def startup_event():
    """Initialize the OCR model on startup."""
    global ocr_processor
    ocr_processor = MoondreamOCR()
    ocr_processor.load_model()

    # Start Kafka consumer in background thread
    thread = threading.Thread(target=kafka_consumer_thread, daemon=True)
    thread.start()


@app.get("/")
async def root():
    """Root endpoint with service info."""
    return {
        "service": "Moondream OCR",
        "version": "1.0.0",
        "status": "running",
        "model": "vikhyatk/moondream2",
        "device": ocr_processor.device if ocr_processor else "not initialized",
    }


@app.get("/healthz")
async def health_check():
    """Health check endpoint."""
    if ocr_processor and ocr_processor.model:
        return {"status": "healthy"}
    else:
        raise HTTPException(status_code=503, detail="Model not loaded")


@app.get("/readyz")
async def readiness_check():
    """Readiness check endpoint."""
    if ocr_processor and ocr_processor.model:
        return {"status": "ready"}
    else:
        raise HTTPException(status_code=503, detail="Model not ready")


@app.post("/ocr", response_model=OCRResponse)
async def perform_ocr(request: OCRRequest):
    """Perform OCR on a base64 encoded image."""
    if not ocr_processor:
        raise HTTPException(status_code=503, detail="OCR processor not initialized")

    start_time = time.time()

    try:
        result = ocr_processor.process_image(request.image_data)
        processing_time_ms = (time.time() - start_time) * 1000

        return OCRResponse(
            ocr_text=result["ocr_text"],
            description=result["description"],
            success=result["success"],
            error=result.get("error"),
            processing_time_ms=processing_time_ms,
        )
    except Exception as e:
        processing_time_ms = (time.time() - start_time) * 1000
        return OCRResponse(
            ocr_text="",
            description="",
            success=False,
            error=str(e),
            processing_time_ms=processing_time_ms,
        )


def kafka_consumer_thread():
    """Kafka consumer thread for processing images."""
    global ocr_processor

    if not ocr_processor:
        logging.error("OCR processor not initialized for Kafka consumer")
        return

    # Kafka configuration
    bootstrap_servers = os.getenv("LOOM_KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
    input_topic = "external.twitter.images.raw"
    output_topic = "media.image.analysis.moondream_results"

    try:
        # Create Kafka consumer and producer
        consumer = KafkaConsumer(
            input_topic,
            bootstrap_servers=bootstrap_servers.split(","),
            auto_offset_reset="latest",
            enable_auto_commit=True,
            group_id="moondream-ocr-consumer",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            max_poll_records=1,  # Process one image at a time
            max_poll_interval_ms=600000,  # 10 minutes timeout for processing
            session_timeout_ms=60000,  # 1 minute session timeout
            heartbeat_interval_ms=3000,  # Send heartbeat every 3 seconds
        )

        producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers.split(","),
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )

        logging.info("Kafka consumer thread started")
        logging.info(f"Consuming from: {input_topic}")
        logging.info(f"Producing to: {output_topic}")

        # Process messages
        for message in consumer:
            try:
                start_time = time.time()
                msg_data = message.value

                # Extract image data
                data = msg_data.get("data", {})
                image_data = data.get("image_data")

                if not image_data:
                    logging.warning("No image data in message")
                    continue

                # Process image
                result = ocr_processor.process_image(image_data)

                # Create output message
                output_message = {
                    "schema_version": "v1",
                    "trace_id": msg_data.get("trace_id"),
                    "tweet_id": data.get("tweet_id"),
                    "tweet_url": data.get("tweet_url"),
                    "device_id": msg_data.get("device_id"),
                    "recorded_at": msg_data.get("recorded_at"),
                    "ocr_results": {
                        "full_text": result["ocr_text"],
                        "description": result["description"],
                        "success": result["success"],
                        "error": result.get("error"),
                    },
                    "processing_time_ms": (time.time() - start_time) * 1000,
                    "model_version": "moondream2",
                    "metadata": data.get("metadata", {}),
                }

                # Send to output topic
                producer.send(output_topic, value=output_message)

                processing_time = (time.time() - start_time) * 1000
                logging.info(
                    f"Processed image for tweet {data.get('tweet_id')} - "
                    f"OCR length: {len(result['ocr_text'])} chars - "
                    f"Processing time: {processing_time:.0f}ms"
                )

            except Exception as e:
                logging.error(f"Error processing Kafka message: {e}")
                continue

    except Exception as e:
        logging.error(f"Error in Kafka consumer thread: {e}")


if __name__ == "__main__":
    # Run FastAPI server
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8007")),
        log_level="info",
    )
