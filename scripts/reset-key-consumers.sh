#!/bin/bash
# Reset key consumer groups that were stalling

echo "Resetting key consumer groups..."

# Stop consumers first
echo "Stopping consumers..."
docker stop loomv2-silero-vad-1 loomv2-gps-geocoding-consumer-1 loomv2-significant-motion-detector-1 2>/dev/null

# Wait a moment for consumers to fully stop
sleep 2

# Reset offsets
echo ""
echo "Resetting silero-vad-consumer..."
docker exec loomv2-kafka-1 /usr/bin/kafka-consumer-groups \
    --bootstrap-server localhost:9092 \
    --group silero-vad-consumer \
    --reset-offsets \
    --to-earliest \
    --all-topics \
    --execute

echo ""
echo "Resetting gps-geocoding-consumer..."
docker exec loomv2-kafka-1 /usr/bin/kafka-consumer-groups \
    --bootstrap-server localhost:9092 \
    --group gps-geocoding-consumer \
    --reset-offsets \
    --to-earliest \
    --all-topics \
    --execute

echo ""
echo "Resetting significant-motion-detector..."
docker exec loomv2-kafka-1 /usr/bin/kafka-consumer-groups \
    --bootstrap-server localhost:9092 \
    --group significant-motion-detector \
    --reset-offsets \
    --to-earliest \
    --all-topics \
    --execute

# Start consumers again
echo ""
echo "Starting consumers..."
docker start loomv2-silero-vad-1 loomv2-gps-geocoding-consumer-1 loomv2-significant-motion-detector-1

# Wait for them to start
sleep 5

# Check status
echo ""
echo "Checking consumer lag..."
docker exec loomv2-kafka-1 /usr/bin/kafka-consumer-groups \
    --bootstrap-server localhost:9092 \
    --describe \
    --group silero-vad-consumer

echo ""
docker exec loomv2-kafka-1 /usr/bin/kafka-consumer-groups \
    --bootstrap-server localhost:9092 \
    --describe \
    --group gps-geocoding-consumer

echo ""
docker exec loomv2-kafka-1 /usr/bin/kafka-consumer-groups \
    --bootstrap-server localhost:9092 \
    --describe \
    --group significant-motion-detector