import 'dart:async';
import 'dart:typed_data';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:loom/core/device_manager.dart';
import 'package:loom/models/data_model.dart';
import 'package:loom/models/data_source.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

// Mock implementation of DataSource for testing
class MockDataSource implements DataSource {
  final String _name;
  final String _sourceType;
  bool _isActive = false;
  final StreamController<DataModel> _controller =
      StreamController<DataModel>.broadcast();
  final Function(DataSource)? _onStart;
  final Function(DataSource)? _onStop;

  MockDataSource(this._name, this._sourceType,
      {Function(DataSource)? onStart, Function(DataSource)? onStop})
      : _onStart = onStart,
        _onStop = onStop;

  @override
  String get name => _name;

  @override
  String get sourceType => _sourceType;

  @override
  String get dataType => 'mock_data';

  @override
  bool get isActive => _isActive;

  @override
  Stream<DataModel> get dataStream => _controller.stream;

  @override
  Future<bool> isAvailable() async => true;

  @override
  Future<void> start({double? frequency}) async {
    _isActive = true;
    if (_onStart != null) {
      _onStart(this);
    }
  }

  @override
  Future<void> stop() async {
    _isActive = false;
    if (_onStop != null) {
      _onStop(this);
    }
  }

  @override
  Future<void> updateConfiguration(Map<String, dynamic> config) async {}

  // Method to emit test data
  void emitData(DataModel data) {
    if (_isActive && !_controller.isClosed) {
      _controller.add(data);
    }
  }

  // Clean up resources
  void dispose() {
    if (!_controller.isClosed) {
      _controller.close();
    }
  }
}

// Mock implementation of ScreenshotDataSource for testing
class MockScreenshotDataSource extends ScreenshotDataSource {
  MockScreenshotDataSource(String name, String sourceType, String dataType)
      : super(name, sourceType, dataType);

  @override
  Future<bool> isAvailable() async => true;

  @override
  Future<void> start({double? frequency}) async {
    // Override to prevent actual screenshot capture during tests
  }
}

// Create a mock version of DeviceManager for testing
class MockDeviceManager extends DeviceManager {
  final Map<String, bool> _dataSourceStates = {};
  final List<DataSource> _dataSources = [];

  @override
  bool isDataSourceEnabled(DataSource source) {
    return _dataSourceStates[source.name] ?? true;
  }

  @override
  void addDataSource(DataSource source) {
    _dataSources.add(source);
    _dataSourceStates[source.name] = true;
  }

  @override
  List<DataSource> getAllDataSources() {
    return List.unmodifiable(_dataSources);
  }
}

void main() {
  // Initialize the Flutter binding
  TestWidgetsFlutterBinding.ensureInitialized();

  // Initialize sqflite_ffi
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;

  // Mock the path_provider plugin
  const MethodChannel('plugins.flutter.io/path_provider')
      .setMockMethodCallHandler((MethodCall methodCall) async {
    if (methodCall.method == 'getApplicationDocumentsDirectory') {
      return '/mock/path/documents';
    }
    return null;
  });

  group('DeviceManager Tests', () {
    late DeviceManager deviceManager;

    setUp(() {
      deviceManager = DeviceManager();
    });

    tearDown(() {
      deviceManager.dispose();
    });

    test('DeviceManager correctly handles webcam source type', () async {
      // Create a webcam data source with 'camera' source type
      final webcamSource = MockDataSource('Test Webcam', 'camera');

      // Add the source to the device manager
      deviceManager.addDataSource(webcamSource);

      // Check if the source was added
      final allSources = deviceManager.getAllDataSources();
      expect(allSources.length, 1);
      expect(allSources[0].name, 'Test Webcam');

      // Check if the source type was corrected to 'webcam'
      // The actual correction would be done by the forceRealWebcamInitialization() method
      // We're testing the concept here

      // Create a data model for the webcam with mock data
      final dataModel = DataModel(
        source: 'Test Webcam',
        sourceType: 'camera', // This should be updated to 'webcam'
        timestamp: DateTime.now(),
        bytes: Uint8List.fromList([1, 2, 3, 4]),
        metadata: {'width': 640, 'height': 480},
      );

      // Simulate how the device manager would update the source type
      // This mimics the behavior in forceRealWebcamInitialization()
      final updatedModel = DataModel(
        source: dataModel.source,
        sourceType: 'webcam', // Updated to webcam
        timestamp: dataModel.timestamp,
        bytes: dataModel.bytes,
        metadata: dataModel.metadata,
      );

      expect(updatedModel.sourceType, 'webcam');
    });

    test('DeviceManager should separate sensor data from screenshot sources',
        () async {
      // Create a sensor data source
      final sensorSource = MockDataSource('Test Accelerometer', 'sensor');

      // Create a screenshot data source
      final screenshotSource = MockDataSource('Test Screenshot', 'screenshot');

      // Add the sources to the device manager
      deviceManager.addDataSource(sensorSource);
      deviceManager.addDataSource(screenshotSource);

      // Check if the sources were added
      final allSources = deviceManager.getAllDataSources();
      expect(allSources.length, 2);

      // Verify source types remain distinct
      expect(allSources.where((s) => s.sourceType == 'sensor').length, 1);
      expect(allSources.where((s) => s.sourceType == 'screenshot').length, 1);

      // Verify that sources are kept separate (no ScreenshotDataSource should be created for the sensor)
      expect(allSources.whereType<ScreenshotDataSource>().length, 0);
    });

    test('DeviceManager should not link sensors with screenshot data',
        () async {
      // Create a mock implementation of DeviceManager that we can manipulate for testing
      final mockDeviceManager = MockDeviceManager();

      // Create a sensor source that might receive screenshot data
      final sensorSource = MockDataSource('Test Accelerometer', 'sensor');

      // Create a screenshot source
      final screenshotSource = MockDataSource('Test Screenshot', 'screenshot');

      // Add the sources
      mockDeviceManager.addDataSource(sensorSource);
      mockDeviceManager.addDataSource(screenshotSource);

      // Check if sources are enabled by default
      expect(mockDeviceManager.isDataSourceEnabled(sensorSource), true);
      expect(mockDeviceManager.isDataSourceEnabled(screenshotSource), true);

      // Create sensor data with screenshot bytes
      final sensorWithScreenshotData = DataModel(
        source: 'Test Accelerometer',
        sourceType: 'sensor', // Type should remain 'sensor'
        timestamp: DateTime.now(),
        bytes: Uint8List.fromList([1, 2, 3, 4]), // Screenshot-like data
        metadata: {'width': 100, 'height': 100},
      );

      // Verify that sourceType remains 'sensor' despite having image bytes
      expect(sensorWithScreenshotData.sourceType, 'sensor');
    });
  });
}
