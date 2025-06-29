import 'dart:async';
import 'package:flutter_background_service/flutter_background_service.dart';
import 'package:permission_handler/permission_handler.dart' as permission_handler;
import '../core/services/device_manager.dart';
import '../core/services/data_source_interface.dart';
import '../core/services/permission_manager.dart';
import '../core/config/data_collection_config.dart';
import '../core/api/loom_api_client.dart';
import '../core/models/sensor_data.dart';
import '../core/models/audio_data.dart';
import '../data_sources/gps_data_source.dart';
import '../data_sources/accelerometer_data_source.dart';
import '../data_sources/battery_data_source.dart';
import '../data_sources/network_data_source.dart';
import '../data_sources/audio_data_source.dart';
import '../data_sources/screenshot_data_source.dart';
import '../data_sources/camera_data_source.dart';

class DataCollectionService {
  final DeviceManager _deviceManager;
  final LoomApiClient _apiClient;
  final Map<String, DataSource> _dataSources = {};
  final Map<String, StreamSubscription> _subscriptions = {};
  final Map<String, List<dynamic>> _uploadQueues = {};
  final Map<String, Timer> _uploadTimers = {};
  
  DataCollectionConfig? _config;
  bool _isRunning = false;
  String? _deviceId;

  DataCollectionService(this._deviceManager, this._apiClient);

  /// Initialize the service and set up data sources
  Future<void> initialize() async {
    // Try to ensure device is registered, but continue if offline
    try {
      await _deviceManager.ensureDeviceRegistered();
    } catch (e) {
      print('Warning: Could not register device (offline?): $e');
    }
    
    _deviceId = await _deviceManager.getDeviceId();

    // Load configuration
    _config = await DataCollectionConfig.load();
    
    // Check permissions before initializing data sources
    final permissionSummary = await PermissionManager.getPermissionSummary();
    if (!permissionSummary.readyForDataCollection) {
      print('Warning: Not all permissions granted. Some data sources may be unavailable.');
    }

    // Initialize all available data sources
    await _initializeDataSources();
    
    // Set up upload timers for each source
    _setupUploadTimers();
  }

  /// Start data collection for all enabled sources
  Future<void> startDataCollection() async {
    if (_isRunning) return;

    _isRunning = true;
    
    final enabledSources = _config?.enabledSourceIds ?? [];
    
    for (final sourceId in enabledSources) {
      final dataSource = _dataSources[sourceId];
      final config = _config?.getConfig(sourceId);
      
      // Only start if explicitly enabled in config
      if (dataSource != null && config != null && config.enabled) {
        // Check permissions first
        final permissionStatus = await PermissionManager.checkAllPermissions();
        final status = permissionStatus[sourceId];
        if (status != null && status.isGranted) {
          print('DEBUG: Starting data source $sourceId (enabled: ${config.enabled})');
          await _startDataSource(sourceId, dataSource);
          _uploadQueues[sourceId] = [];
        } else {
          print('Skipping $sourceId: permissions not granted');
        }
      } else {
        print('DEBUG: Skipping data source $sourceId (available: ${dataSource != null}, config exists: ${config != null}, enabled: ${config?.enabled ?? false})');
      }
    }
  }

  /// Stop all data collection
  Future<void> stopDataCollection() async {
    if (!_isRunning) return;

    _isRunning = false;
    
    // Stop all subscriptions
    for (final subscription in _subscriptions.values) {
      await subscription.cancel();
    }
    _subscriptions.clear();

    // Stop all data sources
    for (final dataSource in _dataSources.values) {
      await dataSource.stop();
    }

    // Cancel all timers
    for (final timer in _uploadTimers.values) {
      timer.cancel();
    }
    _uploadTimers.clear();

    // Upload any remaining data
    await _uploadAllQueuedData();
  }

