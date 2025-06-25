# macOS Data Collection Client
FROM python:3.11-slim

# Set timezone to prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive \
    TZ=UTC

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast Python package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Create working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml README.md ./

# Create virtual environment and install dependencies
RUN uv venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN uv pip install --no-cache -e .

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash loom

# Create necessary directories and set permissions
RUN mkdir -p /app/data /app/logs && \
    chown -R loom:loom /app

# Copy application code
COPY --chown=loom:loom app/ ./app/

# Switch to non-root user
USER loom

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# Expose port
EXPOSE 8080

# Run the client
CMD ["python", "-m", "app.main"]
