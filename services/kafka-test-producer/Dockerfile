FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Create non-root user
RUN useradd -m -u 1000 testproducer && chown -R testproducer:testproducer /app

# Switch to non-root user
USER testproducer

# Expose port
EXPOSE 8008

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8008"]
