# Use pre-built PyTorch image to avoid long build times
# Updated to 2.4.0 to support enable_gqa parameter in scaled_dot_product_attention
FROM pytorch/pytorch:2.4.0-cuda11.8-cudnn9-runtime

# Install additional dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements (excluding torch which is pre-installed)
COPY requirements-no-torch.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Create non-root user
RUN useradd -m -u 1000 moondream && chown -R moondream:moondream /app

# Create volume mount point as root before switching user
RUN mkdir -p /home/aoi/.loom/moondream && \
    chown -R moondream:moondream /home/aoi

# Switch to non-root user
USER moondream

# Set environment variable for model cache
ENV MOONDREAM_MODEL_CACHE=/home/aoi/.loom/moondream

# Expose port for health checks
EXPOSE 8007

# Run the application
CMD ["python", "-m", "app.main"]
