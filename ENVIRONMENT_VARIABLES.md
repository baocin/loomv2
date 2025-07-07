# Loom v2 Environment Variables Documentation

This document provides a comprehensive reference for all environment variables used across the Loom v2 system. All environment variables follow the `LOOM_` prefix convention for consistency.

## Table of Contents

1. [Core Configuration](#core-configuration)
2. [Ingestion API Service](#ingestion-api-service)
3. [Kafka Configuration](#kafka-configuration)
4. [Database Configuration](#database-configuration)
5. [AI Services](#ai-services)
6. [Fetcher Services](#fetcher-services)
7. [Consumer Services](#consumer-services)
8. [Monitoring Services](#monitoring-services)

## Core Configuration

These variables are used across multiple services:

| Variable | Description | Default | Services |
|----------|-------------|---------|----------|
| `LOOM_ENVIRONMENT` | Environment (development/production) | `development` | All |
| `LOOM_LOG_LEVEL` | Logging level (DEBUG/INFO/WARNING/ERROR) | `INFO` | All |
| `LOOM_DEBUG` | Enable debug mode | `false` | All |

## Ingestion API Service

Core data ingestion service configuration:

| Variable | Description | Default |
|----------|-------------|---------|
| `LOOM_HOST` | API server host | `0.0.0.0` |
| `LOOM_PORT` | API server port | `8000` |
| `LOOM_CORS_ORIGINS` | CORS allowed origins (comma-separated) | `*` |
| `LOOM_API_KEY` | API authentication key | None (optional) |
| `LOOM_MAX_REQUEST_SIZE` | Maximum request body size in bytes | `10485760` (10MB) |

## Kafka Configuration

Common Kafka settings used by all services:

| Variable | Description | Default |
|----------|-------------|---------|
| `LOOM_KAFKA_BOOTSTRAP_SERVERS` | Kafka broker addresses (comma-separated) | `localhost:9092` |
| `LOOM_KAFKA_TOPIC_PREFIX` | Prefix for all topic names | None |
| `LOOM_KAFKA_DEFAULT_PARTITIONS` | Default partitions for new topics | `3` |
| `LOOM_KAFKA_DEFAULT_REPLICATION_FACTOR` | Default replication factor | `1` |
| `LOOM_KAFKA_COMPRESSION_TYPE` | Compression type (none/gzip/snappy/lz4) | `lz4` |
| `LOOM_KAFKA_MAX_MESSAGE_SIZE` | Maximum message size in bytes | `1048576` (1MB) |
| `LOOM_KAFKA_BATCH_SIZE` | Producer batch size | `16384` |
| `LOOM_KAFKA_LINGER_MS` | Producer linger time in ms | `10` |

### Consumer-Specific Kafka Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `LOOM_KAFKA_AUTO_OFFSET_RESET` | Auto offset reset (earliest/latest) | `earliest` |
| `LOOM_KAFKA_ENABLE_AUTO_COMMIT` | Enable auto commit | `false` |
| `LOOM_KAFKA_MAX_POLL_RECORDS` | Max records per poll | `500` |
| `LOOM_KAFKA_SESSION_TIMEOUT_MS` | Session timeout in ms | `10000` |

## Database Configuration

PostgreSQL/TimescaleDB settings:

| Variable | Description | Default |
|----------|-------------|---------|
| `LOOM_DATABASE_URL` | PostgreSQL connection URL | `postgresql://loom:loom@localhost:5432/loom` |
| `LOOM_DATABASE_POOL_SIZE` | Connection pool size | `10` |
| `LOOM_DATABASE_MAX_OVERFLOW` | Max overflow connections | `20` |
| `LOOM_DATABASE_POOL_TIMEOUT` | Pool timeout in seconds | `30` |
| `LOOM_DATABASE_ECHO` | Echo SQL statements | `false` |

## AI Services

### Common AI Service Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `LOOM_AI_DEVICE` | Compute device (cuda/cpu) | `cpu` |
| `LOOM_AI_BATCH_SIZE` | Processing batch size | `1` |
| `LOOM_AI_MAX_RETRIES` | Max processing retries | `3` |

### Silero VAD Service

| Variable | Description | Default |
|----------|-------------|---------|
| `LOOM_VAD_MODEL_VERSION` | Silero VAD model version | `v4.0` |
| `LOOM_VAD_THRESHOLD` | Voice activity threshold | `0.5` |
| `LOOM_VAD_MIN_SPEECH_DURATION_MS` | Minimum speech duration | `250` |
| `LOOM_VAD_MIN_SILENCE_DURATION_MS` | Minimum silence duration | `100` |

### Kyutai STT Service

| Variable | Description | Default |
|----------|-------------|---------|
| `LOOM_STT_MODEL_NAME` | Kyutai model name | `kyutai/mimi` |
| `LOOM_STT_LANGUAGE` | Language code | `en` |
| `LOOM_STT_SAMPLE_RATE` | Audio sample rate | `16000` |

### MiniCPM Vision Service

| Variable | Description | Default |
|----------|-------------|---------|
| `LOOM_VISION_MODEL_NAME` | MiniCPM model name | `openbmb/MiniCPM-Llama3-V-2_5` |
| `LOOM_VISION_MAX_NEW_TOKENS` | Max generation tokens | `512` |
| `LOOM_VISION_TEMPERATURE` | Generation temperature | `0.7` |

### Moondream OCR Service

| Variable | Description | Default |
|----------|-------------|---------|
| `LOOM_OCR_MODEL_NAME` | Moondream model name | `vikhyatk/moondream2` |
| `LOOM_OCR_REVISION` | Model revision | `2024-05-20` |
| `LOOM_OCR_TRUST_REMOTE_CODE` | Trust remote code | `true` |

## Fetcher Services

### Calendar Fetcher

| Variable | Description | Default |
|----------|-------------|---------|
| `LOOM_CALENDAR_FETCH_INTERVAL_MINUTES` | Fetch interval in minutes | `30` |
| `LOOM_CALENDAR_RUN_ON_STARTUP` | Run on startup | `true` |
| `LOOM_CALENDAR_DAYS_PAST` | Days to fetch in past | `30` |
| `LOOM_CALENDAR_DAYS_FUTURE` | Days to fetch in future | `365` |
| `LOOM_CALENDAR_ENABLE_GPS_LOOKUP` | Enable location geocoding | `true` |
| `LOOM_CALENDAR_MAX_ACCOUNTS` | Max calendar accounts | `10` |

For each account N (1-10):
- `LOOM_CALDAV_URL_N` - CalDAV server URL
- `LOOM_CALDAV_USERNAME_N` - Username
- `LOOM_CALDAV_PASSWORD_N` - Password
- `LOOM_CALDAV_NAME_N` - Display name
- `LOOM_CALDAV_DISABLED_N` - Disable account

### Email Fetcher

| Variable | Description | Default |
|----------|-------------|---------|
| `LOOM_EMAIL_FETCH_INTERVAL_MINUTES` | Fetch interval in minutes | `5` |
| `LOOM_EMAIL_RUN_ON_STARTUP` | Run on startup | `true` |
| `LOOM_EMAIL_MAX_ACCOUNTS` | Max email accounts | `10` |
| `LOOM_EMAIL_SEARCH_CRITERIA` | IMAP search criteria | `UNSEEN` |
| `LOOM_EMAIL_MAX_FETCH_PER_ACCOUNT` | Max emails per fetch | `50` |

For each account N (1-10):
- `LOOM_EMAIL_ADDRESS_N` - Email address
- `LOOM_EMAIL_PASSWORD_N` - Password
- `LOOM_EMAIL_IMAP_SERVER_N` - IMAP server
- `LOOM_EMAIL_IMAP_PORT_N` - IMAP port
- `LOOM_EMAIL_NAME_N` - Display name
- `LOOM_EMAIL_DISABLED_N` - Disable account

### HackerNews Fetcher

| Variable | Description | Default |
|----------|-------------|---------|
| `LOOM_HACKERNEWS_FETCH_INTERVAL_MINUTES` | Fetch interval | `120` |
| `LOOM_HACKERNEWS_USERNAME` | HN username | Required |
| `LOOM_HACKERNEWS_PASSWORD` | HN password | None |
| `LOOM_HACKERNEWS_MAX_ITEMS` | Max items to fetch | `50` |
| `LOOM_HACKERNEWS_FETCH_TYPE` | favorites/submissions | `favorites` |

### X/Twitter Likes Fetcher

| Variable | Description | Default |
|----------|-------------|---------|
| `LOOM_X_FETCH_INTERVAL_MINUTES` | Fetch interval | `60` |
| `LOOM_X_USERNAME` | X username | Required |
| `LOOM_X_PASSWORD` | X password | Required |
| `LOOM_X_MAX_LIKES` | Max likes to fetch | `100` |

## Consumer Services

### Kafka to DB Consumer

| Variable | Description | Default |
|----------|-------------|---------|
| `LOOM_CONSUMER_GROUP_PREFIX` | Consumer group prefix | `loom` |
| `LOOM_CONSUMER_BATCH_SIZE` | Batch insert size | `1000` |
| `LOOM_CONSUMER_BATCH_TIMEOUT_MS` | Batch timeout | `5000` |
| `LOOM_CONSUMER_ENABLE_DB_CONFIG` | Use DB configuration | `true` |

### Georegion Detector

| Variable | Description | Default |
|----------|-------------|---------|
| `LOOM_GEOREGION_CHECK_INTERVAL_MS` | Check interval | `1000` |
| `LOOM_GEOREGION_TOLERANCE_METERS` | Location tolerance | `50` |

### GPS Geocoding Consumer

| Variable | Description | Default |
|----------|-------------|---------|
| `LOOM_GEOCODING_PROVIDER` | Provider (nominatim/google) | `nominatim` |
| `LOOM_NOMINATIM_BASE_URL` | Nominatim URL | `http://localhost:8080` |
| `LOOM_GOOGLE_MAPS_API_KEY` | Google Maps API key | None |

## Monitoring Services

### Pipeline Monitor

| Variable | Description | Default |
|----------|-------------|---------|
| `LOOM_MONITOR_API_URL` | Backend API URL | `http://localhost:3001` |
| `LOOM_MONITOR_REFRESH_INTERVAL_MS` | UI refresh interval | `5000` |

### Pipeline Monitor API

| Variable | Description | Default |
|----------|-------------|---------|
| `LOOM_MONITOR_API_PORT` | API server port | `3001` |
| `LOOM_MONITOR_ENABLE_CORS` | Enable CORS | `true` |

## Development & Testing

| Variable | Description | Default |
|----------|-------------|---------|
| `LOOM_TEST_MODE` | Enable test mode | `false` |
| `LOOM_MOCK_EXTERNAL_APIS` | Mock external APIs | `false` |
| `LOOM_DISABLE_TELEMETRY` | Disable telemetry | `false` |

## Docker Compose Specific

When using Docker Compose, these variables control service behavior:

| Variable | Description | Default |
|----------|-------------|---------|
| `COMPOSE_PROJECT_NAME` | Docker Compose project name | `loom` |
| `COMPOSE_FILE` | Compose file to use | `docker-compose.local.yml` |
| `COMPOSE_PROFILES` | Active profiles | None |

## Notes

1. **Security**: Never commit sensitive values (passwords, API keys) to version control. Use `.env` files or secret management systems.

2. **Precedence**: Environment variables override default values. Docker Compose `.env` files override system environment variables.

3. **Type Conversion**: Boolean values accept: `true/false`, `1/0`, `yes/no` (case-insensitive).

4. **Lists**: Comma-separated values are used for lists (e.g., `LOOM_KAFKA_BOOTSTRAP_SERVERS=kafka1:9092,kafka2:9092`).

5. **Service-Specific**: Some services may have additional undocumented environment variables. Check the service's `config.py` or documentation.

---

*Last updated: December 2024*