  /// Initialize all data sources
  Future<void> _initializeDataSources() async {
    _dataSources.clear();

    // GPS Data Source
    final gpsSource = GPSDataSource(_deviceId);
    if (await gpsSource.isAvailable()) {
      _dataSources['gps'] = gpsSource;
    }

    // Accelerometer Data Source
    final accelerometerSource = AccelerometerDataSource(_deviceId);
    if (await accelerometerSource.isAvailable()) {
      _dataSources['accelerometer'] = accelerometerSource;
    }

    // Battery Data Source
    final batterySource = BatteryDataSource(_deviceId);
    if (await batterySource.isAvailable()) {
      _dataSources['battery'] = batterySource;
    }

    // Network Data Source
    final networkSource = NetworkDataSource(_deviceId);
    if (await networkSource.isAvailable()) {
      _dataSources['network'] = networkSource;
    }

    // Audio Data Source
    final audioSource = AudioDataSource(_deviceId);
    if (await audioSource.isAvailable()) {
      _dataSources['audio'] = audioSource;
    }

    // Screenshot Data Source
    final screenshotSource = ScreenshotDataSource(_deviceId);
    if (await screenshotSource.isAvailable()) {
      _dataSources['screenshot'] = screenshotSource;
    }

    // Camera Data Source
    final cameraSource = CameraDataSource(_deviceId);
    if (await cameraSource.isAvailable()) {
      _dataSources['camera'] = cameraSource;
    }

    print('Initialized ${_dataSources.length} data sources: ${_dataSources.keys.join(', ')}');
  }

  /// Start a specific data source
  Future<void> _startDataSource(String sourceId, DataSource dataSource) async {
    try {
      // Configure the data source with collection interval
      final config = _config?.getConfig(sourceId);
      if (config != null) {
        await dataSource.updateConfiguration({
          'frequency_ms': config.collectionIntervalMs,
          'enabled': config.enabled,
        });
      }
      
      await dataSource.start();
      
      // Subscribe to data stream
      final subscription = dataSource.dataStream.listen(
        (data) => _onDataReceived(sourceId, data),
        onError: (error) => print('Error from $sourceId: $error'),
      );
      
      _subscriptions[sourceId] = subscription;
      print('Started data source: $sourceId with interval ${config?.collectionIntervalMs}ms');
    } catch (e) {
      print('Failed to start data source $sourceId: $e');
    }
  }

  /// Handle received data from any source
  void _onDataReceived(String sourceId, dynamic data) {
    // Add specific logging for audio data
    if (sourceId == 'audio') {
      print('AUDIO: Data received by DataCollectionService - type: ${data.runtimeType}');
      if (data is AudioChunk) {
        print('AUDIO: AudioChunk details - fileId: ${data.fileId}, size: ${data.chunkData.length} bytes, duration: ${data.durationMs}ms');
      }
    }
    
    final queue = _uploadQueues[sourceId] ?? [];
    queue.add(data);
    _uploadQueues[sourceId] = queue;

    final config = _config?.getConfig(sourceId);
    if (config != null && queue.length >= config.uploadBatchSize) {
      if (sourceId == 'audio') {
        print('AUDIO: Queue reached batch size (${queue.length}/${config.uploadBatchSize}), triggering upload...');
      }
      _uploadQueuedDataForSource(sourceId);
    } else {
      if (sourceId == 'audio') {
        print('AUDIO: Added to queue - current size: ${queue.length}/${config?.uploadBatchSize ?? 'unknown'} (batch size)');
      }
    }
    
    // Update background service with queue information
    _updateBackgroundServiceQueues();
  }

  /// Set up upload timers for each data source
  void _setupUploadTimers() {
    if (_config == null) return;
    
    for (final sourceId in _config!.sourceIds) {
      final config = _config!.getConfig(sourceId);
      final uploadInterval = Duration(milliseconds: config.uploadIntervalMs);
      
      _uploadTimers[sourceId] = Timer.periodic(uploadInterval, (_) {
        _uploadQueuedDataForSource(sourceId);
      });
    }
  }

