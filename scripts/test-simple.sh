#!/bin/bash
# Super simple test script for ingestion API
# Just builds, runs, and tests the container

set -e

echo "🚀 Simple API Test"
echo "=================="

# Stop existing container
echo "Cleaning up..."
docker stop loom-api-simple 2>/dev/null || true
docker rm loom-api-simple 2>/dev/null || true

# Build
echo "Building..."
cd services/ingestion-api
docker build -t loom-api:simple .
cd ../..

# Run (without Kafka)
echo "Starting container..."
docker run -d \
    --name loom-api-simple \
    -p 8000:8000 \
    -e LOOM_KAFKA_BOOTSTRAP_SERVERS=dummy:9092 \
    loom-api:simple

# Wait for startup
echo "Waiting for startup..."
sleep 10

# Test
echo "Testing..."
if curl -f -s http://localhost:8000/healthz; then
    echo ""
    echo "✅ SUCCESS! API is running"
    echo ""
    echo "URLs:"
    echo "  http://localhost:8000"
    echo "  http://localhost:8000/docs"
    echo "  http://localhost:8000/healthz"
    echo ""
    echo "Stop with: docker stop loom-api-simple"
else
    echo "❌ FAILED"
    echo "Logs:"
    docker logs loom-api-simple
    exit 1
fi 