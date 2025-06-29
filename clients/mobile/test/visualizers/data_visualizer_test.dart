import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:foom/models/data_model.dart';
import 'package:foom/ui/visualizers/data_visualizer.dart';
import 'package:foom/ui/visualizers/sensor_visualizer.dart';
import 'package:foom/ui/visualizers/image_visualizer.dart';

void main() {
  group('DataVisualizer Tests', () {
    testWidgets('DataVisualizer creates SensorVisualizer for sensor data',
        (WidgetTester tester) async {
      // Create test data
      final sensorData = DataModel(
        source: 'Test Accelerometer',
        sourceType: 'sensor',
        timestamp: DateTime.now(),
        data: [
          {'x': 0.1, 'y': 0.2, 'z': 0.3}
        ],
        metadata: {'type': 'accelerometer'},
      );

      // Build the widget
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: DataVisualizer(data: sensorData),
        ),
      ));

      // Verify that a SensorVisualizer was created
      expect(find.byType(SensorVisualizer), findsOneWidget);
      expect(find.byType(ImageVisualizer), findsNothing);
    });

    testWidgets(
        'DataVisualizer creates SensorVisualizer for sensor data even with image bytes',
        (WidgetTester tester) async {
      // Create test data for a sensor that contains image bytes
      final sensorWithImageData = DataModel(
        source: 'Test Sensor with Image',
        sourceType: 'sensor',
        timestamp: DateTime.now(),
        bytes: Uint8List.fromList([0, 1, 2, 3]), // Mock image bytes
        metadata: {'width': 2, 'height': 2, 'format': 'png'},
      );

      // Build the widget
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: DataVisualizer(data: sensorWithImageData),
        ),
      ));

      // Verify that a SensorVisualizer was created (not an ImageVisualizer)
      expect(find.byType(SensorVisualizer), findsOneWidget);
      expect(find.byType(ImageVisualizer), findsNothing);
    });

    testWidgets('DataVisualizer creates ImageVisualizer for camera data',
        (WidgetTester tester) async {
      // Create test data
      final cameraData = DataModel(
        source: 'Test Camera',
        sourceType: 'camera',
        timestamp: DateTime.now(),
        bytes: Uint8List.fromList([0, 1, 2, 3]), // Mock image bytes
        metadata: {'width': 2, 'height': 2, 'format': 'png'},
      );

      // Build the widget
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: DataVisualizer(data: cameraData),
        ),
      ));

      // Verify that an ImageVisualizer was created
      expect(find.byType(ImageVisualizer), findsOneWidget);
      expect(find.byType(SensorVisualizer), findsNothing);
    });

    testWidgets('DataVisualizer creates ImageVisualizer for webcam data',
        (WidgetTester tester) async {
      // Create test data
      final webcamData = DataModel(
        source: 'Test Webcam',
        sourceType: 'webcam',
        timestamp: DateTime.now(),
        bytes: Uint8List.fromList([0, 1, 2, 3]), // Mock image bytes
        metadata: {'width': 2, 'height': 2, 'format': 'png'},
      );

      // Build the widget
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: DataVisualizer(data: webcamData),
        ),
      ));

      // Verify that an ImageVisualizer was created
      expect(find.byType(ImageVisualizer), findsOneWidget);
      expect(find.byType(SensorVisualizer), findsNothing);
    });

    testWidgets('DataVisualizer creates ImageVisualizer for screenshot data',
        (WidgetTester tester) async {
      // Create test data
      final screenshotData = DataModel(
        source: 'Test Screenshot',
        sourceType: 'screenshot',
        timestamp: DateTime.now(),
        bytes: Uint8List.fromList([0, 1, 2, 3]), // Mock image bytes
        metadata: {'width': 2, 'height': 2, 'format': 'png'},
      );

      // Build the widget
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: DataVisualizer(data: screenshotData),
        ),
      ));

      // Verify that an ImageVisualizer was created
      expect(find.byType(ImageVisualizer), findsOneWidget);
      expect(find.byType(SensorVisualizer), findsNothing);
    });

    testWidgets(
        'DataVisualizer creates default visualizer for unknown data type',
        (WidgetTester tester) async {
      // Create test data
      final unknownData = DataModel(
        source: 'Test Unknown',
        sourceType: 'unknown',
        timestamp: DateTime.now(),
        data: [
          {'value': 42}
        ],
      );

      // Build the widget
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: DataVisualizer(data: unknownData),
        ),
      ));

      // Verify that neither a SensorVisualizer nor an ImageVisualizer was created
      expect(find.byType(SensorVisualizer), findsNothing);
      expect(find.byType(ImageVisualizer), findsNothing);

      // Verify default visualizer content
      expect(find.text('Unable to visualize unknown data'), findsOneWidget);
    });
  });
}
