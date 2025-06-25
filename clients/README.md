# Loom v2 Clients

This directory contains platform-specific data collection clients for the Loom v2 personal informatics platform.

## Overview

Each client is designed to capture data from its respective platform and send it to the Loom v2 ingestion API. The clients are built as Docker containers for easy deployment and management.

## Available Clients

### macOS Client (`macos/`)

A comprehensive macOS data collection client that captures:
- **Audio**: Continuous microphone recording with voice activity detection
- **Screen**: Periodic screenshots and active window monitoring
- **System**: CPU, memory, disk, network, and battery metrics
- **Applications**: Running apps, window titles, and usage tracking
- **Location**: GPS coordinates (when enabled and permissions granted)
- **Clipboard**: Clipboard content changes (privacy-aware)

**Quick Start:**
```bash
cd clients/macos
docker-compose up -d
```

See [macos/README.md](macos/README.md) for detailed setup instructions.

## Client Architecture

All clients follow a common architecture pattern:

### Core Components

1. **Configuration Management** (`config.py`)
   - Environment-based configuration
   - Feature toggles for data collection
   - Interval and quality settings

2. **Data Collectors** (`collectors/`)
   - Modular collectors for different data types
   - Configurable collection intervals
   - Error handling and retry logic

3. **API Client** (`api/client.py`)
   - HTTP client for Loom ingestion API
   - Automatic retries and connection management
   - Data validation and serialization

4. **Local API Server** (`api/server.py`)
   - REST API for monitoring and control
   - Configuration updates
   - Status reporting and health checks

5. **Scheduler** (`utils/scheduler.py`)
   - Manages collection tasks
   - Interval-based execution
   - Graceful shutdown and restart

### Data Flow

```
Platform APIs → Collectors → API Client → Loom Ingestion API
                    ↓
              Local API Server (monitoring/control)
```

## Development

### Adding a New Client

1. Create a new directory for the platform (e.g., `windows/`, `linux/`, `android/`)
2. Copy the macOS client structure as a template
3. Implement platform-specific collectors using appropriate APIs
4. Update Docker configuration for the target platform
5. Add documentation and examples

### Common Patterns

All clients should implement:
- **Base Collector Interface**: Common interface for all data collectors
- **Configuration Schema**: Pydantic models for type-safe configuration
- **Health Checks**: Both internal health monitoring and external endpoints
- **Graceful Shutdown**: Proper cleanup of resources on termination
- **Privacy Controls**: Configurable data filtering and anonymization

### Testing

Each client should include:
- Unit tests for individual collectors
- Integration tests with the Loom API
- Mock implementations for development/testing
- Permission and error handling tests

## Deployment

### Local Development

```bash
# Start the Loom v2 backend services
cd ../
make dev-compose-up

# Start a client
cd clients/macos
docker-compose up -d

# Monitor logs
docker-compose logs -f
```

### Production

For production deployment:

1. **Security**: Review and configure privacy settings
2. **Permissions**: Ensure proper platform permissions are granted
3. **Monitoring**: Set up log aggregation and metrics collection
4. **Updates**: Implement automatic updates or versioning strategy

### Docker Registry

Clients can be pushed to a container registry for easy deployment:

```bash
# Build and tag
docker build -t loom/macos-client:latest clients/macos/

# Push to registry
docker push loom/macos-client:latest
```

## Configuration

### Environment Variables

All clients use the `LOOM_` prefix for environment variables:

```bash
LOOM_API_BASE_URL=http://localhost:8000
LOOM_DEVICE_ID=unique-device-identifier
LOOM_LOG_LEVEL=INFO
LOOM_AUDIO_ENABLED=true
LOOM_SCREEN_ENABLED=true
# ... etc
```

### Feature Toggles

Each data collection type can be individually enabled/disabled:
- `LOOM_AUDIO_ENABLED`
- `LOOM_SCREEN_ENABLED`
- `LOOM_SYSTEM_ENABLED`
- `LOOM_LOCATION_ENABLED`
- `LOOM_CLIPBOARD_ENABLED`
- `LOOM_APPS_ENABLED`

### Collection Intervals

Customize how frequently data is collected:
- `LOOM_AUDIO_INTERVAL` (seconds)
- `LOOM_SCREEN_INTERVAL` (seconds)
- `LOOM_SYSTEM_INTERVAL` (seconds)
- etc.

## API Endpoints

Each client exposes a local REST API for monitoring and control:

- `GET /health` - Health check
- `GET /status` - Detailed status
- `GET /config` - Current configuration
- `POST /config` - Update configuration
- `POST /start` - Start data collection
- `POST /stop` - Stop data collection
- `GET /collectors` - Collector information

## Privacy and Security

### Data Protection

- **Local Processing**: Sensitive data is processed locally before transmission
- **Configurable Filtering**: Exclude passwords, secure input, private browsing
- **Anonymization**: Hash or aggregate sensitive data where possible
- **Encryption**: All data is encrypted in transit

### Permissions

Clients request only necessary permissions:
- **Microphone**: For audio recording
- **Screen Recording**: For screenshots
- **Location**: For GPS data (optional)
- **Accessibility**: For application monitoring

### Compliance

- **User Consent**: Clear indication of what data is being collected
- **Data Minimization**: Only collect necessary data
- **Retention**: Automatic data expiration policies
- **Transparency**: Open source implementation

## Troubleshooting

### Common Issues

1. **API Connection Failed**
   - Check `LOOM_API_BASE_URL` configuration
   - Verify Loom backend services are running
   - Check network connectivity

2. **Permission Denied**
   - Grant required macOS permissions
   - Check Security & Privacy settings
   - Restart client after granting permissions

3. **High Resource Usage**
   - Adjust collection intervals
   - Disable unnecessary collectors
   - Check for memory leaks in logs

### Debug Mode

Enable debug logging:
```bash
export LOOM_LOG_LEVEL=DEBUG
```

### Logs

Check client logs:
```bash
docker-compose logs -f loom-macos-client
```

## Contributing

1. Follow the established architecture patterns
2. Add comprehensive tests
3. Document new features and configuration options
4. Ensure privacy and security best practices
5. Test on the target platform thoroughly

## Future Clients

Planned clients for additional platforms:
- **Windows**: Windows 10/11 data collection
- **Linux**: Ubuntu/Debian desktop environments
- **iOS**: iPhone/iPad data collection (app store approval required)
- **Android**: Android device data collection
- **Browser**: Web extension for browser data
- **IoT**: Raspberry Pi and embedded device support
