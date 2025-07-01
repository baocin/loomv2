FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV LOOM_LOG_LEVEL=INFO

# Expose port for health checks
EXPOSE 8000

# Run the service
CMD ["python", "-m", "app.main"]