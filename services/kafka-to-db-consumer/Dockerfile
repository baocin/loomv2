FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# Copy application code and configuration
COPY app/ ./app/
COPY config/ ./config/

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8001/healthz || exit 1

# Expose port
EXPOSE 8001

# Run the application (use CONSUMER_TYPE env var to choose between 'legacy' and 'generic')
CMD ["sh", "-c", "if [ \"$CONSUMER_TYPE\" = \"generic\" ]; then python -m app.generic_consumer; else python -m app.main; fi"]
