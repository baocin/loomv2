# Lightweight Dockerfile for Mock VAD Processor
FROM python:3.11-slim

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy and install dependencies
COPY pyproject.toml ./
RUN uv venv .venv && \
    . .venv/bin/activate && \
    uv pip install -e .

# Copy application code
COPY app/ ./app/

# Set environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Create non-root user
RUN useradd -m -u 1000 appuser
USER appuser

# Expose metrics port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8001/metrics || exit 1

# Run the service
CMD ["python", "-m", "app.main"]