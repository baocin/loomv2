# Dockerfile for Kyutai-STT service using Python base image
FROM python:3.11-slim

# Set timezone and locale to prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive \
    TZ=UTC \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    ffmpeg \
    libsndfile1 \
    curl \
    liblz4-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Create a directory for Hugging Face cache with proper permissions
RUN mkdir -p /tmp/cache && chmod -R 777 /tmp/cache

# Set Hugging Face cache to temp directory
ENV HF_HOME=/tmp/cache \
    TRANSFORMERS_CACHE=/tmp/cache \
    TORCH_HOME=/tmp/cache

# Copy application code
COPY app/ ./app/

# Expose port
EXPOSE 8002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=5 \
    CMD curl -f http://localhost:8002/healthz || exit 1

# Run the application as root to avoid permission issues
CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
