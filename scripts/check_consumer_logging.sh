#!/bin/bash

# Script to check which consumers have activity logging implemented

echo "=== Checking Consumer Activity Logging Implementation ==="
echo

# List of consumer services
CONSUMERS=(
    "silero-vad"
    "kyutai-stt"
    "face-emotion"
    "gps-geocoding-consumer"
    "kafka-to-db-consumer"
    "minicpm-vision"
    "moondream-ocr"
    "text-embedder"
    "activity-classifier"
    "step-counter"
    "georegion-detector"
    "significant-motion-detector"
    "scheduled-consumers"
    "hackernews-url-processor"
    "x-url-processor"
)

for consumer in "${CONSUMERS[@]}"; do
    echo "--- $consumer ---"

    # Find consumer files
    consumer_files=$(find ./services/$consumer -name "*.py" -type f 2>/dev/null | grep -E "(consumer|main)" | grep -v __pycache__ | head -3)

    if [ -z "$consumer_files" ]; then
        echo "  ❌ No consumer files found"
    else
        # Check for activity logging
        has_base_consumer=$(echo "$consumer_files" | xargs grep -l "BaseKafkaConsumer" 2>/dev/null)
        actually_uses_base=$(echo "$consumer_files" | xargs grep -E "consumer = BaseKafkaConsumer|consumer = create_optimized_consumer" 2>/dev/null)
        has_activity_logger=$(echo "$consumer_files" | xargs grep -l "ConsumerActivityLogger" 2>/dev/null)
        has_log_consumption=$(echo "$consumer_files" | xargs grep -l "log_consumption" 2>/dev/null)

        if [ -n "$actually_uses_base" ]; then
            echo "  ✓ Uses BaseKafkaConsumer (automatic logging)"
        elif [ -n "$has_base_consumer" ] && [ -z "$actually_uses_base" ]; then
            echo "  ⚠️  Has BaseKafkaConsumer code but doesn't use it"
        elif [ -n "$has_activity_logger" ]; then
            echo "  ✓ Uses ConsumerActivityLogger mixin"
            if [ -n "$has_log_consumption" ]; then
                echo "  ✓ Calls log_consumption/log_production"
            else
                echo "  ⚠️  Has logger but missing log_consumption calls"
            fi
        else
            echo "  ❌ No activity logging implemented"
        fi
    fi
    echo
done

echo "=== Summary ==="
echo "Consumers with activity logging:"
for consumer in "${CONSUMERS[@]}"; do
    consumer_files=$(find ./services/$consumer -name "*.py" -type f 2>/dev/null | grep -E "(consumer|main)" | grep -v __pycache__ | head -3)
    if [ -n "$consumer_files" ]; then
        has_logging=$(echo "$consumer_files" | xargs grep -l "BaseKafkaConsumer\|ConsumerActivityLogger" 2>/dev/null)
        if [ -n "$has_logging" ]; then
            echo "  ✓ $consumer"
        fi
    fi
done
