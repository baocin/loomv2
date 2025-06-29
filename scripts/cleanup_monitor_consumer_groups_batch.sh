#!/bin/bash

echo "Cleaning up monitor consumer groups in batches..."

# Delete groups in parallel batches
docker exec loomv2-kafka-1 bash -c '
    kafka-consumer-groups --bootstrap-server localhost:9092 --list | grep "^monitor-" | \
    xargs -P 10 -I {} kafka-consumer-groups --bootstrap-server localhost:9092 --delete --group {} 2>/dev/null
'

echo "Cleanup complete. Checking remaining groups..."
remaining=$(docker exec loomv2-kafka-1 kafka-consumer-groups --bootstrap-server localhost:9092 --list | grep "^monitor-" | wc -l)
echo "Remaining monitor consumer groups: $remaining"