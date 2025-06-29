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
  final Map<String, Timer> _dutyCycleTimers = {};
  final Map<String, bool> _activeSources = {};
  
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
      if (dataSource != null) {
        // Check permissions first
        final permissionStatus = await PermissionManager.checkAllPermissions();
        final status = permissionStatus[sourceId];
        if (status != null && status.isGranted) {
          await _startDataSourceWithDutyCycle(sourceId, dataSource);
        } else {
          print('Skipping $sourceId: permissions not granted');
        }
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
    
    for (final timer in _dutyCycleTimers.values) {
      timer.cancel();
    }
    _dutyCycleTimers.clear();

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

  /// Start a data source with duty cycle management
  Future<void> _startDataSourceWithDutyCycle(String sourceId, DataSource dataSource) async {
    final config = _config?.getConfig(sourceId);
    if (config == null) return;
    
    _uploadQueues[sourceId] = [];
    _activeSources[sourceId] = false;
    
    if (config.dutyCycle != null) {
      // Use duty cycle
      _startDutyCycle(sourceId, dataSource, config);
    } else {
      // Always on
      await _startDataSource(sourceId, dataSource);
    }
  }
  
  /// Start duty cycle for a data source
  void _startDutyCycle(String sourceId, DataSource dataSource, DataSourceConfigParams config) {
    final dutyCycle = config.dutyCycle!;
    
    // Start with active period
    _startActivePhase(sourceId, dataSource);
    
    // Set up duty cycle timer
    _dutyCycleTimers[sourceId] = Timer.periodic(
      dutyCycle.totalCycleDuration,
      (_) => _cycleDutyPhase(sourceId, dataSource),
    );
  }
  
  /// Start active phase of duty cycle
  Future<void> _startActivePhase(String sourceId, DataSource dataSource) async {
    if (_activeSources[sourceId] == true) return;
    
    _activeSources[sourceId] = true;
    await _startDataSource(sourceId, dataSource);
    
    // Schedule sleep phase
    final config = _config?.getConfig(sourceId);
    if (config?.dutyCycle != null) {
      Timer(config!.dutyCycle!.activeDuration, () {
        _startSleepPhase(sourceId, dataSource);
      });
    }
  }
  
  /// Start sleep phase of duty cycle
  Future<void> _startSleepPhase(String sourceId, DataSource dataSource) async {
    if (_activeSources[sourceId] == false) return;
    
    _activeSources[sourceId] = false;
    await _subscriptions[sourceId]?.cancel();
    _subscriptions.remove(sourceId);
    await dataSource.stop();
  }
  
  /// Cycle between active and sleep phases
  void _cycleDutyPhase(String sourceId, DataSource dataSource) {
    if (_activeSources[sourceId] == true) {
      _startSleepPhase(sourceId, dataSource);
    } else {
      _startActivePhase(sourceId, dataSource);
    }
  }
  
  /// Start a specific data source
  Future<void> _startDataSource(String sourceId, DataSource dataSource) async {
    try {
      await dataSource.start();
      
      // Subscribe to data stream
      final subscription = dataSource.dataStream.listen(
        (data) => _onDataReceived(sourceId, data),
        onError: (error) => print('Error from $sourceId: $error'),
      );
      
      _subscriptions[sourceId] = subscription;
      print('Started data source: $sourceId');
    } catch (e) {
      print('Failed to start data source $sourceId: $e');
    }
  }

  /// Handle received data from any source
  void _onDataReceived(String sourceId, dynamic data) {
    final queue = _uploadQueues[sourceId] ?? [];
    queue.add(data);
    _uploadQueues[sourceId] = queue;

    final config = _config?.getConfig(sourceId);
    if (config != null && queue.length >= config.uploadBatchSize) {
      _uploadQueuedDataForSource(sourceId);
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
    if (queue == null || queue.isEmpty) return;

    final dataToUpload = List.from(queue);
    queue.clear();

    try {
      await _uploadDataByType(sourceId, dataToUpload);
      print('Successfully uploaded ${dataToUpload.length} $sourceId data points');
      // Update background service after successful upload
      _updateBackgroundServiceQueues();
    } catch (e) {
      print('Error uploading $sourceId data: $e');
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
    try {
      switch (sourceId) {
        case 'gps':
          for (final item in data.cast<GPSReading>()) {
            await _apiClient.uploadGPSReading(item);
          }
          break;
          
        case 'accelerometer':
          for (final item in data.cast<AccelerometerReading>()) {
            await _apiClient.uploadAccelerometerReading(item);
          }
          break;
          
        case 'battery':
          for (final item in data.cast<PowerState>()) {
            await _apiClient.uploadPowerState(item);
          }
          break;
          
        case 'network':
          for (final item in data.cast<NetworkWiFiReading>()) {
            await _apiClient.uploadWiFiReading(item);
          }
          break;
          
        case 'audio':
          for (final item in data.cast<AudioChunk>()) {
            await _apiClient.uploadAudioChunk(item);
          }
          break;
          
        case 'screenshot':
          // Screenshots are uploaded immediately by the data source itself
          // This is just a placeholder in case we want to batch them later
          print('Screenshot data handled by data source directly');
          break;
          
        case 'camera':
          // Camera photos are uploaded immediately by the data source itself
          print('Camera data handled by data source directly');
          break;
          
        default:
          print('Unknown data source: $sourceId');
      }
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
            await _startDataSourceWithDutyCycle(sourceId, dataSource);
          }
        } else {
          await _subscriptions[sourceId]?.cancel();
          _subscriptions.remove(sourceId);
          await dataSource.stop();
          _dutyCycleTimers[sourceId]?.cancel();
          _dutyCycleTimers.remove(sourceId);
          _activeSources.remove(sourceId);
        }
      }
    }
  }

  /// Update configuration for a data source
  Future<void> updateDataSourceConfig(String sourceId, DataSourceConfigParams config) async {
    if (_config == null) return;
    
    await _config!.updateConfig(sourceId, config);
    
    // Restart the source if it's currently running
    if (_isRunning && _dataSources.containsKey(sourceId) && config.enabled) {
      await setDataSourceEnabled(sourceId, false);
      await setDataSourceEnabled(sourceId, true);
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