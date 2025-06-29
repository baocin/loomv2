# FOOM - Flutter Observation and Orchestration Module

## Overview

FOOM is a modular Flutter application designed to collect, manage, and process data from various sources such as sensors, cameras, and screenshots. It provides a flexible architecture that allows for easy integration of new data sources and communication methods.

## Key Features

- **Modular Architecture**: Clean separation of concerns between different components
- **Multiple Data Sources**: Support for various data sources including:
  - Sensors (Accelerometer, Light Sensor)
  - Cameras (Webcam)
  - Screenshots (Desktop)
- **Data Processing**: Centralized data processing through device managers
- **Communication**: gRPC integration for communication with external systems
- **Configurability**: All modules are configurable with runtime parameters

## Project Structure

```
lib/
├── core/
│   ├── device_manager.dart      # Manages data sources and communication
│   └── grpc/
│       └── grpc_client.dart     # Client for gRPC communication
├── models/
│   └── data_model.dart          # Base model for all data types
├── modules/
│   ├── camera/
│   │   ├── camera_base.dart     # Base class for camera implementations
│   │   └── webcam.dart          # Webcam implementation
│   ├── data_source.dart         # Data source interface
│   ├── screenshot/
│   │   ├── desktop_screenshot.dart  # Desktop screenshot implementation
│   │   └── screenshot_base.dart     # Base class for screenshot implementations
│   └── sensors/
│       ├── accelerometer_sensor.dart  # Accelerometer sensor implementation
│       ├── light_sensor.dart         # Light sensor implementation
│       └── sensor_base.dart          # Base class for sensor implementations
└── main.dart                    # Application entry point
```

## Getting Started

1. Ensure Flutter is installed and set up on your system
2. Clone the repository
3. Run `flutter pub get` to install dependencies
4. Run `flutter run` to start the application

## Usage

The application provides a simple UI to control data collection from various sources:

- **Sensors**: Toggle sensor data collection
- **Camera**: Toggle camera stream
- **Screenshots**: Toggle screenshot capture

Each data source can be configured independently, and the collected data is displayed in the UI.

## Architecture

FOOM follows a clean, modular architecture:

1. **Data Sources**: Each data source implements the `DataSource` interface
2. **Device Managers**: Coordinate data collection from multiple sources
3. **Data Models**: Represent collected data with appropriate metadata
4. **gRPC Communication**: Send data to external systems

## Extension

To add a new data source:

1. Create a new class extending the appropriate base class (SensorBase, CameraBase, ScreenshotBase)
2. Implement required methods like `isAvailable()`, `start()`, `stop()`
3. Register the new data source with the appropriate DeviceManager

## Dependencies

- Flutter: UI framework
- Provider: State management
- gRPC: Communication protocol
- Meta: Annotation support

## License

MIT License
