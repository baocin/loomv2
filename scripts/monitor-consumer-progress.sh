#!/bin/bash
# Monitor consumer progress in real-time

echo "Monitoring consumer progress (Ctrl+C to stop)..."
echo ""

while true; do
    clear
    echo "Consumer Progress Monitor - $(date)"
    echo "========================================"
    echo ""
    
    # Check each consumer group
    echo "SILERO-VAD CONSUMER:"
    docker exec loomv2-kafka-1 /usr/bin/kafka-consumer-groups \
        --bootstrap-server localhost:9092 \
        --describe --group silero-vad-consumer 2>/dev/null | \
        grep -E "TOPIC|device.audio.raw" | \
        awk '{printf "%-25s %-10s %-15s %-15s %-10s\n", $2, $3, $4, $5, $6}'
    
    echo ""
    echo "GPS GEOCODING CONSUMER:"
    docker exec loomv2-kafka-1 /usr/bin/kafka-consumer-groups \
        --bootstrap-server localhost:9092 \
        --describe --group gps-geocoding-consumer 2>/dev/null | \
        grep -E "TOPIC|device.sensor.gps" | \
        awk '{printf "%-25s %-10s %-15s %-15s %-10s\n", $2, $3, $4, $5, $6}'
    
    echo ""
    echo "MOTION DETECTOR CONSUMER:"
    docker exec loomv2-kafka-1 /usr/bin/kafka-consumer-groups \
        --bootstrap-server localhost:9092 \
        --describe --group significant-motion-detector 2>/dev/null | \
        grep -E "TOPIC|device.sensor.accelerometer" | \
        awk '{printf "%-25s %-10s %-15s %-15s %-10s\n", $2, $3, $4, $5, $6}'
    
    echo ""
    echo "Press Ctrl+C to exit"
    sleep 5
done