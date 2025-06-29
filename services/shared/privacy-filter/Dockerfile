# Multi-stage build for Privacy Filter Service
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast package management
RUN pip install uv

# Set working directory
WORKDIR /build

# Copy requirements and install dependencies
COPY requirements.txt .
RUN uv pip install --system --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

# Create non-root user
RUN groupadd -r loom && useradd -r -g loom loom

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Set working directory
WORKDIR /app

# Copy application code
COPY app/ ./app/

# Create directories and set permissions
RUN mkdir -p /app/data /app/logs && \
    chown -R loom:loom /app

# Switch to non-root user
USER loom

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8011/health || exit 1

# Expose port
EXPOSE 8011

# Run the application
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8011"]
