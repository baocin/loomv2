# FOOM Data Collection App Tests

This directory contains the tests for the FOOM Data Collection application. These tests ensure that the app's data visualization and handling components work as expected, particularly focusing on the correct handling of different data source types.

## Test Structure

The tests are organized as follows:

### Unit Tests
- `visualizers/data_visualizer_test.dart`: Tests for the `DataVisualizer` component that ensure it correctly chooses the appropriate visualizer based on source type.
- `visualizers/image_visualizer_test.dart`: Tests for the `ImageVisualizer` component to ensure it properly handles image data from various sources.
- `core/device_manager_test.dart`: Tests for the `DeviceManager` class, focusing on source type handling and data separation between sensors and screenshots.

### Widget Tests
- `pages/visualization_page_test.dart`: Tests for the `VisualizationPage` that verify integration between the page and its visualizers.
- `widget_test.dart`: Basic app-level widget tests that verify the app initializes correctly and handles different data types.

## Key Features Tested

The tests focus on several key areas:

1. **Source Type Handling**: Ensuring that 'webcam', 'camera', 'screenshot', and 'sensor' source types are correctly identified and processed.
2. **Sensor Data Visualization**: Verifying that sensor data is always visualized with a `SensorVisualizer`, even when it contains image bytes.
3. **Image Data Visualization**: Checking that image data from cameras, webcams, and screenshots is visualized appropriately.
4. **Device Manager**: Testing the device manager's ability to correctly handle different data sources and maintain appropriate separation between them.

## Running the Tests

To run all tests, use the following command from the project root:

```bash
flutter test
```

To run a specific test file, specify the path:

```bash
flutter test test/visualizers/data_visualizer_test.dart
```

## Adding New Tests

When adding new features or fixing bugs, please ensure that appropriate tests are added or updated. Follow these guidelines:

1. Unit tests should be placed in the appropriate subdirectory (e.g., `visualizers/` for visualizer components).
2. Widget tests should focus on the integration between components.
3. Tests should be comprehensive but focused on specific functionality.
4. Test names should clearly describe what is being tested.

## Test Coverage

The current tests focus on the visualizer components and their integration with the device manager. Future improvements could include:

- More extensive testing of error handling
- Performance tests for large data sets
- Integration tests with actual device sensors (using the Flutter Driver) 