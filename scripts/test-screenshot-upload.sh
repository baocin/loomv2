#!/bin/bash
# Test script to verify screenshot upload endpoint

echo "Testing screenshot upload to device.image.screenshot.raw topic..."
echo ""

# Generate a small test image (1x1 pixel PNG)
TEST_IMAGE="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="

# Create request payload
REQUEST_BODY=$(cat <<EOF
{
  "device_id": "550e8400-e29b-41d4-a716-446655440000",
  "image_data": "$TEST_IMAGE",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "recorded_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "format": "png",
  "width": 1,
  "height": 1,
  "camera_type": "screen",
  "file_size": 100,
  "metadata": {
    "test": true,
    "source": "test-script"
  }
}
EOF
)

# Send request
echo "Sending screenshot to /images/screenshot endpoint..."
RESPONSE=$(curl -s -X POST "http://localhost:8000/images/screenshot" \
  -H "Content-Type: application/json" \
  -d "$REQUEST_BODY")

echo "Response: $RESPONSE"
echo ""

# Check if successful
if echo "$RESPONSE" | grep -q '"status":"success"'; then
  echo "✅ Screenshot upload successful!"
  
  # Extract topic from response
  TOPIC=$(echo "$RESPONSE" | grep -o '"topic":"[^"]*"' | cut -d'"' -f4)
  echo "Message sent to topic: $TOPIC"
  
  # Check if it's the correct topic
  if [ "$TOPIC" = "device.image.screenshot.raw" ]; then
    echo "✅ Correct topic used!"
  else
    echo "❌ Wrong topic! Expected device.image.screenshot.raw, got $TOPIC"
  fi
else
  echo "❌ Screenshot upload failed!"
fi

echo ""
echo "To check if message was sent to Kafka:"
echo "docker exec loomv2-kafka-1 /usr/bin/kafka-console-consumer --bootstrap-server localhost:9092 --topic device.image.screenshot.raw --from-beginning --max-messages 1"