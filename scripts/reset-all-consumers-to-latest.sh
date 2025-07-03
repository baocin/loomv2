#!/bin/bash
# Reset all consumer groups to latest offset to skip old messages

echo "Resetting all consumer groups to latest offset..."

# Get list of all consumer groups
CONSUMER_GROUPS=$(docker exec loomv2-kafka-1 /usr/bin/kafka-consumer-groups --bootstrap-server localhost:9092 --list)

for GROUP in $CONSUMER_GROUPS; do
    echo ""
    echo "Resetting consumer group: $GROUP"
    
    # Get topics for this consumer group
    TOPICS=$(docker exec loomv2-kafka-1 /usr/bin/kafka-consumer-groups --bootstrap-server localhost:9092 --describe --group $GROUP 2>/dev/null | grep -v "TOPIC" | awk '{print $2}' | sort -u | grep -v "^$")
    
    if [ -z "$TOPICS" ]; then
        echo "  No topics found for group $GROUP"
        continue
    fi
    
    # Reset each topic to latest
    for TOPIC in $TOPICS; do
        echo "  Resetting topic: $TOPIC"
        docker exec loomv2-kafka-1 /usr/bin/kafka-consumer-groups \
            --bootstrap-server localhost:9092 \
            --group $GROUP \
            --reset-offsets \
            --topic $TOPIC \
            --to-latest \
            --execute 2>/dev/null || echo "    Failed to reset $TOPIC"
    done
done

echo ""
echo "All consumer groups reset to latest offset!"
echo ""
echo "Restarting all consumers..."

# Restart all consumer containers
docker compose -f docker-compose.local.yml restart \
    silero-vad \
    kyutai-stt \
    minicpm-vision \
    gps-geocoding-consumer \
    text-embedder \
    kafka-to-db-consumer \
    generic-kafka-to-db-consumer

echo ""
echo "Consumers restarted. They will now process only new messages."