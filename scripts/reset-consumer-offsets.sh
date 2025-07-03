#!/bin/bash
# Reset consumer group offsets to reprocess all messages from the beginning

echo "Resetting consumer group offsets to beginning..."
echo ""

# List of consumer groups to reset
CONSUMER_GROUPS=(
    "silero-vad-consumer"
    "gps-geocoding-consumer"
    "significant-motion-detector"
    "kafka-to-db-consumer"
    "generic-kafka-to-db-consumer"
    "kyutai-stt-consumer"
    "minicpm-vision-consumer"
    "moondream-ocr-consumer"
    "text-embedder-consumer"
    "hackernews-url-processor"
    "twitter-ocr-processor"
)

# Function to reset a consumer group
reset_consumer_group() {
    local group=$1
    echo "Resetting consumer group: $group"
    
    # First, stop the consumer by restarting its container
    container_name=$(docker ps --format "{{.Names}}" | grep -i "${group%-consumer}" | head -1)
    if [ ! -z "$container_name" ]; then
        echo "  Stopping consumer container: $container_name"
        docker stop "$container_name" >/dev/null 2>&1
    fi
    
    # Reset the offsets to earliest
    docker exec loomv2-kafka-1 /usr/bin/kafka-consumer-groups \
        --bootstrap-server localhost:9092 \
        --group "$group" \
        --reset-offsets \
        --to-earliest \
        --all-topics \
        --execute
    
    # Start the consumer again if we stopped it
    if [ ! -z "$container_name" ]; then
        echo "  Starting consumer container: $container_name"
        docker start "$container_name" >/dev/null 2>&1
    fi
    
    echo ""
}

# Reset each consumer group
for group in "${CONSUMER_GROUPS[@]}"; do
    reset_consumer_group "$group"
done

echo "All consumer groups have been reset to the beginning."
echo ""
echo "Checking consumer group status..."
docker exec loomv2-kafka-1 /usr/bin/kafka-consumer-groups --bootstrap-server localhost:9092 --describe --all-groups | head -50