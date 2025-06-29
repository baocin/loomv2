# FastAPI base image for Loom v2 API services
FROM loom/kafka-python-base:3.11-slim

# Build arguments for metadata
ARG BUILD_DATE=unknown
ARG GIT_COMMIT=unknown
ARG BUILD_VERSION=latest

# Labels for tracking
LABEL org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.version="${BUILD_VERSION}" \
      org.opencontainers.image.title="loom-fastapi-base" \
      org.opencontainers.image.description="FastAPI base for Loom v2 API services"

# Switch to root for installations
USER root

# Install FastAPI stack and database drivers
RUN pip install --no-cache-dir \
    # FastAPI and server
    fastapi>=0.110.0 \
    uvicorn[standard]>=0.25.0 \
    # Database
    asyncpg>=0.29.0 \
    # HTTP client
    httpx>=0.25.0 \
    # File handling
    python-multipart>=0.0.6 \
    # WebSocket support
    websockets>=12.0 \
    # Metrics
    prometheus-client>=0.19.0 \
    # API documentation
    python-jose[cryptography]>=3.3.0

# Expose common API port
EXPOSE 8000

# Switch back to non-root user
USER appuser

# Default command for API services
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Override health check for API services
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1
