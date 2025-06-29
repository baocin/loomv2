#!/bin/bash

echo "Cleaning up monitor consumer groups..."

# Get all monitor consumer groups
consumer_groups=$(docker exec loomv2-kafka-1 kafka-consumer-groups --bootstrap-server localhost:9092 --list | grep "^monitor-")

# Count total groups
total_groups=$(echo "$consumer_groups" | wc -l)
echo "Found $total_groups monitor consumer groups to delete"

# Delete each consumer group
deleted=0
for group in $consumer_groups; do
    if docker exec loomv2-kafka-1 kafka-consumer-groups --bootstrap-server localhost:9092 --delete --group "$group" 2>/dev/null; then
        deleted=$((deleted + 1))
        if [ $((deleted % 100)) -eq 0 ]; then
            echo "Deleted $deleted/$total_groups groups..."
        fi
    fi
done

echo "Successfully deleted $deleted consumer groups"