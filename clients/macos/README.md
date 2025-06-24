# Loom v2 macOS Client

A comprehensive macOS data collection client that captures various types of system and user data and sends them to the Loom v2 ingestion API.

## Features

- **Audio Recording**: Continuous or triggered microphone recording
- **Screen Capture**: Periodic screenshots and screen recording keyframes  
- **System Monitoring**: CPU, memory, disk, network, battery metrics
- **Application Tracking**: Active applications, window titles, usage time
- **Location Services**: GPS coordinates (when available)
- **Clipboard Monitoring**: Clipboard content changes
- **Network Monitoring**: Wi-Fi status, connected networks
- **Health Integration**: Integration with macOS HealthKit (when available)
- **Sensor Data**: Accelerometer, gyroscope (for MacBooks with sensors)

## Installation

### Prerequisites

- macOS 10.15 (Catalina) or later
- Python 3.11 or later
- Docker (for containerized deployment)

### Local Development

```bash
# Install dependencies
uv pip install -e .

# Run the client
python -m app.main
```

### Docker Deployment

```bash
# Build the container
docker build -t loom-macos-client .

# Run the container
docker run -d \
  --name loom-macos-client \
  -e LOOM_API_BASE_URL=http://host.docker.internal:8000 \
  -e LOOM_DEVICE_ID=macos-$(hostname) \
  -p 8080:8080 \
  loom-macos-client
```

## Configuration

Set environment variables to configure the client:

```bash
# Required
export LOOM_API_BASE_URL="http://localhost:8000"  # Loom ingestion API URL
export LOOM_DEVICE_ID="macos-$(hostname)"         # Unique device identifier

# Optional
export LOOM_LOG_LEVEL="INFO"                      # Logging level
export LOOM_AUDIO_ENABLED="true"                  # Enable audio recording
export LOOM_SCREEN_ENABLED="true"                 # Enable screen capture
export LOOM_SYSTEM_ENABLED="true"                 # Enable system monitoring
export LOOM_LOCATION_ENABLED="false"              # Enable location services
export LOOM_CLIPBOARD_ENABLED="true"              # Enable clipboard monitoring

# Data collection intervals (seconds)
export LOOM_AUDIO_INTERVAL="10"                   # Audio chunk duration
export LOOM_SCREEN_INTERVAL="30"                  # Screenshot interval
export LOOM_SYSTEM_INTERVAL="60"                  # System metrics interval
export LOOM_LOCATION_INTERVAL="300"               # GPS check interval
```

## Data Types Collected

### Audio Data
- Continuous microphone recording in configurable chunks
- Automatic silence detection and filtering
- Compressed audio format (AAC/MP3)
- Metadata: sample rate, channels, duration

### Screen Data
- Periodic screenshots (configurable interval)
- Active window information
- Screen resolution and display configuration
- Privacy-aware capture (excludes secure input fields)

### System Metrics
- CPU usage, temperature, frequency
- Memory usage (RAM, swap)
- Disk usage and I/O metrics
- Network traffic and connection status
- Battery level and power state
- Running processes and applications

### Location Data
- GPS coordinates (when location services enabled)
- Wi-Fi network information
- Bluetooth device proximity
- Network-based location approximation

### Application Data
- Active application tracking
- Window titles and focus time
- Application usage statistics
- Keystroke and mouse activity levels (aggregated, not keylogged)

## Privacy & Security

- **Local Processing**: All sensitive data processing happens locally
- **Configurable Collection**: Each data type can be enabled/disabled
- **Privacy Filters**: Automatic filtering of passwords, secure input
- **Encryption**: Data encrypted in transit to the ingestion API
- **User Consent**: Requires explicit permission for sensitive data types
- **Audit Logging**: Complete log of all data collection activities

## API Endpoints

The client exposes a local REST API for monitoring and control:

- `GET /health` - Health check and status
- `GET /status` - Detailed collection status
- `GET /config` - Current configuration
- `POST /config` - Update configuration
- `POST /start` - Start data collection
- `POST /stop` - Stop data collection
- `GET /logs` - Recent log entries

## System Permissions

The client requires various macOS permissions:

1. **Microphone Access**: For audio recording
2. **Screen Recording**: For screenshot capture
3. **Location Services**: For GPS data (optional)
4. **Accessibility**: For application monitoring
5. **Full Disk Access**: For comprehensive system monitoring (optional)

These permissions must be granted manually in System Preferences > Security & Privacy.

## Development

### Project Structure

```
clients/macos/
├── app/
│   ├── main.py              # Application entry point
│   ├── config.py            # Configuration management
│   ├── collectors/          # Data collection modules
│   │   ├── audio.py         # Audio recording
│   │   ├── screen.py        # Screen capture
│   │   ├── system.py        # System metrics
│   │   ├── location.py      # Location services
│   │   ├── apps.py          # Application monitoring
│   │   └── clipboard.py     # Clipboard monitoring
│   ├── api/                 # Local REST API
│   │   ├── client.py        # Loom API client
│   │   └── server.py        # Local control server
│   └── utils/               # Utilities
│       ├── logging.py       # Structured logging
│       ├── permissions.py   # Permission management
│       └── scheduler.py     # Task scheduling
├── tests/                   # Test suite
├── Dockerfile              # Container configuration
├── pyproject.toml          # Python dependencies
└── README.md               # This file
```

### Adding New Collectors

1. Create a new file in `app/collectors/`
2. Implement the `BaseCollector` interface
3. Add configuration options to `app/config.py`
4. Register the collector in `app/main.py`
5. Add appropriate tests

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_collectors.py
```

## Troubleshooting

### Common Issues

1. **Permission Denied**: Ensure all required macOS permissions are granted
2. **Connection Failed**: Check LOOM_API_BASE_URL and network connectivity
3. **Audio Issues**: Verify microphone permissions and audio device availability
4. **High CPU Usage**: Adjust collection intervals or disable unnecessary collectors

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
export LOOM_LOG_LEVEL="DEBUG"
python -m app.main
```

### Logs

Logs are written to:
- Container: `/app/logs/`
- Local: `~/Library/Logs/Loom/`
- Console: Standard output (when not daemonized)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

Part of the Loom v2 project. See the main repository for license information.