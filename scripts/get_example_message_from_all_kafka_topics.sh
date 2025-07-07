#!/bin/bash

# Script to fetch one example message from all Kafka topics
# This helps verify the message format that consumers are expecting

set -euo pipefail

# Configuration
KAFKA_CONTAINER="loomv2-kafka-1"
KAFKA_BOOTSTRAP_SERVER="localhost:9092"
POSTGRES_CONTAINER="loomv2-postgres-1"
DB_NAME="loom"
DB_USER="loom"
TIMEOUT_SECONDS=5
OUTPUT_FILE="kafka_topic_examples.json"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Kafka Topic Message Inspector ===${NC}"
echo "Fetching example messages from all Kafka topics..."
echo ""

# Get all Kafka topics from the database
echo -e "${YELLOW}Fetching topic list from database...${NC}"
TOPICS=$(docker exec -i $POSTGRES_CONTAINER psql -U $DB_USER -d $DB_NAME -t -c "
    SELECT DISTINCT topic_name
    FROM pipeline_stage_topics
    WHERE topic_name IS NOT NULL
    ORDER BY topic_name
" | tr -d ' ' | grep -v '^$')

if [ -z "$TOPICS" ]; then
    echo -e "${RED}No topics found in database${NC}"
    exit 1
fi

# Initialize output file with JSON array
echo "[" > $OUTPUT_FILE

FIRST=true
TOPIC_COUNT=0
TOTAL_TOPICS=$(echo "$TOPICS" | wc -l)

# Process each topic
while IFS= read -r TOPIC; do
    if [ -z "$TOPIC" ]; then
        continue
    fi

    TOPIC_COUNT=$((TOPIC_COUNT + 1))
    echo -e "${YELLOW}[$TOPIC_COUNT/$TOTAL_TOPICS] Processing topic: ${GREEN}$TOPIC${NC}"

    # Try to fetch one message from the topic
    MESSAGE=$(docker exec -i $KAFKA_CONTAINER kafka-console-consumer \
        --bootstrap-server $KAFKA_BOOTSTRAP_SERVER \
        --topic "$TOPIC" \
        --from-beginning \
        --max-messages 1 \
        --timeout-ms $((TIMEOUT_SECONDS * 1000)) \
        2>/dev/null || echo "NO_MESSAGES")

    if [ "$MESSAGE" != "NO_MESSAGES" ] && [ -n "$MESSAGE" ]; then
        # Try to parse as JSON for pretty printing
        PRETTY_MESSAGE=$(echo "$MESSAGE" | jq -r '.' 2>/dev/null || echo "$MESSAGE")

        # Add comma if not first entry
        if [ "$FIRST" = false ]; then
            echo "," >> $OUTPUT_FILE
        fi
        FIRST=false

        # Write to output file
        cat >> $OUTPUT_FILE << EOF
  {
    "topic": "$TOPIC",
    "message": $MESSAGE,
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  }
EOF

        # Display on console
        echo -e "  ${GREEN}✓${NC} Found message:"
        echo "$PRETTY_MESSAGE" | head -20 | sed 's/^/    /'
        if [ $(echo "$PRETTY_MESSAGE" | wc -l) -gt 20 ]; then
            echo "    ... (truncated)"
        fi
    else
        echo -e "  ${YELLOW}⚠${NC} No messages found or topic is empty"
    fi

    echo ""
done <<< "$TOPICS"

# Close JSON array
echo "]" >> $OUTPUT_FILE

echo -e "${GREEN}=== Summary ===${NC}"
echo "Processed $TOPIC_COUNT topics"
echo "Results saved to: $OUTPUT_FILE"
echo ""

# Show topics with expected consumers
echo -e "${YELLOW}Topics and their consumers:${NC}"
docker exec -i $POSTGRES_CONTAINER psql -U $DB_USER -d $DB_NAME -c "
    SELECT
        pst.topic_name,
        ps.service_name as consumer,
        pst.topic_role
    FROM pipeline_stage_topics pst
    JOIN pipeline_stages ps ON pst.stage_id = ps.id
    WHERE pst.topic_role = 'input'
    ORDER BY pst.topic_name, ps.service_name
" | head -50

echo ""
echo -e "${GREEN}Script completed!${NC}"
echo "Review $OUTPUT_FILE to see all message examples"
