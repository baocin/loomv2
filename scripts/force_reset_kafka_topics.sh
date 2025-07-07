#\!/bin/bash

# Force reset Kafka topics with single partition

KAFKA_CONTAINER="loomv2-kafka-1"
BOOTSTRAP_SERVER="localhost:9092"
PARTITIONS=1
REPLICATION_FACTOR=1

# List of all topics from database
TOPICS=(
    "device.audio.raw"
    "device.video.screen.raw"
    "device.image.camera.raw"
    "device.sensor.gps.raw"
    "device.sensor.accelerometer.raw"
    "device.sensor.barometer.raw"
    "device.sensor.temperature.raw"
    "device.health.heartrate.raw"
    "device.health.steps.raw"
    "device.state.power.raw"
    "device.system.apps.macos.raw"
    "device.system.apps.android.raw"
    "device.metadata.raw"
    "device.network.wifi.raw"
    "device.network.bluetooth.raw"
    "os.events.app_lifecycle.raw"
    "os.events.system.raw"
    "os.events.notifications.raw"
    "digital.clipboard.raw"
    "external.twitter.liked.raw"
    "external.calendar.events.raw"
    "external.email.events.raw"
    "task.url.ingest"
    "media.audio.vad_filtered"
    "media.audio.environment_classified"
    "media.text.transcribed.words"
    "media.text.ocr_extracted"
    "media.text.ocr_cleaned"
    "media.image.camera.preprocessed"
    "media.image.screenshot.preprocessed"
    "media.image.objects_detected"
    "media.image.objects_hashed"
    "media.image.faces_detected"
    "media.image.pose_detected"
    "media.image.gaze_detected"
    "media.image.analysis.moondream_results"
    "media.image.analysis.minicpm_results"
    "media.video.analysis.yolo_results"
    "analysis.3d_reconstruction.dustr_results"
    "analysis.inferred_context.qwen_results"
    "analysis.inferred_context.mistral_results"
    "analysis.audio.emotion_results"
    "analysis.image.emotion_results"
    "task.url.processed.twitter_archived"
    "task.url.processed.hackernews_archived"
    "task.url.processed.pdf_extracted"
    "location.georegion.detected"
    "location.address.geocoded"
    "location.business.identified"
    "device.sensor.accelerometer.windowed"
    "motion.events.significant"
    "motion.classification.activity"
    "device.state.power.enriched"
    "device.state.power.patterns"
    "os.events.app_lifecycle.enriched"
    "external.email.raw"
    "external.email.parsed"
    "external.email.embedded"
    "external.calendar.raw"
    "external.calendar.enriched"
    "external.calendar.embedded"
    "external.hackernews.liked"
    "external.hackernews.content_fetched"
    "external.hackernews.embedded"
    "spatial.slam.mapping"
)

echo "=== Force Kafka Topic Reset ==="
echo "Deleting ALL topics and recreating with $PARTITIONS partition(s)"

# First, delete ALL topics (not just the ones in our list)
echo -e "\nStep 1: Deleting ALL topics..."
ALL_TOPICS=$(docker exec $KAFKA_CONTAINER kafka-topics --bootstrap-server $BOOTSTRAP_SERVER --list  < /dev/null |  grep -v "^__consumer_offsets$")

for topic in $ALL_TOPICS; do
    echo "Deleting topic: $topic"
    docker exec $KAFKA_CONTAINER kafka-topics --bootstrap-server $BOOTSTRAP_SERVER --delete --topic "$topic" 2>/dev/null || true
done

# Wait for deletion
echo -e "\nWaiting for deletion to complete..."
sleep 10

# Verify all topics are deleted
echo -e "\nVerifying deletion..."
REMAINING=$(docker exec $KAFKA_CONTAINER kafka-topics --bootstrap-server $BOOTSTRAP_SERVER --list | grep -v "^__consumer_offsets$" | wc -l)
echo "Remaining topics: $REMAINING"

# Create topics with proper retention
echo -e "\nStep 2: Creating topics with single partition..."

# Define retention periods (in milliseconds)
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

# Create topics
for topic in "${TOPICS[@]}"; do
    # Get retention or use default 30 days
    retention=${RETENTION_MS[$topic]:-2592000000}
    
    echo "Creating topic: $topic (partitions=$PARTITIONS, retention=$retention)"
    docker exec $KAFKA_CONTAINER kafka-topics --bootstrap-server $BOOTSTRAP_SERVER \
        --create --topic "$topic" \
        --partitions $PARTITIONS \
        --replication-factor $REPLICATION_FACTOR \
        --config retention.ms=$retention 2>/dev/null || echo "Topic $topic may already exist"
done

echo -e "\nStep 3: Verifying topics..."
docker exec $KAFKA_CONTAINER kafka-topics --bootstrap-server $BOOTSTRAP_SERVER --list | sort | head -20
echo "..."

echo -e "\nStep 4: Checking partition counts..."
for topic in "device.audio.raw" "device.sensor.accelerometer.raw" "os.events.app_lifecycle.raw"; do
    PART_COUNT=$(docker exec $KAFKA_CONTAINER kafka-topics --bootstrap-server $BOOTSTRAP_SERVER --describe --topic $topic 2>/dev/null | grep -c "Partition:")
    echo "$topic: $PART_COUNT partition(s)"
done

echo -e "\nDone! All topics reset with single partition."
