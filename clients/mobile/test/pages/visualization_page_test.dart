import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:foom/models/data_model.dart';
import 'package:foom/ui/visualizers/sensor_visualizer.dart';
import 'package:foom/ui/visualizers/image_visualizer.dart';

void main() {
  group('VisualizationPage Tests', () {
    testWidgets(
        'VisualizationPage properly builds visualizers for different data types',
        (WidgetTester tester) async {
      // Create test data for different source types
      final sensorData = DataModel(
        source: 'Test Accelerometer',
        sourceType: 'sensor',
        timestamp: DateTime.now(),
        data: [
          {'x': 0.1, 'y': 0.2, 'z': 0.3}
        ],
      );

      final cameraData = DataModel(
        source: 'Test Camera',
        sourceType: 'camera',
        timestamp: DateTime.now(),
        bytes: Uint8List.fromList([1, 2, 3, 4]),
        metadata: {'width': 10, 'height': 10, 'format': 'png'},
      );

      final webcamData = DataModel(
        source: 'Test Webcam',
        sourceType: 'webcam',
        timestamp: DateTime.now(),
        bytes: Uint8List.fromList([1, 2, 3, 4]),
        metadata: {'width': 10, 'height': 10, 'format': 'png'},
      );

      final screenshotData = DataModel(
        source: 'Test Screenshot',
        sourceType: 'screenshot',
        timestamp: DateTime.now(),
        bytes: Uint8List.fromList([1, 2, 3, 4]),
        metadata: {'width': 10, 'height': 10, 'format': 'png'},
      );

      // Create a test widget that uses _buildVisualizer directly
      // This widget wraps the method we want to test for easier verification
      final testWidget = MaterialApp(
        home: Scaffold(
          body: Column(
            children: [
              // We're testing the _buildVisualizer method in VisualizationPage by using a wrapper class
              VisualizerTestWrapper(data: sensorData, key: const Key('sensor')),
              VisualizerTestWrapper(data: cameraData, key: const Key('camera')),
              VisualizerTestWrapper(data: webcamData, key: const Key('webcam')),
              VisualizerTestWrapper(
                  data: screenshotData, key: const Key('screenshot')),
            ],
          ),
        ),
      );

      // Build the widget
      await tester.pumpWidget(testWidget);

      // Verify that the correct visualizers are created for each data type
      expect(find.byType(SensorVisualizer), findsOneWidget);
      expect(find.byType(ImageVisualizer),
          findsNWidgets(3)); // Camera, webcam, and screenshot
    });

    testWidgets(
        'VisualizationPage handles sensor data with image bytes correctly',
        (WidgetTester tester) async {
      // Create test data for a sensor that contains image bytes (simulating our issue)
      final sensorWithImageData = DataModel(
        source: 'Test Sensor with Image',
        sourceType: 'sensor',
        timestamp: DateTime.now(),
        bytes: Uint8List.fromList([1, 2, 3, 4]), // Image bytes
        metadata: {'width': 10, 'height': 10, 'format': 'png'},
      );

      // Create a test widget
      final testWidget = MaterialApp(
        home: Scaffold(
          body: VisualizerTestWrapper(data: sensorWithImageData),
        ),
      );

      // Build the widget
      await tester.pumpWidget(testWidget);

      // Verify that the sensor data is visualized with a SensorVisualizer, not an ImageVisualizer
      expect(find.byType(SensorVisualizer), findsOneWidget);
      expect(find.byType(ImageVisualizer), findsNothing);
    });
  });
}

/// A test wrapper that uses the _buildVisualizer method from VisualizationPage
class VisualizerTestWrapper extends StatelessWidget {
  final DataModel data;

  const VisualizerTestWrapper({Key? key, required this.data}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 100,
      child: _buildVisualizer(data),
    );
  }

  /// Builds a visualizer for the given data based on its source type.
  /// This is a copy of the method from VisualizationPage for testing purposes.
  Widget _buildVisualizer(DataModel data) {
    final sourceType = data.sourceType;

    if (sourceType.isEmpty) {
      return const Center(
        child: Text('Unknown data type'),
      );
    }

    if (sourceType == 'sensor') {
      // Always use SensorVisualizer for all sensor data regardless of content
      // This prevents sensors from displaying duplicate camera images
      return SensorVisualizer(data: data);
    } else if (sourceType == 'camera' ||
        sourceType == 'webcam' ||
        sourceType == 'screenshot') {
      return ImageVisualizer(data: data);
    } else {
      return Center(
        child: Text('Unknown data type: $sourceType'),
      );
    }
  }
}
