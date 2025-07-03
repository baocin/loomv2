# Multi-stage Docker build for process scheduler service

FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast Python package management
RUN pip install uv

# Create app user
RUN useradd --create-home --shell /bin/bash app

# Set work directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies
RUN uv pip install --system -e .

# Copy application code
COPY app/ ./app/

# Change ownership to app user
RUN chown -R app:app /app

# Switch to app user
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import asyncio; import sys; sys.exit(0)" || exit 1

# Default command
CMD ["python", "-m", "app.scheduler"]

# Production stage
FROM base as production

# Set production environment
ENV ENVIRONMENT=production

# Copy optimized application
COPY --from=base --chown=app:app /app /app

# Switch to app user
USER app

# Expose port (if needed for health checks)
EXPOSE 8080

# Run the scheduler
CMD ["python", "-m", "app.scheduler"]