  /// Upload queued data for a specific source
  Future<void> _uploadQueuedDataForSource(String sourceId) async {
    final queue = _uploadQueues[sourceId];
    if (queue == null || queue.isEmpty) {
      if (sourceId == 'audio') {
        print('AUDIO: Upload called but queue is empty');
      }
      return;
    }

    if (sourceId == 'audio') {
      print('AUDIO: Starting upload process - queue size: ${queue.length}');
    }

    final dataToUpload = List.from(queue);
    queue.clear();

    try {
      await _uploadDataByType(sourceId, dataToUpload);
      // Update background service after successful upload
      _updateBackgroundServiceQueues();
      
      if (sourceId == 'audio') {
        print('AUDIO: Upload completed successfully');
      }
    } catch (e) {
      print('Error uploading $sourceId data: $e');
      
      if (sourceId == 'audio') {
        print('AUDIO: Upload failed, re-adding to queue');
      }
      
      // Re-add failed uploads to queue (with a limit)
      if (queue.length < 1000) {
        queue.addAll(dataToUpload);
      }
    }
  }
  
  /// Upload all queued data from all sources
  Future<void> _uploadAllQueuedData() async {
    for (final sourceId in _uploadQueues.keys) {
      await _uploadQueuedDataForSource(sourceId);
    }
  }


  /// Upload data based on its type
  Future<void> _uploadDataByType(String sourceId, List<dynamic> data) async {
    if (data.isEmpty) return;
    
    int totalBytes = 0;
    String endpoint = '';
    
    try {
      switch (sourceId) {
        case 'gps':
          endpoint = '/sensor/gps';
          final items = data.cast<GPSReading>();
          for (final item in items) {
            final jsonData = item.toJson();
            totalBytes += jsonData.toString().length;
            await _apiClient.uploadGPSReading(item);
          }
          break;
          
        case 'accelerometer':
          endpoint = '/sensor/accelerometer';
          final items = data.cast<AccelerometerReading>();
          for (final item in items) {
            final jsonData = item.toJson();
            totalBytes += jsonData.toString().length;
            await _apiClient.uploadAccelerometerReading(item);
          }
          break;
          
        case 'battery':
          endpoint = '/sensor/power';
          final items = data.cast<PowerState>();
          for (final item in items) {
            final jsonData = item.toJson();
            totalBytes += jsonData.toString().length;
            await _apiClient.uploadPowerState(item);
          }
          break;
          
        case 'network':
          endpoint = '/sensor/wifi';
          final items = data.cast<NetworkWiFiReading>();
          for (final item in items) {
            final jsonData = item.toJson();
            totalBytes += jsonData.toString().length;
            await _apiClient.uploadWiFiReading(item);
          }
          break;
          
        case 'audio':
          endpoint = '/audio/upload';
          final items = data.cast<AudioChunk>();
          print('AUDIO: Starting upload of ${items.length} audio chunks...');
          
          for (int i = 0; i < items.length; i++) {
            final item = items[i];
            print('AUDIO: Uploading chunk ${i + 1}/${items.length} - fileId: ${item.fileId}, size: ${item.chunkData.length} bytes');
            
            // Audio data is in bytes
            totalBytes += item.chunkData.length;
            
            try {
              await _apiClient.uploadAudioChunk(item);
              print('AUDIO: Successfully uploaded chunk ${item.fileId}');
            } catch (e) {
              print('AUDIO: ERROR uploading chunk ${item.fileId}: $e');
              rethrow;
            }
          }
          print('AUDIO: Completed upload of all ${items.length} audio chunks');
          break;
          
        case 'screenshot':
          // Screenshots are uploaded immediately by the data source itself
          print('Screenshot data handled by data source directly');
          return;
          
        case 'camera':
          // Camera photos are uploaded immediately by the data source itself
          print('Camera data handled by data source directly');
          return;
          
        default:
          print('Unknown data source: $sourceId');
          return;
      }
      
      // Log the upload
      print('UPLOAD: $endpoint | batch_size: ${data.length} | payload_size: $totalBytes bytes | source: $sourceId');
      
    } catch (e) {
      print('Error uploading $sourceId data: $e');
      rethrow;
    }
  }


