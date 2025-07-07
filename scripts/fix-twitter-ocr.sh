#!/bin/bash
# Fix Twitter OCR Processor missing topic issue and improve naming

set -euo pipefail

NAMESPACE="${NAMESPACE:-loom-dev}"

echo "=== Fixing Twitter OCR Processor & Improving Topic Naming ==="
echo "Namespace: $NAMESPACE"
echo ""
echo "Note: external.twitter.images.raw contains SCREENSHOTS of tweets, not embedded images"
echo "Consider renaming to external.twitter.screenshots.raw for clarity"
echo ""

# Step 1: Check if cluster is accessible
echo "Step 1: Checking cluster connectivity..."
if ! kubectl get nodes >/dev/null 2>&1; then
    echo "❌ Kubernetes cluster not accessible. Please ensure k3d cluster is running:"
    echo "   k3d cluster start loom-local"
    echo "   k3d kubeconfig merge loom-local --kubeconfig-merge-default"
    exit 1
fi

# Step 2: Get Kafka pod
echo "Step 2: Finding Kafka pod..."
KAFKA_POD=$(kubectl get pods -n $NAMESPACE -l app=kafka -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

if [ -z "$KAFKA_POD" ]; then
    echo "❌ Kafka pod not found in namespace $NAMESPACE"
    echo "   Available namespaces:"
    kubectl get namespaces
    exit 1
fi

echo "✅ Found Kafka pod: $KAFKA_POD"

# Step 3: Check if topic exists
echo ""
echo "Step 3: Checking if external.twitter.images.raw topic exists..."
TOPIC_EXISTS=$(kubectl exec -n $NAMESPACE $KAFKA_POD -- kafka-topics.sh \
    --bootstrap-server localhost:9092 \
    --list 2>/dev/null | grep "external.twitter.images.raw" || echo "")

if [ -n "$TOPIC_EXISTS" ]; then
    echo "✅ Topic external.twitter.images.raw already exists"
else
    echo "❌ Topic external.twitter.images.raw does not exist"

    # Step 4: Create the topic
    echo ""
    echo "Step 4: Creating missing topic..."
    kubectl exec -n $NAMESPACE $KAFKA_POD -- kafka-topics.sh \
        --bootstrap-server localhost:9092 \
        --create \
        --topic external.twitter.images.raw \
        --partitions 3 \
        --replication-factor 1

    echo "✅ Created topic: external.twitter.images.raw"
fi

# Step 5: Create any other missing topics
echo ""
echo "Step 5: Creating other required topics..."
REQUIRED_TOPICS=(
    "external.twitter.liked.raw"
    "media.image.analysis.moondream_results"
    "media.text.ocr_extracted"
    "media.text.ocr_cleaned"
)

for topic in "${REQUIRED_TOPICS[@]}"; do
    echo "Checking topic: $topic"
    TOPIC_EXISTS=$(kubectl exec -n $NAMESPACE $KAFKA_POD -- kafka-topics.sh \
        --bootstrap-server localhost:9092 \
        --list 2>/dev/null | grep "^$topic$" || echo "")

    if [ -z "$TOPIC_EXISTS" ]; then
        echo "  Creating: $topic"
        kubectl exec -n $NAMESPACE $KAFKA_POD -- kafka-topics.sh \
            --bootstrap-server localhost:9092 \
            --create \
            --topic $topic \
            --partitions 3 \
            --replication-factor 1 || echo "  ⚠️  Failed to create $topic"
    else
        echo "  ✅ Already exists: $topic"
    fi
done

# Step 6: Restart twitter-ocr-processor
echo ""
echo "Step 6: Restarting twitter-ocr-processor..."
kubectl rollout restart deployment/twitter-ocr-processor -n $NAMESPACE 2>/dev/null || \
    echo "⚠️  twitter-ocr-processor deployment not found"

# Step 7: Check consumer group status
echo ""
echo "Step 7: Checking consumer group status..."
sleep 5
kubectl exec -n $NAMESPACE $KAFKA_POD -- kafka-consumer-groups.sh \
    --bootstrap-server localhost:9092 \
    --group twitter-ocr-processor \
    --describe 2>/dev/null || echo "⚠️  Consumer group not found or no active consumers"

echo ""
echo "=== Fix Complete ==="
echo "✅ Missing topics created"
echo "✅ twitter-ocr-processor restarted"
echo ""
echo "📝 NAMING RECOMMENDATION:"
echo "   Consider renaming 'external.twitter.images.raw' to 'external.twitter.screenshots.raw'"
echo "   This topic contains tweet SCREENSHOTS for OCR, not embedded images"
echo "   See RENAME_TWITTER_TOPIC.md for migration guide"
echo ""
echo "Monitor logs with:"
echo "   kubectl logs -n $NAMESPACE deployment/twitter-ocr-processor -f"
echo ""
echo "Check all topics with:"
echo "   kubectl exec -n $NAMESPACE $KAFKA_POD -- kafka-topics.sh --bootstrap-server localhost:9092 --list"
