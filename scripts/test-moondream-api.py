#!/usr/bin/env python3
"""Test script to validate Moondream OCR API with a sample image."""

import base64
import requests
import time
from io import BytesIO
from PIL import Image, ImageDraw


def create_test_tweet_image():
    """Create a test image that looks like a tweet."""
    # Create a white background image
    img = Image.new("RGB", (600, 400), color="white")
    draw = ImageDraw.Draw(img)

    # Add some test tweet content
    draw.text((20, 20), "@test_user", fill="black")
    draw.text(
        (20, 50), "This is a test tweet with some text that should be", fill="black"
    )
    draw.text(
        (20, 70), "extracted by the OCR service. Let's see if it works!", fill="black"
    )
    draw.text((20, 100), "👍 42  💬 5  🔁 12", fill="gray")
    draw.text((20, 130), "12:34 PM · Dec 26, 2024", fill="gray")

    # Save to bytes
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    # Convert to base64
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def test_ocr_endpoint(base_url="http://localhost:8007"):
    """Test the OCR endpoint with a sample image."""

    # Check health first
    print("Checking service health...")
    try:
        response = requests.get(f"{base_url}/healthz")
        if response.status_code == 200:
            print("✅ Service is healthy")
        else:
            print(f"❌ Service unhealthy: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Cannot connect to service: {e}")
        return

    # Create test image
    print("\nCreating test tweet image...")
    test_image = create_test_tweet_image()

    # Test OCR endpoint
    print("\nTesting OCR endpoint...")
    start_time = time.time()

    try:
        response = requests.post(
            f"{base_url}/ocr",
            json={
                "image_data": test_image,
                "prompt": "Extract all text from this tweet image including username, tweet content, and timestamp.",
            },
        )

        elapsed_time = (time.time() - start_time) * 1000

        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ OCR completed in {elapsed_time:.0f}ms")
            print(f"\nOCR Text:\n{result['ocr_text']}")
            print(f"\nDescription:\n{result['description']}")
            print(f"\nProcessing time: {result['processing_time_ms']:.0f}ms")

            # Check if key text was extracted
            if "@test_user" in result["ocr_text"]:
                print("\n✅ Username detected correctly")
            if "test tweet" in result["ocr_text"].lower():
                print("✅ Tweet content detected")

        else:
            print(f"\n❌ OCR failed: {response.status_code}")
            print(response.text)

    except Exception as e:
        print(f"\n❌ Error calling OCR endpoint: {e}")


if __name__ == "__main__":
    test_ocr_endpoint()
