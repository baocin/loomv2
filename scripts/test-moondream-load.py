#!/usr/bin/env python3
"""Simple test to load Moondream model."""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from PIL import Image
import time

print("Testing Moondream model loading...")
start_time = time.time()

# Load model
model_id = "vikhyatk/moondream2"
print(f"Loading tokenizer from {model_id}...")
tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
print("Tokenizer loaded!")

print(f"Loading model from {model_id}...")
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

model = AutoModelForCausalLM.from_pretrained(
    model_id,
    trust_remote_code=True,
    torch_dtype=torch.float16 if device == "cuda" else torch.float32,
    low_cpu_mem_usage=True
)
print("Model loaded!")

elapsed = time.time() - start_time
print(f"Total loading time: {elapsed:.2f} seconds")

# Test with a simple image
print("\nTesting OCR on a simple image...")
img = Image.new('RGB', (100, 100), color='white')

try:
    enc_image = model.encode_image(img)
    response = model.answer_question(enc_image, "What do you see?", tokenizer)
    print(f"Model response: {response}")
    print("\n✅ Model is working correctly!")
except Exception as e:
    print(f"❌ Error testing model: {e}")