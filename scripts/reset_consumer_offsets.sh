#\!/bin/bash

# Reset all consumer group offsets to latest

KAFKA_CONTAINER="loomv2-kafka-1"
BOOTSTRAP_SERVER="localhost:9092"

echo "=== Resetting Consumer Group Offsets ==="

# Get all consumer groups
CONSUMER_GROUPS=$(docker exec $KAFKA_CONTAINER kafka-consumer-groups --bootstrap-server $BOOTSTRAP_SERVER --list)

for group in $CONSUMER_GROUPS; do
    echo -e "\nResetting offsets for consumer group: $group"
    
    # Get topics for this consumer group
    TOPICS=$(docker exec $KAFKA_CONTAINER kafka-consumer-groups --bootstrap-server $BOOTSTRAP_SERVER --describe --group $group 2>/dev/null  < /dev/null |  grep -E "^$group" | awk '{print $2}' | sort -u | grep -v "^$")
    
    if [ -z "$TOPICS" ]; then
        echo "  No topics found for this group"
        continue
    fi
    
    for topic in $TOPICS; do
        echo "  Resetting topic: $topic to latest"
        docker exec $KAFKA_CONTAINER kafka-consumer-groups --bootstrap-server $BOOTSTRAP_SERVER \
            --group $group \
            --topic $topic \
            --reset-offsets \
            --to-latest \
            --execute 2>/dev/null || echo "    Failed to reset (group may be active)"
    done
done

echo -e "\nDone\! All consumer offsets reset to latest."
