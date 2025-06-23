# Multi-stage build for Silero VAD service
ARG PYTHON_VERSION=3.11

# Build stage - install dependencies
FROM python:${PYTHON_VERSION}-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
ENV UV_VERSION=0.5.8
RUN curl -LsSf https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-installer.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies
RUN uv venv && \
    . .venv/bin/activate && \
    uv pip install -e .

# Download Silero VAD model during build to cache it
RUN . .venv/bin/activate && \
    python -c "import torch; torch.hub.load('snakers4/silero-vad', 'silero_vad', force_reload=False)"

# Runtime stage
FROM python:${PYTHON_VERSION}-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash appuser

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy torch hub cache
COPY --from=builder /root/.cache/torch /home/appuser/.cache/torch
RUN chown -R appuser:appuser /home/appuser/.cache

# Copy application code
COPY --chown=appuser:appuser app/ ./app/

# Set environment variables
ENV PATH="/app/.venv/bin:${PATH}"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import httpx; r = httpx.get('http://localhost:8001/healthz'); r.raise_for_status()"

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]