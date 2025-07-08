# Dockerfile for ONNX-ASR service using Parakeet TDT model
FROM nvidia/cuda:12.2.2-cudnn8-runtime-ubuntu22.04

# Set timezone and locale to prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive \
    TZ=UTC \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    CUDA_VISIBLE_DEVICES=0

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-venv \
    python3-pip \
    gcc \
    g++ \
    git \
    ffmpeg \
    libsndfile1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set python3.11 as the default python3
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# Set working directory
WORKDIR /app

# Copy dependency files and application code
COPY pyproject.toml setup.py ./
COPY app/ ./app/

# Upgrade pip and install dependencies
RUN python3 -m pip install --upgrade pip setuptools wheel && \
    python3 -m pip install --no-cache-dir -e .

# Create a directory for Hugging Face cache with proper permissions
RUN mkdir -p /tmp/cache && chmod -R 777 /tmp/cache

# Set Hugging Face cache to temp directory
ENV HF_HOME=/tmp/cache \
    TRANSFORMERS_CACHE=/tmp/cache \
    TORCH_HOME=/tmp/cache

# Expose port
EXPOSE 8002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=5 \
    CMD curl -f http://localhost:8002/healthz || exit 1

# Run the application
CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
