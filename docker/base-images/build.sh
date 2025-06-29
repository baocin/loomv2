#!/bin/bash
# Build script for Loom v2 base Docker images

set -e

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# Build arguments
BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
GIT_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
BUILD_VERSION="${BUILD_VERSION:-latest}"

echo "Building Loom v2 base images..."
echo "Build date: $BUILD_DATE"
echo "Git commit: $GIT_COMMIT"
echo "Version: $BUILD_VERSION"

# Build python-base
echo "Building loom/python-base:3.11-slim..."
docker build \
  --build-arg BUILD_DATE="$BUILD_DATE" \
  --build-arg GIT_COMMIT="$GIT_COMMIT" \
  --build-arg BUILD_VERSION="$BUILD_VERSION" \
  -t loom/python-base:3.11-slim \
  -t loom/python-base:latest \
  "$SCRIPT_DIR/python-base"

# Build kafka-python-base
echo "Building loom/kafka-python-base:3.11-slim..."
docker build \
  --build-arg BUILD_DATE="$BUILD_DATE" \
  --build-arg GIT_COMMIT="$GIT_COMMIT" \
  --build-arg BUILD_VERSION="$BUILD_VERSION" \
  -t loom/kafka-python-base:3.11-slim \
  -t loom/kafka-python-base:latest \
  "$SCRIPT_DIR/kafka-python-base"

# Build fastapi-base
echo "Building loom/fastapi-base:3.11-slim..."
docker build \
  --build-arg BUILD_DATE="$BUILD_DATE" \
  --build-arg GIT_COMMIT="$GIT_COMMIT" \
  --build-arg BUILD_VERSION="$BUILD_VERSION" \
  -t loom/fastapi-base:3.11-slim \
  -t loom/fastapi-base:latest \
  "$SCRIPT_DIR/fastapi-base"

echo "Base images built successfully!"

# Optional: Show image sizes
echo ""
echo "Image sizes:"
docker images | grep "loom/" | grep -E "(python-base|kafka-python-base|fastapi-base)"
