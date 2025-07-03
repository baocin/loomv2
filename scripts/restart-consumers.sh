#!/bin/bash
# Script to restart Kafka consumers after fixes

echo "Restarting Kafka consumers with fixes..."

# Restart consumers that have been fixed
echo "Restarting silero-vad..."
kubectl rollout restart deployment/silero-vad -n loom-dev

echo "Restarting gps-geocoding-consumer..."
kubectl rollout restart deployment/gps-geocoding-consumer -n loom-dev

# Wait for rollouts to complete
echo "Waiting for rollouts to complete..."
kubectl rollout status deployment/silero-vad -n loom-dev --timeout=60s
kubectl rollout status deployment/gps-geocoding-consumer -n loom-dev --timeout=60s

echo "Checking consumer status..."
kubectl get pods -n loom-dev | grep -E "silero-vad|gps-geocoding"

echo ""
echo "To monitor logs:"
echo "  kubectl logs -f deployment/silero-vad -n loom-dev"
echo "  kubectl logs -f deployment/gps-geocoding-consumer -n loom-dev"
echo ""
echo "To check consumer lag:"
echo "  kubectl exec -it deployment/kafka -n loom-dev -- kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --all-groups"