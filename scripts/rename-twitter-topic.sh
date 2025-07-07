#!/bin/bash
# Rename external.twitter.images.raw to external.twitter.screenshots.raw for clarity

set -euo pipefail

NAMESPACE="${NAMESPACE:-loom-dev}"
OLD_TOPIC="external.twitter.images.raw"
NEW_TOPIC="external.twitter.screenshots.raw"

echo "=== Renaming Twitter Topic for Better Clarity ==="
echo "Namespace: $NAMESPACE"
echo "From: $OLD_TOPIC"
echo "To:   $NEW_TOPIC"
echo ""
echo "Reason: This topic contains SCREENSHOTS of tweets for OCR, not embedded images"
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
    exit 1
fi

echo "✅ Found Kafka pod: $KAFKA_POD"

# Step 3: Check current topics
echo ""
echo "Step 3: Checking current topics..."
OLD_EXISTS=$(kubectl exec -n $NAMESPACE $KAFKA_POD -- kafka-topics.sh \
    --bootstrap-server localhost:9092 \
    --list 2>/dev/null | grep "^$OLD_TOPIC$" || echo "")

NEW_EXISTS=$(kubectl exec -n $NAMESPACE $KAFKA_POD -- kafka-topics.sh \
    --bootstrap-server localhost:9092 \
    --list 2>/dev/null | grep "^$NEW_TOPIC$" || echo "")

if [ -n "$NEW_EXISTS" ]; then
    echo "✅ New topic '$NEW_TOPIC' already exists"
    if [ -n "$OLD_EXISTS" ]; then
        echo "⚠️  Old topic '$OLD_TOPIC' still exists - both topics present"
        echo "    You may want to migrate data and delete the old topic"
    fi
else
    echo "Creating new topic: $NEW_TOPIC"
    kubectl exec -n $NAMESPACE $KAFKA_POD -- kafka-topics.sh \
        --bootstrap-server localhost:9092 \
        --create \
        --topic $NEW_TOPIC \
        --partitions 3 \
        --replication-factor 1
    echo "✅ Created topic: $NEW_TOPIC"
fi

# Step 4: Update service configurations
echo ""
echo "Step 4: Files that need manual updates:"
echo ""
echo "1. X URL Processor (Producer):"
echo "   File: services/x-url-processor/app/main.py"
echo "   Change line 128: topic=\"$NEW_TOPIC\""
echo ""
echo "2. Twitter OCR Processor (Consumer):"
echo "   File: services/twitter-ocr-processor/app/main.py"
echo "   Change line 201: self.input_topic = \"$NEW_TOPIC\""
echo ""
echo "3. Topic Creation Script:"
echo "   File: scripts/create_kafka_topics.py"
echo "   Update RAW_TOPICS list"
echo ""

# Step 5: Show deployment commands
echo "Step 5: After updating code, redeploy services:"
echo ""
echo "# Rebuild and deploy X URL processor"
echo "cd services/x-url-processor && make docker && make docker-push"
echo "kubectl rollout restart deployment/x-url-processor -n $NAMESPACE"
echo ""
echo "# Rebuild and deploy Twitter OCR processor"
echo "cd services/twitter-ocr-processor && make docker && make docker-push"
echo "kubectl rollout restart deployment/twitter-ocr-processor -n $NAMESPACE"
echo ""

# Step 6: Clean up old topic (optional)
if [ -n "$OLD_EXISTS" ] && [ -n "$NEW_EXISTS" ]; then
    echo "Step 6: Clean up old topic (OPTIONAL - only after migration):"
    echo ""
    echo "⚠️  WARNING: This will delete the old topic and all its data!"
    echo ""
    echo "# Delete old topic (run manually when ready)"
    echo "kubectl exec -n $NAMESPACE $KAFKA_POD -- kafka-topics.sh \\"
    echo "    --bootstrap-server localhost:9092 \\"
    echo "    --delete \\"
    echo "    --topic $OLD_TOPIC"
fi

echo ""
echo "=== Rename Process Summary ==="
echo "✅ New topic created: $NEW_TOPIC"
echo "📝 Manual code updates required (see above)"
echo "🔄 Services need rebuild and restart after code changes"
echo "🗑️  Old topic cleanup is optional and manual"
echo ""
echo "This renaming improves clarity: the topic contains tweet SCREENSHOTS, not embedded images"
