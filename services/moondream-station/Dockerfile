# Multi-stage build for Moondream Station
FROM ubuntu:22.04 AS base

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    python3.11 \
    python3.11-venv \
    python3-pip \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r app && useradd -r -g app app

# Set working directory
WORKDIR /app

# Install Moondream Station
RUN curl -fsSL https://depot.moondream.ai/station/install.sh | bash || \
    (echo "Fallback: Manual installation" && \
     mkdir -p /usr/local/bin && \
     wget -O /usr/local/bin/moondream https://depot.moondream.ai/station/latest/moondream-linux-x86_64 && \
     chmod +x /usr/local/bin/moondream)

# Copy Python requirements and install
COPY pyproject.toml .
RUN python3.11 -m pip install --no-cache-dir -e .

# Copy application code
COPY app/ ./app/
COPY tests/ ./tests/

# Create data directory
RUN mkdir -p /app/data && chown -R app:app /app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Switch to non-root user
USER app

# Expose ports
EXPOSE 8000 2020

# Environment variables
ENV MOONDREAM_HOST="0.0.0.0"
ENV MOONDREAM_PORT="2020"
ENV PYTHONUNBUFFERED=1

# Start both Moondream Station and FastAPI wrapper
CMD ["sh", "-c", "moondream serve --host 0.0.0.0 --port 2020 & sleep 10 && python3.11 -m uvicorn app.main:app --host 0.0.0.0 --port 8000"]