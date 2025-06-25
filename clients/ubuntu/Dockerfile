FROM python:3.11-slim

# Set timezone to prevent interactive prompts
ENV TZ=UTC
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies for Ubuntu data collection
RUN apt-get update && apt-get install -y \
    # Audio tools
    alsa-utils \
    pulseaudio-utils \
    # Screen capture tools
    scrot \
    imagemagick \
    xdotool \
    wmctrl \
    # Wayland tools
    wl-clipboard \
    # Clipboard tools
    xclip \
    xsel \
    # Network tools
    iproute2 \
    net-tools \
    # System tools
    psmisc \
    procps \
    # Location tools
    geoclue-2.0 \
    networkmanager \
    # Image processing
    libpng-dev \
    libjpeg-dev \
    # Python build tools
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install additional Python packages for image processing
RUN pip install --no-cache-dir Pillow

# Create app directory
WORKDIR /app

# Copy application code
COPY app/ ./app/
COPY *.py ./

# Create pino-proxy config directory
RUN mkdir -p /root/.config/pino-proxy

# Set environment variables
ENV PYTHONPATH=/app
ENV LOOM_API_URL=http://ingestion-api:8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import asyncio; from app.api_client import LoomAPIClient; asyncio.run(LoomAPIClient('${LOOM_API_URL}', 'health-check').health_check())" || exit 1

# Run the application
CMD ["python", "app/main.py"]
