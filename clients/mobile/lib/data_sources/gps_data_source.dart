import 'dart:async';
import 'dart:io';
import 'package:geolocator/geolocator.dart';
import '../core/services/data_source_interface.dart';
import '../core/models/sensor_data.dart';
import '../core/utils/content_hasher.dart';

class GPSDataSource extends BaseDataSource<GPSReading> {
  static const String _sourceId = 'gps';
  
  String? _deviceId;
  Position? _lastPosition;

  GPSDataSource(this._deviceId);

  @override
  String get sourceId => _sourceId;

  @override
  String get displayName => 'GPS Location';

  @override
  List<String> get requiredPermissions => [
    'location',
    'location_always', // For background location
  ];

  @override
  Future<bool> isAvailable() async {
    if (!Platform.isAndroid && !Platform.isIOS) {
      return false;
    }

    try {
      return await Geolocator.isLocationServiceEnabled();
    } catch (e) {
      return false;
    }
  }

  @override
  Future<void> onStart() async {
    // Check permissions
    final hasPermission = await _checkPermissions();
    if (!hasPermission) {
      throw Exception('Location permission not granted');
    }

    // Check if location services are enabled
    final serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) {
      throw Exception('Location services are disabled');
    }
  }

  @override
  Future<void> onStop() async {
    _lastPosition = null;
  }

  @override
  Future<void> collectDataPoint() async {
    if (_deviceId == null) return;

    try {
      // Get current position with timeout
      final position = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
        timeLimit: const Duration(seconds: 5),
      );
      
      _lastPosition = position;

      final now = DateTime.now();
      final reading = GPSReading(
        deviceId: _deviceId!,
        recordedAt: now,
        latitude: position.latitude,
        longitude: position.longitude,
        altitude: position.altitude,
        accuracy: position.accuracy,
        heading: position.heading,
        speed: position.speed,
        contentHash: ContentHasher.generateSensorHash(
          sensorType: 'gps',
          timestamp: now,
          value: {
            'latitude': position.latitude,
            'longitude': position.longitude,
            'accuracy': position.accuracy,
          },
        ),
      );

      emitData(reading);
    } catch (e) {
      print('Error collecting GPS data: $e');
      _updateStatus(errorMessage: e.toString());
    }
  }

  LocationSettings _getLocationSettings() {
    // Get accuracy from configuration
    final accuracy = configuration['accuracy'] as String? ?? 'high';
    final distanceFilter = configuration['distance_filter'] as double? ?? 10.0;

    LocationAccuracy locationAccuracy;
    switch (accuracy) {
      case 'lowest':
        locationAccuracy = LocationAccuracy.lowest;
        break;
      case 'low':
        locationAccuracy = LocationAccuracy.low;
        break;
      case 'medium':
        locationAccuracy = LocationAccuracy.medium;
        break;
      case 'high':
        locationAccuracy = LocationAccuracy.high;
        break;
      case 'best':
        locationAccuracy = LocationAccuracy.best;
        break;
      case 'best_for_navigation':
        locationAccuracy = LocationAccuracy.bestForNavigation;
        break;
      default:
        locationAccuracy = LocationAccuracy.high;
    }

    if (Platform.isAndroid) {
      return AndroidSettings(
        accuracy: locationAccuracy,
        distanceFilter: distanceFilter.round(),
        forceLocationManager: configuration['force_location_manager'] as bool? ?? false,
        intervalDuration: Duration(milliseconds: super.configuration['frequency_ms'] ?? 5000),
      );
    } else if (Platform.isIOS) {
      return AppleSettings(
        accuracy: locationAccuracy,
        distanceFilter: distanceFilter.round(),
        pauseLocationUpdatesAutomatically: configuration['pause_automatically'] as bool? ?? true,
        showBackgroundLocationIndicator: configuration['show_background_indicator'] as bool? ?? false,
      );
    } else {
      return LocationSettings(
        accuracy: locationAccuracy,
        distanceFilter: distanceFilter.round(),
      );
    }
  }

  Future<bool> _checkPermissions() async {
    // Check current permission status
    LocationPermission permission = await Geolocator.checkPermission();
    
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }

    if (permission == LocationPermission.deniedForever) {
      throw Exception('Location permission permanently denied');
    }

    if (permission == LocationPermission.denied) {
      throw Exception('Location permission denied');
    }

    // For background location, we need to request "always" permission
    if (configuration['background_location'] as bool? ?? false) {
      if (permission == LocationPermission.whileInUse) {
        // On iOS, this will show the "always" permission dialog
        permission = await Geolocator.requestPermission();
      }
    }

    return permission == LocationPermission.whileInUse || 
           permission == LocationPermission.always;
  }

  /// Get current location once
  Future<GPSReading?> getCurrentLocation() async {
    if (_deviceId == null) return null;

    try {
      final hasPermission = await _checkPermissions();
      if (!hasPermission) return null;

      final position = await Geolocator.getCurrentPosition();

      final now = DateTime.now();
      return GPSReading(
        deviceId: _deviceId!,
        recordedAt: now,
        latitude: position.latitude,
        longitude: position.longitude,
        altitude: position.altitude,
        accuracy: position.accuracy,
        heading: position.heading,
        speed: position.speed,
        contentHash: ContentHasher.generateSensorHash(
          sensorType: 'gps',
          timestamp: now,
          value: {
            'latitude': position.latitude,
            'longitude': position.longitude,
            'accuracy': position.accuracy,
          },
        ),
      );
    } catch (e) {
      print('Error getting current location: $e');
      return null;
    }
  }

  void _updateStatus({String? errorMessage}) {
    // This would normally update the parent class status
    // For now, just print the error
    if (errorMessage != null) {
      print('GPS Status Error: $errorMessage');
    }
  }

  @override
  Future<void> onConfigurationUpdated(DataSourceConfig config) async {
    // Configuration is handled by the base class
  }
}