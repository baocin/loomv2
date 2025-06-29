# Base Python image for all Loom v2 Python services
FROM python:3.11-slim

# Build arguments for metadata
ARG BUILD_DATE=unknown
ARG GIT_COMMIT=unknown
ARG BUILD_VERSION=latest

# Labels for tracking
LABEL org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.version="${BUILD_VERSION}" \
      org.opencontainers.image.title="loom-python-base" \
      org.opencontainers.image.description="Base Python image for Loom v2 services"

# Set timezone to prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive \
    TZ=UTC

# Install common system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Build essentials for Python packages with C extensions
    gcc \
    g++ \
    # Network utilities for health checks
    curl \
    netcat-traditional \
    # Time zone data
    tzdata \
    # Clean up
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install uv for faster Python package installation
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Create non-root user with consistent UID/GID
RUN useradd -m -u 1000 -s /bin/bash appuser

# Set up Python environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create app directory
WORKDIR /app
RUN chown appuser:appuser /app

# Install common Python build tools
RUN pip install --no-cache-dir \
    setuptools>=61.0 \
    wheel>=0.40.0 \
    pip>=23.0

# Add healthcheck script
COPY --chown=appuser:appuser healthcheck.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/healthcheck.sh

# Default to non-root user (services can override if needed)
USER appuser

# Common healthcheck (services should override with specific checks)
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD /usr/local/bin/healthcheck.sh || exit 1