  /// Enable/disable a data source
  Future<void> setDataSourceEnabled(String sourceId, bool enabled) async {
    if (_config == null) return;
    
    await _config!.setEnabled(sourceId, enabled);
    
    // If currently running, start/stop the source immediately
    if (_isRunning) {
      final dataSource = _dataSources[sourceId];
      if (dataSource != null) {
        if (enabled) {
          // Check permissions first
          final permissionStatus = await PermissionManager.checkAllPermissions();
          final status = permissionStatus[sourceId];
          if (status != null && status.isGranted) {
            print('DEBUG: Enabling data source $sourceId via toggle');
            await _startDataSource(sourceId, dataSource);
            _uploadQueues[sourceId] = [];
          }
        } else {
          print('DEBUG: Disabling data source $sourceId via toggle');
          await _subscriptions[sourceId]?.cancel();
          _subscriptions.remove(sourceId);
          await dataSource.stop();
        }
      }
    }
  }

  /// Update configuration for a data source
  Future<void> updateDataSourceConfig(String sourceId, DataSourceConfigParams config) async {
    if (_config == null) return;
    
    // Check if the source was previously enabled before updating config
    final wasEnabled = _config!.getConfig(sourceId).enabled;
    
    await _config!.updateConfig(sourceId, config);
    
    // Only restart the source if it was previously enabled AND still enabled
    // This prevents accidentally starting sources when switching profiles
    if (_isRunning && _dataSources.containsKey(sourceId) && wasEnabled && config.enabled) {
      print('DEBUG: Restarting $sourceId due to config change (was enabled, still enabled)');
      await setDataSourceEnabled(sourceId, false);
      await setDataSourceEnabled(sourceId, true);
    } else if (_isRunning && _dataSources.containsKey(sourceId) && wasEnabled && !config.enabled) {
      print('DEBUG: Disabling $sourceId due to config change (was enabled, now disabled)');
      await setDataSourceEnabled(sourceId, false);
    } else if (_isRunning && _dataSources.containsKey(sourceId) && !wasEnabled && config.enabled) {
      print('DEBUG: NOT auto-starting $sourceId - was disabled before profile change');
    }
  }
  
  /// Get configuration for a data source
  DataSourceConfigParams? getDataSourceConfig(String sourceId) {
    return _config?.getConfig(sourceId);
  }

  /// Get available data sources
  Map<String, DataSource> get availableDataSources => Map.unmodifiable(_dataSources);

  /// Get current service status
  bool get isRunning => _isRunning;

  /// Get current queue size for all sources
  int get queueSize => _uploadQueues.values.fold(0, (sum, queue) => sum + queue.length);
  
  /// Get queue size for a specific source
  int getQueueSizeForSource(String sourceId) => _uploadQueues[sourceId]?.length ?? 0;

  /// Get last data point for a specific source
  dynamic getLastDataPointForSource(String sourceId) {
    final dataSource = _dataSources[sourceId];
    if (dataSource is BaseDataSource) {
      return dataSource.lastDataPoint;
    }
    return null;
  }

  /// Manually trigger data upload for all sources
  Future<void> uploadNow() async {
    await _uploadAllQueuedData();
  }
  
  /// Manually trigger data upload for a specific source
  Future<void> uploadNowForSource(String sourceId) async {
    await _uploadQueuedDataForSource(sourceId);
  }

  /// Request permissions for all data sources
  Future<Map<String, bool>> requestAllPermissions() async {
    final results = await PermissionManager.requestAllCriticalPermissions();
    return results.map((key, value) => MapEntry(key, value.granted));
  }
  
  /// Request permissions for a specific data source
  Future<bool> requestPermissionForSource(String sourceId) async {
    final result = await PermissionManager.requestDataSourcePermissions(sourceId);
    return result.granted;
  }
  
  /// Get permission summary
  Future<PermissionSummary> getPermissionSummary() async {
    return await PermissionManager.getPermissionSummary();
  }
  
  /// Get current configuration
  DataCollectionConfig? get config => _config;
  
  /// Update background service with current queue sizes
  void _updateBackgroundServiceQueues() {
    final service = FlutterBackgroundService();
    final queueData = <String, int>{};
    
    _uploadQueues.forEach((sourceId, queue) {
      if (queue.isNotEmpty) {
        queueData[sourceId] = queue.length;
      }
    });
    
    service.invoke('updateQueues', {'queues': queueData});
  }
  
  /// Dispose the service
  void dispose() {
    stopDataCollection();
    for (final dataSource in _dataSources.values) {
      if (dataSource is BaseDataSource) {
        dataSource.dispose();
      }
    }
  }
}