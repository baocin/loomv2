# Nomic Embed Vision Service Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy pyproject.toml first for dependency caching
COPY pyproject.toml ./

# Install Python dependencies
RUN uv sync --frozen

# Create models cache directory
RUN mkdir -p ./models && chmod 755 ./models

# Copy application code
COPY app/ ./app/

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Set Python path
ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:$PATH"

# Set model cache directory
ENV NOMIC_EMBED_MODEL_CACHE_DIR="/app/models"
ENV TRANSFORMERS_CACHE="/app/models"
ENV HF_HOME="/app/models"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8004/healthz', timeout=10)" || exit 1

# Expose port
EXPOSE 8004

# Run the application
CMD ["python", "-m", "app.main"]