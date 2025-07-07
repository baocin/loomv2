#\!/bin/bash

# Purge all messages from Kafka topics by setting retention to 1ms temporarily

KAFKA_CONTAINER="loomv2-kafka-1"
BOOTSTRAP_SERVER="localhost:9092"

echo "=== Purging All Kafka Messages ==="
echo "This will delete all messages while keeping topics intact"

# Get all topics except internal ones
TOPICS=$(docker exec $KAFKA_CONTAINER kafka-topics --bootstrap-server $BOOTSTRAP_SERVER --list  < /dev/null |  grep -v "^__consumer_offsets$" | sort)

echo -e "\nStep 1: Setting retention to 1ms for all topics..."
for topic in $TOPICS; do
    echo "Purging topic: $topic"
    docker exec $KAFKA_CONTAINER kafka-configs --bootstrap-server $BOOTSTRAP_SERVER \
        --alter --entity-type topics --entity-name "$topic" \
        --add-config retention.ms=1 2>/dev/null || echo "  Failed to set retention"
done

echo -e "\nStep 2: Waiting for purge to complete..."
sleep 5

echo -e "\nStep 3: Restoring default retention policies..."
# Restore proper retention based on topic type
declare -A RETENTION_MS
RETENTION_MS["device.audio.raw"]=604800000  # 7 days
RETENTION_MS["device.sensor.gps.raw"]=2592000000  # 30 days
RETENTION_MS["device.sensor.accelerometer.raw"]=2592000000  # 30 days
RETENTION_MS["device.health.heartrate.raw"]=5184000000  # 60 days
RETENTION_MS["device.state.power.raw"]=2592000000  # 30 days
RETENTION_MS["device.system.apps.macos.raw"]=2592000000  # 30 days
RETENTION_MS["device.system.apps.android.raw"]=2592000000  # 30 days
RETENTION_MS["device.metadata.raw"]=7776000000  # 90 days
RETENTION_MS["os.events.app_lifecycle.raw"]=2592000000  # 30 days
RETENTION_MS["os.events.system.raw"]=2592000000  # 30 days
RETENTION_MS["os.events.notifications.raw"]=2592000000  # 30 days

for topic in $TOPICS; do
    # Get retention or use default 30 days
    retention=${RETENTION_MS[$topic]:-2592000000}
    
    echo "Restoring retention for $topic to $retention ms"
    docker exec $KAFKA_CONTAINER kafka-configs --bootstrap-server $BOOTSTRAP_SERVER \
        --alter --entity-type topics --entity-name "$topic" \
        --add-config retention.ms=$retention 2>/dev/null || echo "  Failed to restore retention"
done

echo -e "\nStep 4: Verifying message counts..."
for topic in device.audio.raw device.sensor.accelerometer.raw os.events.app_lifecycle.raw; do
    OFFSET=$(docker exec $KAFKA_CONTAINER kafka-run-class kafka.tools.GetOffsetShell --broker-list $BOOTSTRAP_SERVER --topic $topic 2>/dev/null | cut -d: -f3)
    echo "$topic: $OFFSET messages"
done

echo -e "\nDone! All messages purged."
