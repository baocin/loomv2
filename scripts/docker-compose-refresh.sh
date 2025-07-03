#!/bin/bash
# Optimized Docker Compose refresh script
# Only rebuilds the last layer of containers for faster development

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Enable Docker BuildKit for better caching
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1
export BUILDKIT_PROGRESS=plain

# Git metadata for labels
export GIT_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
export GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
export BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
export BUILD_VERSION=$(git describe --tags --always 2>/dev/null || echo "latest")

# Service name from argument
SERVICE=$1

echo -e "${BLUE}🔄 Docker Compose Refresh - Minimal Layer Rebuild${NC}"
echo -e "${YELLOW}💡 Using BuildKit cache for maximum efficiency${NC}"
echo ""

# Function to check if a service exists
service_exists() {
    docker compose -f docker-compose.local.yml config --services | grep -q "^$1$"
}

# Function to get the last build time of an image
get_image_build_time() {
    local service=$1
    local image_name="loomv2-${service}"
    docker inspect "${image_name}:latest" --format='{{.Created}}' 2>/dev/null || echo "never"
}

# Function to check if source files have changed
files_changed_since() {
    local service=$1
    local timestamp=$2

    # Map service to directory
    local service_dir=""
    case $service in
        ingestion-api|kafka-to-db-consumer|pipeline-monitor*)
            service_dir="services/${service}"
            ;;
        *)
            service_dir="services/${service}"
            ;;
    esac

    if [ -d "$service_dir" ]; then
        # Check if any files in the service directory are newer than the timestamp
        find "$service_dir" -type f -newer <(date -d "$timestamp" "+%Y%m%d%H%M.%S" | xargs touch -t) 2>/dev/null | head -1
    fi
}

if [ -z "$SERVICE" ]; then
    # Build all services
    echo -e "${YELLOW}📦 Refreshing all services...${NC}"

    # Get list of all services
    SERVICES=$(docker compose -f docker-compose.local.yml config --services)

    # Build only services that have changed
    for svc in $SERVICES; do
        last_build=$(get_image_build_time "$svc")
        if [ "$last_build" != "never" ] && [ -z "$(files_changed_since "$svc" "$last_build")" ]; then
            echo -e "${GREEN}✓ $svc is up to date (no changes detected)${NC}"
        else
            echo -e "${YELLOW}🔨 Building $svc (changes detected)...${NC}"
            docker compose -f docker-compose.local.yml build --no-cache=false "$svc"
        fi
    done

    # Recreate all containers
    echo -e "${BLUE}🔄 Recreating containers...${NC}"
    docker compose -f docker-compose.local.yml up -d --force-recreate --no-build

else
    # Build specific service
    if ! service_exists "$SERVICE"; then
        echo -e "${RED}❌ Service '$SERVICE' not found in docker-compose.local.yml${NC}"
        echo "Available services:"
        docker compose -f docker-compose.local.yml config --services | sed 's/^/  - /'
        exit 1
    fi

    echo -e "${YELLOW}📦 Refreshing $SERVICE...${NC}"

    # Check if rebuild is needed
    last_build=$(get_image_build_time "$SERVICE")
    if [ "$last_build" != "never" ] && [ -z "$(files_changed_since "$SERVICE" "$last_build")" ]; then
        echo -e "${GREEN}✓ $SERVICE is up to date (no changes detected)${NC}"
        echo -e "${BLUE}🔄 Restarting container anyway...${NC}"
        docker compose -f docker-compose.local.yml restart "$SERVICE"
    else
        echo -e "${YELLOW}🔨 Building $SERVICE (changes detected)...${NC}"

        # Build with cache
        docker compose -f docker-compose.local.yml build --no-cache=false "$SERVICE"

        # Recreate only this container
        echo -e "${BLUE}🔄 Recreating $SERVICE container...${NC}"
        docker compose -f docker-compose.local.yml up -d --no-deps --no-build "$SERVICE"
    fi
fi

echo ""
echo -e "${GREEN}✅ Refresh complete!${NC}"
echo ""
echo -e "${BLUE}📊 Useful commands:${NC}"
echo -e "  View logs: ${YELLOW}docker compose -f docker-compose.local.yml logs -f${NC}"
if [ -n "$SERVICE" ]; then
    echo -e "  View $SERVICE logs: ${YELLOW}docker compose -f docker-compose.local.yml logs -f $SERVICE${NC}"
fi
echo -e "  Check build cache: ${YELLOW}docker buildx du${NC}"
echo -e "  Clear build cache: ${YELLOW}docker buildx prune${NC}"
echo ""

# Show cache usage
echo -e "${BLUE}💾 Build cache status:${NC}"
docker buildx du --filter type=regular 2>/dev/null | head -5 || echo "BuildKit cache info not available"
