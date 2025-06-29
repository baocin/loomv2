# Kafka-enabled Python base image for Loom v2 services
FROM loom/python-base:3.11-slim

# Build arguments for metadata
ARG BUILD_DATE=unknown
ARG GIT_COMMIT=unknown
ARG BUILD_VERSION=latest

# Labels for tracking
LABEL org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.version="${BUILD_VERSION}" \
      org.opencontainers.image.title="loom-kafka-python-base" \
      org.opencontainers.image.description="Kafka-enabled Python base for Loom v2 services"

# Switch to root for installations
USER root

# Create directory for common requirements
WORKDIR /tmp/build

# Install common Kafka and utility packages
RUN pip install --no-cache-dir \
    # Kafka libraries
    aiokafka>=0.10.0 \
    kafka-python>=2.0.2 \
    # Logging and configuration
    structlog>=24.0.0 \
    python-dotenv>=1.0.0 \
    # Serialization and validation
    pydantic>=2.0.0 \
    pydantic-settings>=2.0.0 \
    # Common utilities
    python-dateutil>=2.8.0 \
    # Async utilities
    aiofiles>=23.0.0 \
    # JSON handling
    orjson>=3.9.0

# Install the loom-common package if it exists
# This will be updated once we create the package
# RUN pip install --no-cache-dir loom-common

# Switch back to app directory and non-root user
WORKDIR /app
USER appuser

# Environment variables for Kafka
ENV LOOM_KAFKA_BOOTSTRAP_SERVERS=localhost:9092 \
    LOOM_KAFKA_TOPIC_PREFIX="" \
    LOOM_LOG_LEVEL=INFO
