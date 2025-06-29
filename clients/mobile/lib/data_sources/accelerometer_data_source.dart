import 'dart:async';
import 'dart:io';
import 'package:sensors_plus/sensors_plus.dart';
import '../core/services/data_source_interface.dart';
import '../core/models/sensor_data.dart';
import '../core/utils/content_hasher.dart';

class AccelerometerDataSource extends BaseDataSource<AccelerometerReading> {
  static const String _sourceId = 'accelerometer';
  
  String? _deviceId;
  AccelerometerEvent? _lastReading;

  AccelerometerDataSource(this._deviceId);

  @override
  String get sourceId => _sourceId;

  @override
  String get displayName => 'Accelerometer';

  @override
  List<String> get requiredPermissions => []; // No special permissions needed

  @override
  Future<bool> isAvailable() async {
    if (!Platform.isAndroid && !Platform.isIOS) {
      return false;
    }

    // Simply return true for mobile platforms - accelerometer is standard
    // Don't create any streams during availability check to prevent unwanted data collection
    return true;
  }

  @override
  Future<void> onStart() async {
    // Nothing to do on start - we'll collect readings on demand
  }

  @override
  Future<void> onStop() async {
    _lastReading = null;
  }

  @override
  Future<void> collectDataPoint() async {
    print('ACCELEROMETER: collectDataPoint() called - deviceId: $_deviceId, enabled: ${configuration['enabled']}');
    
    if (_deviceId == null) {
      print('ACCELEROMETER: Device ID is null, returning');
      return;
    }
    
    // Additional safety check to prevent disabled sensors from collecting
    if (!configuration['enabled']) {
      print('ACCELEROMETER: collectDataPoint called but sensor is disabled, returning');
      return;
    }
    
    print('ACCELEROMETER: Starting data collection...');

    try {
      // Get a single accelerometer reading
      final completer = Completer<AccelerometerEvent>();
      late StreamSubscription<AccelerometerEvent> subscription;
      
      subscription = accelerometerEventStream(
        samplingPeriod: const Duration(milliseconds: 10), // Fast sampling for single reading
      ).listen(
        (event) {
          subscription.cancel();
          if (!completer.isCompleted) {
            completer.complete(event);
          }
        },
        onError: (error) {
          subscription.cancel();
          if (!completer.isCompleted) {
            completer.completeError(error);
          }
        },
      );

      // Timeout after 1 second
      Timer(const Duration(seconds: 1), () {
        if (!completer.isCompleted) {
          subscription.cancel();
          completer.completeError(TimeoutException('Failed to get accelerometer reading'));
        }
      });

      final event = await completer.future;
      _lastReading = event;

      final now = DateTime.now();
      final reading = AccelerometerReading(
        deviceId: _deviceId!,
        recordedAt: now,
        x: event.x,
        y: event.y,
        z: event.z,
        contentHash: ContentHasher.generateSensorHash(
          sensorType: 'accelerometer',
          timestamp: now,
          value: {
            'x': event.x,
            'y': event.y,
            'z': event.z,
          },
        ),
      );

      print('ACCELEROMETER: Emitting accelerometer reading - x: ${event.x}, y: ${event.y}, z: ${event.z}');
      emitData(reading);
      print('ACCELEROMETER: Data emitted successfully');
    } catch (e) {
      print('Error collecting accelerometer data: $e');
      _updateStatus(errorMessage: e.toString());
    }
  }

  void _updateStatus({String? errorMessage}) {
    // This would normally update the parent class status
    // For now, just print the error
    if (errorMessage != null) {
      print('Accelerometer Status Error: $errorMessage');
    }
  }

  @override
  Future<void> onConfigurationUpdated(DataSourceConfig config) async {
    // Configuration is handled by the base class
  }
}