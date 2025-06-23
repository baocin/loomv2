# Loom v2 Scripts

This directory contains utility scripts for the Loom v2 project.

## Scripts

### e2e_test_pipeline.py

End-to-end pipeline test that validates the complete data flow from API → Kafka → Database.

**Features:**
- Tests all API endpoints with realistic test data
- Verifies data reaches correct Kafka topics
- Injects simulated AI-processed data
- Verifies data persistence in TimescaleDB
- Provides detailed pass/fail report

**Requirements:**
- Development environment running (`make dev-up`)
- Python dependencies installed (`pip install -r scripts/requirements.txt`)

**Usage:**
```bash
# Run the e2e test
make test-e2e

# Or run directly
python scripts/e2e_test_pipeline.py
```

**Test Coverage:**
- Audio upload endpoint
- Image/screenshot upload endpoints
- All sensor endpoints (GPS, accelerometer, heart rate, power)
- System monitoring endpoints (macOS apps, device metadata)
- Notes endpoints (device notes, digital notes)
- URL ingestion endpoint
- Processed data injection for AI pipeline simulation

### create_topics.sh

Creates all required Kafka topics for the Loom v2 pipeline.

**Usage:**
```bash
make topics-create
```

## Dependencies

Install script dependencies:
```bash
pip install -r scripts/requirements.txt
```

Required packages:
- `aiohttp` - Async HTTP client for API testing
- `asyncpg` - PostgreSQL async driver
- `aiokafka` - Kafka async client
- `structlog` - Structured logging
