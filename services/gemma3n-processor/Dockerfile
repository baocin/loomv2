# Multi-stage build for Gemma 3N Processor
FROM python:3.11-slim AS base

# Security hardening
RUN groupadd -r app && useradd -r -g app app
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies  
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .[dev]

# Copy application code
COPY app/ ./app/
COPY tests/ ./tests/

# Create ollama models directory and set permissions
RUN mkdir -p /app/.ollama && chown -R app:app /app/.ollama
ENV OLLAMA_MODELS=/app/.ollama/models

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Switch to non-root user
USER app

# Expose ports
EXPOSE 8000 11434

# Default command - starts both Ollama server and FastAPI app
CMD ["sh", "-c", "ollama serve & sleep 5 && ollama pull gemma3n:e4b && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"]