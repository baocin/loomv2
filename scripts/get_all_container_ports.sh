#!/bin/bash

# Script to display all container ports for Loom v2 services
# This helps identify which services are accessible and on which ports

echo "======================================"
echo "Loom v2 Container Ports"
echo "======================================"
echo ""

# Function to get container info
get_container_info() {
    local container_name=$1
    local container_info=$(docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep "^$container_name" | head -1)
    
    if [ -n "$container_info" ]; then
        echo "$container_info"
    else
        # Check if container exists but is not running
        local stopped_info=$(docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep "^$container_name" | head -1)
        if [ -n "$stopped_info" ]; then
            echo "$stopped_info"
        else
            echo "$container_name\tNot Found\t-"
        fi
    fi
}

# Print header
printf "%-40s %-25s %s\n" "CONTAINER" "STATUS" "PORTS"
printf "%-40s %-25s %s\n" "========================================" "=========================" "====================================="

# Core Services
echo -e "\n### Core Services ###"
get_container_info "loomv2-postgres-1"
get_container_info "loomv2-kafka-1"
get_container_info "loomv2-zookeeper-1"
get_container_info "loomv2-kafka-ui-1"

# API Services
echo -e "\n### API Services ###"
get_container_info "loomv2-ingestion-api-1"
get_container_info "loomv2-pipeline-monitor-api-1"
get_container_info "loomv2-pipeline-monitor-1"

# AI/ML Services
echo -e "\n### AI/ML Services ###"
get_container_info "loomv2-silero-vad-1"
get_container_info "loomv2-parakeet-tdt-1"
get_container_info "loomv2-kyutai-stt-1"
get_container_info "loomv2-minicpm-vision-1"
get_container_info "loomv2-bud-e-emotion-1"
get_container_info "loomv2-face-emotion-1"
get_container_info "loomv2-moondream-ocr-1"
get_container_info "loomv2-text-embedder-1"

# Data Fetchers
echo -e "\n### Data Fetchers ###"
get_container_info "loomv2-hackernews-fetcher-1"
get_container_info "loomv2-gmail-fetcher-1"
get_container_info "loomv2-fastmail-fetcher-1"
get_container_info "loomv2-calendar-fetcher-1"
get_container_info "loomv2-x-likes-fetcher-1"

# Processors
echo -e "\n### Processors ###"
get_container_info "loomv2-hackernews-url-processor-1"
get_container_info "loomv2-x-url-processor-1"
get_container_info "loomv2-twitter-ocr-processor-1"

# Consumers
echo -e "\n### Consumers ###"
get_container_info "loomv2-kafka-to-db-consumer-1"
get_container_info "loomv2-generic-kafka-to-db-consumer-1"
get_container_info "loomv2-scheduled-consumers-1"

# Test Services
echo -e "\n### Test Services ###"
get_container_info "loomv2-kafka-test-producer-1"

echo -e "\n======================================"
echo "Service URLs:"
echo "======================================"
echo ""

# Function to check if port is open
check_port() {
    local port=$1
    local service=$2
    if nc -z localhost $port 2>/dev/null; then
        echo "✓ $service: http://localhost:$port"
    else
        echo "✗ $service: http://localhost:$port (not accessible)"
    fi
}

# Check main service endpoints
echo "### Web Interfaces ###"
check_port 3000 "Pipeline Monitor UI"
check_port 8081 "Kafka UI"

echo -e "\n### API Endpoints ###"
check_port 8000 "Ingestion API"
check_port 8082 "Pipeline Monitor API"

echo -e "\n### AI Services ###"
check_port 8001 "Silero VAD"
check_port 8002 "Parakeet TDT (STT)"
check_port 8003 "MiniCPM Vision"
check_port 8004 "BUD-E Emotion"
check_port 8005 "Face Emotion"
check_port 8006 "Text Embedder"
check_port 8007 "Moondream OCR"
check_port 8008 "Kyutai STT"

echo -e "\n### Database & Messaging ###"
check_port 5432 "PostgreSQL"
check_port 9092 "Kafka"

echo -e "\n### Consumer Health Endpoints ###"
check_port 8009 "Generic Kafka-to-DB Consumer"

echo ""
echo "======================================"
echo "Quick Commands:"
echo "======================================"
echo "View logs for a service:  docker logs -f loomv2-<service>-1"
echo "Restart a service:        docker restart loomv2-<service>-1"
echo "View all containers:      docker ps -a | grep loomv2"
echo ""