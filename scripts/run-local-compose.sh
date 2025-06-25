#!/bin/bash
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting Loom v2 Local Development Environment (Docker Compose)${NC}"

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  docker-compose not found. Using 'docker compose' instead.${NC}"
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

# Build images first
echo -e "${YELLOW}🔨 Building Docker images...${NC}"
$COMPOSE_CMD -f docker-compose.local.yml build

# Start services
echo -e "${YELLOW}🚀 Starting services...${NC}"
$COMPOSE_CMD -f docker-compose.local.yml up -d

# Wait for services to be ready
echo -e "${YELLOW}⏳ Waiting for services to be ready...${NC}"

# Wait for PostgreSQL
echo -n "Waiting for PostgreSQL"
for i in {1..30}; do
    if docker exec $(docker ps -q -f name=postgres) pg_isready -U loom -d loom >/dev/null 2>&1; then
        echo -e " ${GREEN}✓${NC}"
        break
    fi
    echo -n "."
    sleep 2
    if [ $i -eq 30 ]; then
        echo -e " ${RED}✗ PostgreSQL failed to start${NC}"
        exit 1
    fi
done

# Wait for Kafka
echo -n "Waiting for Kafka"
for i in {1..30}; do
    if docker exec $(docker ps -q -f name=kafka) kafka-topics --bootstrap-server localhost:9092 --list >/dev/null 2>&1; then
        echo -e " ${GREEN}✓${NC}"
        break
    fi
    echo -n "."
    sleep 2
    if [ $i -eq 30 ]; then
        echo -e " ${RED}✗ Kafka failed to start${NC}"
        exit 1
    fi
done

# Wait for Ingestion API
echo -n "Waiting for Ingestion API"
for i in {1..30}; do
    if curl -s http://localhost:8000/healthz >/dev/null 2>&1; then
        echo -e " ${GREEN}✓${NC}"
        break
    fi
    echo -n "."
    sleep 2
    if [ $i -eq 30 ]; then
        echo -e " ${RED}✗ Ingestion API failed to start${NC}"
        exit 1
    fi
done

echo -e "${GREEN}🎉 All services are ready!${NC}"
echo ""
echo -e "${BLUE}📍 Service URLs:${NC}"
echo -e "  • Ingestion API: ${GREEN}http://localhost:8000${NC}"
echo -e "  • API Docs: ${GREEN}http://localhost:8000/docs${NC}"
echo -e "  • Kafka UI: ${GREEN}http://localhost:8081${NC}"
echo -e "  • PostgreSQL: ${GREEN}localhost:5432${NC} (loom/loom/loom)"
echo ""
echo -e "${BLUE}🔧 Useful Commands:${NC}"
echo -e "  • View logs: ${YELLOW}$COMPOSE_CMD -f docker-compose.local.yml logs -f${NC}"
echo -e "  • Stop services: ${YELLOW}$COMPOSE_CMD -f docker-compose.local.yml down${NC}"
echo -e "  • Run tests: ${YELLOW}./scripts/test-local-compose.sh${NC}"
echo ""

# Run basic smoke tests
echo -e "${YELLOW}🧪 Running smoke tests...${NC}"

# Test health endpoint
if curl -s http://localhost:8000/healthz | grep -q "ok"; then
    echo -e "  ✓ Health endpoint: ${GREEN}OK${NC}"
else
    echo -e "  ✗ Health endpoint: ${RED}FAILED${NC}"
fi

# Test readiness endpoint
if curl -s http://localhost:8000/readyz | grep -q "ready"; then
    echo -e "  ✓ Readiness endpoint: ${GREEN}OK${NC}"
else
    echo -e "  ✗ Readiness endpoint: ${RED}FAILED${NC}"
fi

# Test database connection
if docker exec $(docker ps -q -f name=postgres) psql -U loom -d loom -c "SELECT 1" >/dev/null 2>&1; then
    echo -e "  ✓ Database connection: ${GREEN}OK${NC}"
else
    echo -e "  ✗ Database connection: ${RED}FAILED${NC}"
fi

echo ""
echo -e "${GREEN}🚀 Loom v2 is running successfully!${NC}"
