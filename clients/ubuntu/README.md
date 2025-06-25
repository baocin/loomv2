# Pino-proxy Ubuntu Client

A comprehensive data collection client for Ubuntu/Linux systems that integrates with the Loom v2 data pipeline. This client collects various types of system data including audio, screen captures, system metrics, application activity, location information, and clipboard changes.

## Features

### Data Collectors

1. **System Metrics Collector**
   - CPU usage, memory, disk I/O, network I/O
   - Process monitoring (top CPU and memory consumers)
   - Load averages, temperatures, battery info
   - Linux distribution information

2. **Audio Collector**
   - Microphone audio capture using ALSA
   - Configurable sample rate and channels
   - WAV format output with duty cycle support

3. **Screen Capture Collector**
   - Multiple capture methods: scrot, gnome-screenshot, ImageMagick
   - Automatic tool detection and fallback
   - Configurable quality and resolution limits
   - Image resizing with Pillow

4. **Application Monitoring Collector**
   - Running process detection with GUI filtering
   - X11 window management (wmctrl, xdotool)
   - Wayland support (Sway compositor)
   - Active window tracking

5. **Location Collector**
   - GeoClue2 integration for precise location
   - WiFi-based location approximation
   - Network interface monitoring
   - Timezone and locale information

6. **Clipboard Collector**
   - Multi-tool clipboard monitoring (xclip, xsel, wl-paste)
   - Content type analysis and sensitive data filtering
   - Change detection with MD5 hashing
   - Support for both X11 and Wayland

### Duty Cycle Architecture

Each collector implements a configurable duty cycle pattern:
- **Poll Interval**: How often to collect data (e.g., every 1 second)
- **Send Interval**: How often to send batched data (e.g., every 5 seconds)
- **Data Buffering**: Collects data locally and sends in batches
- **Persistent UUID**: Maintains consistent device identification

## Installation

### Requirements

- Ubuntu 18.04+ or compatible Linux distribution
- Python 3.11+
- Docker (for containerized deployment)

### System Dependencies

The client requires various system tools for data collection:

```bash
# Audio tools
sudo apt-get install alsa-utils pulseaudio-utils

# Screen capture tools
sudo apt-get install scrot imagemagick xdotool wmctrl

# Wayland tools (if using Wayland)
sudo apt-get install wl-clipboard

# Clipboard tools
sudo apt-get install xclip xsel

# Location services
sudo apt-get install geoclue-2.0 networkmanager

# System tools
sudo apt-get install iproute2 net-tools psmisc procps
```

### Python Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd loomv2/clients/ubuntu
```

2. Create virtual environment:
```bash
python3.11 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment:
```bash
cp .env.example .env
# Edit .env with your settings
```

5. Run the client:
```bash
python app/main.py
```

### Docker Installation

1. Build the image:
```bash
docker build -t pino-proxy-ubuntu .
```

2. Run with environment file:
```bash
docker run -d \
  --name pino-proxy-ubuntu \
  --env-file .env \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  -v /run/user/$(id -u)/pulse:/run/user/1000/pulse \
  -e DISPLAY=$DISPLAY \
  --net=host \
  pino-proxy-ubuntu
```

## Configuration

### Environment Variables

All configuration is done through environment variables. See `.env.example` for a complete list.

#### Key Settings

