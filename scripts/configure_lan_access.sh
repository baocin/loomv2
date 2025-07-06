#!/bin/bash

# Script to configure Loom services for LAN access

echo "Configuring Loom services for LAN access..."

# Get the machine's IP address
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    IP_ADDRESS=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | head -1 | awk '{print $2}')
else
    # Linux
    IP_ADDRESS=$(hostname -I | awk '{print $1}')
fi

if [ -z "$IP_ADDRESS" ]; then
    echo "Error: Could not determine IP address automatically"
    echo "Please enter your machine's IP address manually:"
    read IP_ADDRESS
fi

echo "Using IP address: $IP_ADDRESS"

# Update Pipeline Monitor .env file
PIPELINE_MONITOR_ENV="services/pipeline-monitor/.env"
if [ -f "$PIPELINE_MONITOR_ENV" ]; then
    echo "Updating Pipeline Monitor configuration..."
    sed -i.bak "s|VITE_API_URL=.*|VITE_API_URL=http://$IP_ADDRESS:8082|" "$PIPELINE_MONITOR_ENV"
    sed -i.bak "s|VITE_WS_URL=.*|VITE_WS_URL=ws://$IP_ADDRESS:8082/ws|" "$PIPELINE_MONITOR_ENV"
    echo "✓ Pipeline Monitor configured"
else
    echo "Creating Pipeline Monitor .env file..."
    cat > "$PIPELINE_MONITOR_ENV" << EOF
# Pipeline Monitor Frontend Environment Variables

# API endpoint for the backend service
VITE_API_URL=http://$IP_ADDRESS:8082

# WebSocket endpoint
VITE_WS_URL=ws://$IP_ADDRESS:8082/ws

# Kafka Test Producer endpoint
VITE_TEST_PRODUCER_URL=http://$IP_ADDRESS:8008

# Refresh intervals (in milliseconds)
VITE_METRICS_REFRESH_INTERVAL=5000
VITE_HEALTH_CHECK_INTERVAL=10000

# Cache settings
VITE_MAX_CACHED_MESSAGES=100
EOF
    echo "✓ Pipeline Monitor .env created"
fi

# Update docker-compose.simple.yml to expose ports
echo "Updating Docker Compose configuration for LAN access..."
sed -i.bak 's/127.0.0.1:8082:8080/0.0.0.0:8082:8080/' docker-compose.simple.yml 2>/dev/null || true
sed -i.bak 's/127.0.0.1:3001:3000/0.0.0.0:3001:3000/' docker-compose.simple.yml 2>/dev/null || true

echo ""
echo "Configuration complete!"
echo ""
echo "To access Loom services from other devices on your LAN:"
echo "1. Pipeline Monitor UI: http://$IP_ADDRESS:3001"
echo "2. Pipeline Monitor API: http://$IP_ADDRESS:8082"
echo ""
echo "Make sure to:"
echo "1. Rebuild the Pipeline Monitor: cd services/pipeline-monitor && npm run build"
echo "2. Restart services: docker-compose -f docker-compose.simple.yml down && docker-compose -f docker-compose.simple.yml up -d"
echo ""
echo "Note: Ensure your firewall allows connections on ports 3001 and 8082"
