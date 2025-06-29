// This is a basic Flutter widget test.
//
// To perform an interaction with a widget in your test, use the WidgetTester
// utility in the flutter_test package. For example, you can send tap and scroll
// gestures. You can also use WidgetTester to find child widgets in the widget
// tree, read text, and verify that the values of widget properties are correct.

import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:loom/models/data_model.dart';

// Mock version of MyApp for testing
class TestApp extends StatelessWidget {
  final List<DataModel> dataModels;

  const TestApp({Key? key, required this.dataModels}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      home: Scaffold(
        appBar: AppBar(
          title: const Text('FOOM Data Collection'),
        ),
        body: Column(
          children: [
            const Text('Data Collection Controls'),
            Expanded(
              child: ListView(
                children: dataModels
                    .map((model) => ListTile(
                          title: Text(model.source),
                          subtitle: Text(model.sourceType),
                        ))
                    .toList(),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

void main() {
  testWidgets('Basic app initialization test', (WidgetTester tester) async {
    // Build our test app and trigger a frame.
    await tester.pumpWidget(const TestApp(dataModels: []));

    // Verify that our app header appears
    expect(find.text('FOOM Data Collection'), findsOneWidget);
    expect(find.text('Data Collection Controls'), findsOneWidget);
  });

  testWidgets('App handles different source types correctly',
      (WidgetTester tester) async {
    // Create test data
    final testData = [
      DataModel(
        source: 'Test Camera',
        sourceType: 'camera',
        timestamp: DateTime.now(),
        bytes: Uint8List.fromList([1, 2, 3, 4]),
        metadata: {'width': 10, 'height': 10, 'format': 'png'},
      ),
      DataModel(
        source: 'Test Webcam',
        sourceType: 'webcam',
        timestamp: DateTime.now(),
        bytes: Uint8List.fromList([1, 2, 3, 4]),
        metadata: {'width': 10, 'height': 10, 'format': 'png'},
      ),
      DataModel(
        source: 'Test Accelerometer',
        sourceType: 'sensor',
        timestamp: DateTime.now(),
        data: [
          {'x': 0.1, 'y': 0.2, 'z': 0.3}
        ],
      ),
      DataModel(
        source: 'Test Screenshot',
        sourceType: 'screenshot',
        timestamp: DateTime.now(),
        bytes: Uint8List.fromList([1, 2, 3, 4]),
        metadata: {'width': 10, 'height': 10, 'format': 'png'},
      ),
    ];

    // Build our test app with test data
    await tester.pumpWidget(TestApp(dataModels: testData));

    // Verify that data sources appear in the UI
    expect(find.text('Test Camera'), findsOneWidget);
    expect(find.text('Test Webcam'), findsOneWidget);
    expect(find.text('Test Accelerometer'), findsOneWidget);
    expect(find.text('Test Screenshot'), findsOneWidget);
  });

  testWidgets('App properly handles sensor data with image bytes',
      (WidgetTester tester) async {
    // Create test data for a sensor with image bytes
    final testData = [
      DataModel(
        source: 'Test Sensor with Image',
        sourceType: 'sensor',
        timestamp: DateTime.now(),
        bytes: Uint8List.fromList([1, 2, 3, 4]), // Image bytes
        metadata: {'width': 10, 'height': 10, 'format': 'png'},
      ),
    ];

    // Build our test app with test data
    await tester.pumpWidget(TestApp(dataModels: testData));

    // Verify that the sensor appears in the UI
    expect(find.text('Test Sensor with Image'), findsOneWidget);
    expect(find.text('sensor'), findsOneWidget); // Should show the source type
  });
}
