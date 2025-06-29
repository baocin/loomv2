# Migration Guide: Using Base Images and Loom Common

This guide explains how to migrate existing services to use the new base Docker images and loom-common package.

## Overview

The new architecture provides:
- **Base Docker images** with common dependencies pre-installed
- **loom-common package** with shared code patterns
- **Multi-stage builds** for smaller, more secure images

## Base Images

### Available Images

1. **loom/python-base:3.11-slim**
   - Base Python 3.11 with system dependencies
   - Non-root user setup
   - uv for fast package installation

2. **loom/kafka-python-base:3.11-slim**
   - Extends python-base
   - Includes Kafka libraries (aiokafka, kafka-python)
   - Common utilities (structlog, pydantic)

3. **loom/fastapi-base:3.11-slim**
   - Extends kafka-python-base
   - FastAPI stack pre-installed
   - Database drivers included

## Migration Steps

### 1. Update Dockerfile to Multi-Stage Build

**Before:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y gcc
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app/ ./app/
CMD ["python", "app/main.py"]
```

**After:**
```dockerfile
# Stage 1: Builder
FROM loom/python-base:3.11-slim as builder
USER root
WORKDIR /app
RUN python -m venv .venv
ENV PATH="/app/.venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM loom/kafka-python-base:3.11-slim
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
COPY --chown=appuser:appuser app/ ./app/
CMD ["python", "app/main.py"]
```

### 2. Update Dependencies

Remove common dependencies from your `requirements.txt` that are already in base images:
- aiokafka
- kafka-python
- structlog
- pydantic
- python-dotenv

Keep only service-specific dependencies.

### 3. Use Loom Common

Replace custom Kafka producer/consumer code:

**Before:**
```python
# app/kafka_producer.py
class KafkaProducer:
    def __init__(self):
        self.producer = KP(
            bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS"),
            # ... custom config
        )
```

**After:**
```python
# app/main.py
from loom_common.kafka import BaseKafkaProducer
from loom_common.config import BaseSettings
from loom_common.logging import setup_logging

class Settings(BaseSettings):
    # Add service-specific settings
    calendar_fetch_interval: int = 30

settings = Settings()
logger = setup_logging("calendar-fetcher", settings)

class CalendarProducer(BaseKafkaProducer):
    async def send_event(self, event_data):
        await self.send_message("calendar.events", event_data)
```

### 4. Update Environment Variables

Standardize environment variable names:
- `KAFKA_BOOTSTRAP_SERVERS` → `LOOM_KAFKA_BOOTSTRAP_SERVERS`
- `LOG_LEVEL` → `LOOM_LOG_LEVEL`
- Add `LOOM_SERVICE_NAME=your-service-name`

### 5. Add Health Checks (for API services)

```python
from fastapi import FastAPI
from loom_common.health import create_health_router, HealthChecker
from loom_common.health.checks import kafka_health_check

app = FastAPI()

# Configure health checks
health_checker = HealthChecker()
health_checker.add_check(
    "kafka",
    lambda: kafka_health_check(settings.kafka_bootstrap_servers)
)

# Add health endpoints
app.include_router(create_health_router(health_checker))
```

## Benefits

### Image Size Reduction
- **Before**: 400-1400MB per service
- **After**: 150-250MB per service

### Build Time
- Faster builds due to layer caching
- Common dependencies cached in base images

### Maintenance
- Update base image to update all services
- Consistent patterns across services
- Less code duplication

## Testing

1. Build base images:
   ```bash
   cd docker/base-images
   ./build.sh
   ```

2. Build your service:
   ```bash
   docker build -f Dockerfile.multistage -t my-service:test .
   ```

3. Compare image sizes:
   ```bash
   docker images | grep my-service
   ```

4. Run tests to ensure functionality:
   ```bash
   docker run --rm my-service:test python -m pytest
   ```

## Rollback

If issues arise, the original Dockerfiles are preserved and can be used by reverting the changes.

## Support

For questions or issues, consult the team or refer to the loom-common documentation.
