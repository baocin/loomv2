#!/bin/bash
# Default health check script for Python services
# Services should override this with their specific health endpoints

# Check if a health endpoint is defined
if [ ! -z "$HEALTH_CHECK_URL" ]; then
    curl -f "$HEALTH_CHECK_URL" || exit 1
else
    # Default: check if Python process is running
    pgrep -f python > /dev/null || exit 1
fi