- `LOOM_API_URL`: URL of the Loom ingestion API (default: http://localhost:8000)
- `SYSTEM_POLL_INTERVAL`: System metrics polling interval in seconds (default: 5.0)
- `AUDIO_POLL_INTERVAL`: Audio capture interval in seconds (default: 2.0)
- `SCREEN_POLL_INTERVAL`: Screen capture interval in seconds (default: 30.0)

#### Duty Cycle Configuration

Each collector has separate poll and send intervals:

```bash
# Audio: Poll every 2 seconds, send every 10 seconds
AUDIO_POLL_INTERVAL=2.0
AUDIO_SEND_INTERVAL=10.0

# Screen: Poll every 30 seconds, send every 60 seconds
SCREEN_POLL_INTERVAL=30.0
SCREEN_SEND_INTERVAL=60.0
```

### Device ID Management

The client automatically generates and persists a unique device UUID in:
- Linux: `~/.config/pino-proxy/device_id`
- macOS: `~/Library/Application Support/pino-proxy/device_id`

## Usage

### Basic Usage

```bash
# Start with default configuration
python app/main.py

# Start with custom environment
LOOM_API_URL=http://custom-api:8000 python app/main.py
```

### Docker Compose

```yaml
version: '3.8'
services:
  pino-proxy-ubuntu:
    build: .
    environment:
      - LOOM_API_URL=http://ingestion-api:8000
      - SYSTEM_POLL_INTERVAL=10.0
      - AUDIO_POLL_INTERVAL=5.0
    volumes:
      - /tmp/.X11-unix:/tmp/.X11-unix:rw
      - /run/user/1000/pulse:/run/user/1000/pulse
    network_mode: host
    environment:
      - DISPLAY=${DISPLAY}
```

### Production Deployment

For production use, consider:

1. **Resource Limits**: Set appropriate CPU/memory limits
2. **Data Retention**: Configure send intervals based on bandwidth
3. **Privacy**: Review and adjust sensitive data filtering
4. **Monitoring**: Enable health checks and logging
5. **Security**: Run with minimal privileges

## API Endpoints

The client sends data to these Loom API endpoints:

- `POST /audio/upload` - Audio data chunks
- `POST /sensor/gps` - GPS coordinates
- `POST /sensor/generic` - Generic sensor readings
- `POST /sensor/batch` - Batch sensor data
- `POST /media/screen` - Screen captures (may need implementation)
- `POST /system/apps` - Application monitoring (may need implementation)
- `POST /system/clipboard` - Clipboard data (may need implementation)

## Privacy & Security

### Data Filtering

The client includes built-in privacy protections:

1. **Sensitive Content Detection**: Automatically filters passwords, API keys, etc.
2. **Content Limits**: Truncates large clipboard content
3. **Local Processing**: Hashes clipboard content for change detection
4. **Configurable Intervals**: Reduce data collection frequency as needed

### Security Considerations

- Device UUID is stored with user-only permissions (0600)
- No secrets or credentials are logged
- Network traffic uses standard HTTP/HTTPS
- Local data buffering with configurable limits

## Troubleshooting

### Common Issues

1. **No Audio Devices Found**
   ```bash
   # Check audio devices
   arecord -l

   # Test audio recording
   arecord -d 1 test.wav
   ```

2. **Screen Capture Fails**
   ```bash
   # Check display environment
   echo $DISPLAY

   # Test screen capture tools
   scrot test.png
   ```

3. **Location Services Unavailable**
   ```bash
   # Check GeoClue2 service
   systemctl --user status geoclue-agent

   # List D-Bus services
   busctl list --user | grep geoclue
   ```

4. **Clipboard Access Issues**
   ```bash
   # Test clipboard tools
   echo "test" | xclip -selection clipboard
   xclip -selection clipboard -o
   ```

### Debug Mode

Enable debug logging:

```bash
LOG_LEVEL=DEBUG python app/main.py
```

### Health Checks

Check client status:

```bash
# Using curl (if local API server is running)
curl http://localhost:8000/healthz

# Docker health check
docker inspect --format='{{.State.Health.Status}}' pino-proxy-ubuntu
```

## Development

### Project Structure

```
clients/ubuntu/
├── app/
│   ├── collectors/          # Data collection modules
│   │   ├── __init__.py     # BaseCollector with duty cycle
│   │   ├── system.py       # System metrics
│   │   ├── audio.py        # Audio capture
│   │   ├── screen.py       # Screen capture
│   │   ├── apps.py         # Application monitoring
│   │   ├── location.py     # Location services
│   │   └── clipboard.py    # Clipboard monitoring
│   ├── utils/
│   │   └── device_id.py    # Device ID management
│   ├── config.py           # Configuration management
│   ├── api_client.py       # Loom API client
│   └── main.py            # Main application
├── Dockerfile             # Container configuration
├── requirements.txt       # Python dependencies
├── .env.example          # Environment template
└── README.md            # This file
```

### Adding New Collectors

1. Create a new collector class inheriting from `BaseCollector`
2. Implement required methods: `initialize()`, `poll_data()`, `send_data_batch()`, `cleanup()`
3. Add configuration options to `config.py`
4. Register the collector in `main.py`

### Testing

```bash
# Unit tests (when implemented)
python -m pytest tests/

# Manual testing with mock API
LOOM_API_URL=http://httpbin.org/post python app/main.py
```

## License

This project is part of the Loom v2 data pipeline. See the main repository for license information.
