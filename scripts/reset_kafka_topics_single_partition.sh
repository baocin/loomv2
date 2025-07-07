#!/bin/bash
# Script to reset Kafka topics with single partition for debugging
# This script will delete and recreate all topics with 1 partition

set -e

# Configuration
KAFKA_CONTAINER="loomv2-kafka-1"
BOOTSTRAP_SERVER="localhost:9092"
PARTITIONS=1
REPLICATION_FACTOR=1

echo "=== Kafka Topic Reset Script (Single Partition) ==="
echo "This will DELETE and RECREATE all topics with $PARTITIONS partition(s)"
echo "Press Ctrl+C to cancel, or wait 5 seconds to continue..."
sleep 5

# Function to delete a topic
delete_topic() {
    local topic=$1
    echo "Deleting topic: $topic"
    docker exec $KAFKA_CONTAINER kafka-topics --bootstrap-server $BOOTSTRAP_SERVER --delete --topic $topic 2>/dev/null || echo "Topic $topic doesn't exist or already deleted"
}

# Function to create a topic
create_topic() {
    local topic=$1
    local retention_ms=$2
    echo "Creating topic: $topic (partitions=$PARTITIONS, retention=$retention_ms)"
    docker exec $KAFKA_CONTAINER kafka-topics --bootstrap-server $BOOTSTRAP_SERVER \
        --create --topic $topic \
        --partitions $PARTITIONS \
        --replication-factor $REPLICATION_FACTOR \
        --config retention.ms=$retention_ms \
        --config compression.type=producer
}

# List of topics with their retention periods
declare -A TOPICS=(
    # Audio topics
    ["device.audio.raw"]="604800000"  # 7 days
    ["media.audio.vad_filtered"]="604800000"  # 7 days

    # Sensor topics
    ["device.sensor.gps.raw"]="2592000000"  # 30 days
    ["device.sensor.accelerometer.raw"]="2592000000"  # 30 days
    ["device.state.power.raw"]="2592000000"  # 30 days
    ["device.network.wifi.raw"]="604800000"  # 7 days

    # Health topics
    ["device.health.heartrate.raw"]="5184000000"  # 60 days

    # OS Events
    ["os.events.app_lifecycle.raw"]="2592000000"  # 30 days
    ["os.events.system.raw"]="2592000000"  # 30 days
    ["os.events.notifications.raw"]="2592000000"  # 30 days

    # System monitoring
    ["device.system.apps.macos.raw"]="2592000000"  # 30 days
    ["device.system.apps.android.raw"]="2592000000"  # 30 days
    ["device.metadata.raw"]="7776000000"  # 90 days

    # Images
    ["device.image.camera.raw"]="1296000000"  # 15 days
    ["device.video.screen.raw"]="604800000"  # 7 days

    # Processing topics
    ["media.text.transcribed.words"]="1296000000"  # 15 days
    ["media.image.analysis.moondream_results"]="1296000000"  # 15 days
)

echo ""
echo "Step 1: Deleting existing topics..."
for topic in "${!TOPICS[@]}"; do
    delete_topic "$topic"
done

echo ""
echo "Waiting for deletion to complete..."
sleep 5

echo ""
echo "Step 2: Creating topics with single partition..."
for topic in "${!TOPICS[@]}"; do
    create_topic "$topic" "${TOPICS[$topic]}"
done

echo ""
echo "Step 3: Listing all topics to verify..."
docker exec $KAFKA_CONTAINER kafka-topics --bootstrap-server $BOOTSTRAP_SERVER --list | sort

echo ""
echo "=== Topic reset complete! ==="
echo "All topics now have $PARTITIONS partition(s)"
echo ""
echo "Next steps:"
echo "1. Run the database update script: ./scripts/update_kafka_partitions_db.sql"
echo "2. Restart all services: docker-compose restart"
