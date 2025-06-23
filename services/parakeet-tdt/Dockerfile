# Multi-stage Dockerfile for Parakeet-TDT service

# Stage 1: Base image with CUDA support
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04 AS base

# Install Python 3.11
RUN apt-get update && apt-get install -y \
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3.11-distutils \
    python3-pip \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.11 as default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 \
    && update-alternatives --set python3 /usr/bin/python3.11

# Install uv for package management
RUN pip3 install --no-cache-dir uv

# Stage 2: Builder
FROM base AS builder

WORKDIR /build

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies using uv
RUN uv pip install --system --no-cache -e .

# Stage 3: Runtime
FROM base AS runtime

# Create non-root user
RUN groupadd -r loom && useradd -r -g loom -m loom

# Set working directory
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/dist-packages /usr/local/lib/python3.11/dist-packages
COPY --from=builder /usr/lib/python3/dist-packages /usr/lib/python3/dist-packages

# Create model cache directory
RUN mkdir -p /models && chown -R loom:loom /models

# Copy application code
COPY --chown=loom:loom app/ ./app/

# Switch to non-root user
USER loom

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TRANSFORMERS_CACHE=/models \
    HF_HOME=/models \
    TORCH_HOME=/models

# Expose port
EXPOSE 8002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 -c "import requests; requests.get('http://localhost:8002/healthz').raise_for_status()"

# Run the application
CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]