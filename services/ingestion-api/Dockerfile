# Multi-stage Dockerfile for Ingestion API Service

# Stage 1: Build environment
FROM python:3.11-slim as builder

# Set timezone to prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive \
    TZ=UTC

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster dependency installation
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./

# Create virtual environment and install dependencies
RUN uv venv .venv && \
    . .venv/bin/activate && \
    uv pip install -e .

# Stage 2: Runtime environment
FROM python:3.11-slim

# Git commit information (passed as build args)
ARG GIT_COMMIT=unknown
ARG GIT_BRANCH=unknown
ARG BUILD_DATE=unknown
ARG BUILD_VERSION=latest

# Add labels for tracking
LABEL org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${GIT_COMMIT}" \
      org.opencontainers.image.version="${BUILD_VERSION}" \
      org.opencontainers.image.source="https://github.com/loomv2/loomv2" \
      org.opencontainers.image.title="loom-ingestion-api" \
      org.opencontainers.image.description="Loom v2 Ingestion API Service" \
      com.loomv2.git.commit="${GIT_COMMIT}" \
      com.loomv2.git.branch="${GIT_BRANCH}"

# Set timezone to prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive \
    TZ=UTC

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    netcat-traditional \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash appuser

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --chown=appuser:appuser app/ ./app/
COPY --chown=appuser:appuser migrations/ ./migrations/

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Switch to non-root user
USER appuser

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Run the API
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
