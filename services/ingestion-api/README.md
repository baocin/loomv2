# Ingestion API Service

Core data ingestion service for Loom v2 that provides REST and WebSocket endpoints for device data.

## Features

- REST API for sensor data ingestion (GPS, accelerometer, heart rate, etc.)
- WebSocket support for real-time audio streaming
- Schema validation using JSON Schema
- Automatic Kafka topic publishing
- Health check and metrics endpoints

## Configuration

See the service's environment variables in docker-compose.local.yml for configuration options.
