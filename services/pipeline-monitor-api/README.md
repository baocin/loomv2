# Pipeline Monitor API - Backend

Backend service providing real-time monitoring data for the Loom v2 data pipeline.

## Features

- **Kafka Monitoring**: Topic metrics, consumer lag, message throughput
- **Database Metrics**: TimescaleDB health, table statistics, query performance
- **WebSocket Support**: Real-time updates to connected clients
- **REST API**: Comprehensive endpoints for all monitoring data
- **Caching Layer**: Efficient message caching for quick access

## Development

```bash
# Install dependencies
make install

# Start development server with hot reload
make dev

# Build TypeScript
make build

# Run production server
make start

# Run with Docker
make docker
make docker-run
```

## API Endpoints

### Health & Status
- `GET /health` - System health overview
- `GET /health/ready` - Readiness probe
- `GET /health/live` - Liveness probe

### Kafka Monitoring
- `GET /api/kafka/topics` - List all topics
- `GET /api/kafka/topics/metrics` - Topic metrics (messages, lag, rates)
- `GET /api/kafka/topics/:topic/latest` - Latest message from topic
- `GET /api/kafka/consumers` - List consumer groups
- `GET /api/kafka/consumers/metrics` - Consumer metrics

### Database Monitoring
- `GET /api/database/metrics` - Database overview (size, connections, queries)
- `GET /api/database/tables` - Table statistics

### WebSocket
- `ws://localhost:8080/ws` - Real-time metrics updates

## Environment Variables

See `.env.example` for configuration:
- Kafka connection settings
- TimescaleDB/PostgreSQL credentials
- CORS configuration
- Cache and monitoring intervals

## Architecture

The API connects to:
- **Kafka**: Using KafkaJS for topic and consumer monitoring
- **TimescaleDB**: Using pg client for database metrics
- **WebSocket**: Broadcasting updates every 5 seconds

Built with:
- Node.js + Express + TypeScript
- KafkaJS for Kafka integration
- pg for PostgreSQL/TimescaleDB
- ws for WebSocket support
