#!/usr/bin/env python3
"""Simple OCR test."""

import base64
import requests
from PIL import Image, ImageDraw
from io import BytesIO

# Create test image
img = Image.new('RGB', (300, 200), color='white')
draw = ImageDraw.Draw(img)
draw.text((20, 20), "Hello OCR Test", fill='black')
draw.text((20, 50), "@test_user", fill='black')
draw.text((20, 80), "This is a test tweet", fill='black')

# Convert to base64
buffer = BytesIO()
img.save(buffer, format='PNG')
buffer.seek(0)
image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')

# Test OCR
response = requests.post(
    "http://localhost:8007/ocr",
    json={
        "image_data": image_data,
        "prompt": "Extract all text from this image."
    }
)

print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"OCR Text: {data['ocr_text']}")
    print(f"Success: {data['success']}")
    print(f"Time: {data['processing_time_ms']:.0f}ms")
else:
    print(f"Error: {response.text}")