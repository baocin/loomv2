# Loom v2 Base Docker Images

This directory contains the base Docker images used by all Loom v2 services. These images provide common dependencies and configurations to reduce duplication and improve build times.

## Base Images

### 1. `loom/python-base:3.11-slim`
The foundation image for all Python services.

**Includes:**
- Python 3.11 slim base
- System dependencies (gcc, curl, netcat, tzdata)
- uv package manager for fast installs
- Non-root user setup (appuser)
- Basic health check script

**Use for:** Any Python service that doesn't need Kafka

### 2. `loom/kafka-python-base:3.11-slim`
Extends python-base with Kafka and common Python libraries.

**Additional includes:**
- aiokafka & kafka-python
- structlog for structured logging
- pydantic for data validation
- python-dotenv for configuration
- Common utilities (dateutil, orjson)

**Use for:** Services that interact with Kafka (consumers, producers)

### 3. `loom/fastapi-base:3.11-slim`
Extends kafka-python-base with FastAPI stack.

**Additional includes:**
- FastAPI & uvicorn
- asyncpg for PostgreSQL
- httpx for HTTP client
- prometheus-client for metrics
- WebSocket support

**Use for:** API services and web endpoints

## Building Base Images

### Quick Build
```bash
# From project root
make base-images

# Or directly
cd docker/base-images
./build.sh
```

### Manual Build
```bash
cd docker/base-images

# Build python-base
docker build -t loom/python-base:3.11-slim python-base/

# Build kafka-python-base
docker build -t loom/kafka-python-base:3.11-slim kafka-python-base/

# Build fastapi-base
docker build -t loom/fastapi-base:3.11-slim fastapi-base/
```

## Using Base Images

### Example: Simple Kafka Consumer
```dockerfile
FROM loom/kafka-python-base:3.11-slim

# Copy only service-specific requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY --chown=appuser:appuser app/ ./app/

# Service runs as non-root by default
CMD ["python", "app/main.py"]
```

### Example: Multi-Stage Build for Smaller Image
```dockerfile
# Builder stage
FROM loom/python-base:3.11-slim as builder
USER root
WORKDIR /app
RUN python -m venv .venv
ENV PATH="/app/.venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM loom/kafka-python-base:3.11-slim
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
COPY --chown=appuser:appuser app/ ./app/
CMD ["python", "app/main.py"]
```

## Benefits

### 1. Reduced Image Sizes
- Shared layers across services
- No duplicate common dependencies
- Multi-stage builds remove build artifacts

### 2. Faster Builds
- Common dependencies cached in base images
- Only service-specific deps need installation
- Better Docker layer caching

### 3. Consistency
- Same Python version across all services
- Standardized user setup and permissions
- Common environment variables

### 4. Security
- Non-root user by default
- Minimal attack surface
- Regular base image updates apply to all services

## Maintenance

### Updating Base Images
1. Modify Dockerfile in appropriate directory
2. Run `make base-images` to rebuild
3. Test with a sample service
4. Update all services to use new base

### Version Management
- Tag images with version numbers for production
- Use `latest` tag for development
- Consider automated builds in CI/CD

## Environment Variables

Base images set these defaults:
- `PYTHONUNBUFFERED=1` - Immediate output
- `PYTHONDONTWRITEBYTECODE=1` - No .pyc files
- `TZ=UTC` - Consistent timezone
- `PATH` includes `/app/.venv/bin` for virtual envs

Kafka images add:
- `LOOM_KAFKA_BOOTSTRAP_SERVERS=localhost:9092`
- `LOOM_KAFKA_TOPIC_PREFIX=""`
- `LOOM_LOG_LEVEL=INFO`

## Troubleshooting

### Image not found
```bash
# Ensure base images are built
make base-images
```

### Permission issues
```bash
# Files should be owned by appuser (UID 1000)
COPY --chown=appuser:appuser app/ ./app/
```

### Missing dependencies
Check if dependency should be:
1. In base image (common to many services)
2. In service requirements (service-specific)

## Future Enhancements

- [ ] Add Node.js base images for frontend services
- [ ] Create ML-specific base with PyTorch/TensorFlow
- [ ] Add base images for other languages (Go, Rust)
- [ ] Implement vulnerability scanning in build process
- [ ] Set up automated base image rebuilds
