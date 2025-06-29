#!/bin/bash
# Script to build Docker images with git commit labels

set -e

# Get git information
export GIT_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
export GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
export BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
export BUILD_VERSION=$(git describe --tags --always 2>/dev/null || echo "latest")

echo "Building Docker images with labels:"
echo "  GIT_COMMIT: $GIT_COMMIT"
echo "  GIT_BRANCH: $GIT_BRANCH"
echo "  BUILD_DATE: $BUILD_DATE"
echo "  BUILD_VERSION: $BUILD_VERSION"

# Build services using docker-compose
if [ "$1" = "--rebuild" ]; then
    echo "Forcing rebuild of all images..."
    docker compose -f docker-compose.local.yml build --no-cache
else
    docker compose -f docker-compose.local.yml build
fi

echo "Build complete!"
echo ""
echo "To inspect image labels, run:"
echo "  docker inspect <image-name> --format '{{json .Config.Labels}}' | jq ."
