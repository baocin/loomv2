#!/bin/bash
# Check if the consumer fixes are working by examining Docker logs

echo "Checking consumer logs for batch commit messages..."
echo ""

# Check silero-vad logs for batch commits
echo "=== Silero VAD Consumer ==="
docker logs $(docker ps -q -f name=silero-vad) 2>&1 | grep -E "Batch commit|messages_processed|VAD processing completed" | tail -10

echo ""
echo "=== GPS Geocoding Consumer ==="
docker logs $(docker ps -q -f name=gps-geocoding) 2>&1 | grep -E "Batch commit|Processing GPS location|Geocoded" | tail -10

echo ""
echo "To follow logs in real-time:"
echo "  docker logs -f \$(docker ps -q -f name=silero-vad)"
echo "  docker logs -f \$(docker ps -q -f name=gps-geocoding)"