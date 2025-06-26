#!/usr/bin/env python3
"""Moondream OCR service for processing Twitter screenshots."""

import asyncio
import base64
import json
import logging
import os
import time
from io import BytesIO

import torch
from PIL import Image
from transformers import AutoModelForCausalLM, AutoTokenizer
from kafka import KafkaConsumer, KafkaProducer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - moondream-ocr - %(levelname)s - %(message)s"
)


class MoondreamOCR:
    """Moondream-based OCR processor for Twitter images."""
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.tokenizer = None
        
    def load_model(self):
        """Load Moondream model and tokenizer."""
        logging.info("Loading Moondream model...")
        
        model_id = "vikhyatk/moondream2"
        self.tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_id,
            trust_remote_code=True,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            device_map={"": self.device}
        )
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
            description = self.model.answer_question(enc_image, desc_prompt, self.tokenizer)
            
            return {
                "ocr_text": response,
                "description": description,
                "success": True
            }
            
        except Exception as e:
            logging.error(f"Error processing image: {e}")
            return {
                "ocr_text": "",
                "description": "",
                "success": False,
                "error": str(e)
            }


def main():
    """Main service loop."""
    # Initialize OCR processor
    ocr = MoondreamOCR()
    ocr.load_model()
    
    # Kafka configuration
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
    input_topic = "external.twitter.images.raw"
    output_topic = "media.image.analysis.moondream_results"
    
    # Create Kafka consumer and producer
    consumer = KafkaConsumer(
        input_topic,
        bootstrap_servers=bootstrap_servers.split(","),
        auto_offset_reset='latest',
        enable_auto_commit=True,
        group_id='moondream-ocr-consumer',
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )
    
    producer = KafkaProducer(
        bootstrap_servers=bootstrap_servers.split(","),
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    
    logging.info(f"Starting Moondream OCR service...")
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
            result = ocr.process_image(image_data)
            
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
                    "error": result.get("error")
                },
                "processing_time_ms": (time.time() - start_time) * 1000,
                "model_version": "moondream2",
                "metadata": data.get("metadata", {})
            }
            
            # Send to output topic
            producer.send(output_topic, value=output_message)
            
            logging.info(f"Processed image for tweet {data.get('tweet_id')} - "
                        f"OCR length: {len(result['ocr_text'])} chars")
            
        except Exception as e:
            logging.error(f"Error processing message: {e}")
            continue
    
    consumer.close()
    producer.close()


if __name__ == "__main__":
    main()