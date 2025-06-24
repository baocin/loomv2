# OneFileLLM Service Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy pyproject.toml first for dependency caching
COPY pyproject.toml ./

# Install Python dependencies
RUN uv sync --frozen

# Clone OneFileLLM repository
RUN git clone https://github.com/raphaelsty/onefilellm.git /tmp/onefilellm

# Install OneFileLLM
RUN cd /tmp/onefilellm && \
    /app/.venv/bin/pip install -e .

# Copy application code
COPY app/ ./app/

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Set Python path
ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:$PATH"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# Expose port
EXPOSE 8080

# Run the application
CMD ["python", "-m", "app.main"]
