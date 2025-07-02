#!/bin/bash

# Delete all Kafka consumer groups to force reprocessing from beginning

echo "🗑️  Deleting all Kafka consumer groups..."
echo ""

# Get list of consumer groups
CONSUMER_GROUPS=$(docker exec loomv2-kafka-1 kafka-consumer-groups --bootstrap-server localhost:9092 --list)

# Count total groups
TOTAL_GROUPS=$(echo "$CONSUMER_GROUPS" | wc -l)
echo "Found $TOTAL_GROUPS consumer groups to delete"
echo ""

# Delete each consumer group
COUNT=0
for GROUP in $CONSUMER_GROUPS; do
    if [ -n "$GROUP" ]; then
        COUNT=$((COUNT + 1))
        echo "[$COUNT/$TOTAL_GROUPS] Deleting consumer group: $GROUP"
        docker exec loomv2-kafka-1 kafka-consumer-groups --bootstrap-server localhost:9092 --delete --group "$GROUP" 2>/dev/null
        if [ $? -eq 0 ]; then
            echo "  ✅ Deleted successfully"
        else
            echo "  ⚠️  Failed to delete (may already be deleted)"
        fi
    fi
done

echo ""
echo "✅ Finished deleting consumer groups"
echo ""

# Verify all groups are deleted
echo "Verifying deletion..."
REMAINING=$(docker exec loomv2-kafka-1 kafka-consumer-groups --bootstrap-server localhost:9092 --list | wc -l)
if [ "$REMAINING" -eq 0 ]; then
    echo "✅ All consumer groups successfully deleted"
else
    echo "⚠️  Warning: $REMAINING consumer groups still exist"
    docker exec loomv2-kafka-1 kafka-consumer-groups --bootstrap-server localhost:9092 --list
fi