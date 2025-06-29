import 'dart:io' show Platform;
import 'package:flutter/material.dart';
import 'package:flutter_background_service/flutter_background_service.dart';
import 'package:permission_handler/permission_handler.dart' as permission_handler;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';
import 'services/background_service.dart';
import 'services/permission_handler.dart';
import 'core/services/permission_manager.dart';
import 'core/config/data_collection_config.dart';
import 'core/api/loom_api_client.dart';
import 'core/services/device_manager.dart';
import 'services/data_collection_service.dart';
import 'screens/settings_screen.dart';
import 'data_sources/screenshot_data_source.dart';
import 'data_sources/camera_data_source.dart';
import 'widgets/screenshot_widget.dart';
import 'widgets/camera_widget.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  try {
    // Initialize API client and device manager
    final apiClient = await LoomApiClient.createFromSettings();
    final deviceManager = DeviceManager(apiClient);

    // Initialize data collection service
    final dataService = DataCollectionService(deviceManager, apiClient);
    await dataService.initialize();

    // Initialize background service
    try {
      await BackgroundServiceManager.initialize();
    } catch (e) {
      print('Warning: Background service initialization failed: $e');
    }

    runApp(MyApp(dataService: dataService));
  } catch (e) {
    print('Critical initialization error: $e');
    // Show error dialog and exit gracefully
    rethrow;
  }
}

class MyApp extends StatelessWidget {
  final DataCollectionService dataService;

  const MyApp({super.key, required this.dataService});

  // This widget is the root of your application.
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Loom',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue),
        useMaterial3: true,
      ),
      home: HomePage(dataService: dataService),
    );
  }
}

class HomePage extends StatefulWidget {
  final DataCollectionService dataService;

  const HomePage({super.key, required this.dataService});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  bool _isServiceRunning = false;
  bool _isDataCollectionRunning = false;
  PermissionSummary? _permissionSummary;
  String _serviceStatus = 'Initializing...';
  DateTime? _lastUpdate;
  final Map<String, bool> _dataSourceStates = {};
  BatteryProfile _currentProfile = BatteryProfile.balanced;
  ScreenshotDataSource? _screenshotDataSource;
  CameraDataSource? _cameraDataSource;
  bool _isCapturingScreenshot = false;
  bool _isCapturingPhoto = false;

  @override
  void initState() {
    super.initState();
    _checkServiceStatus();
    _checkPermissions();
    _listenToServiceUpdates();
    _initializeDataSources();
    _initializeScreenshotDataSource();
    _initializeCameraDataSource();
  }

  Future<void> _checkServiceStatus() async {
    final service = FlutterBackgroundService();
    final isRunning = await service.isRunning();
    setState(() {
      _isServiceRunning = isRunning;
      _isDataCollectionRunning = widget.dataService.isRunning;
      _serviceStatus = isRunning ? 'Service is running' : 'Service is stopped';
    });
  }

  Future<void> _checkPermissions() async {
    final summary = await PermissionManager.getPermissionSummary();
    setState(() {
      _permissionSummary = summary;
    });
  }

  void _listenToServiceUpdates() {
    FlutterBackgroundService().on('update').listen((event) {
      if (event != null) {
        setState(() {
          _lastUpdate = DateTime.parse(event['current_time'] ?? DateTime.now().toIso8601String());
          _serviceStatus = 'Running for ${event['running_duration']} seconds';
        });
      }
    });
  }

  Future<void> _initializeDataSources() async {
    final dataSources = widget.dataService.availableDataSources;
    final config = widget.dataService.config;
    
    for (final sourceId in dataSources.keys) {
      _dataSourceStates[sourceId] = config?.getConfig(sourceId).enabled ?? false;
    }
    setState(() {});
  }

  Future<void> _initializeScreenshotDataSource() async {
    // Get device ID from shared preferences
    final prefs = await SharedPreferences.getInstance();
    String? deviceId = prefs.getString('loom_device_id');
    
    if (deviceId == null) {
      deviceId = const Uuid().v4();
      await prefs.setString('loom_device_id', deviceId);
    }
    
    _screenshotDataSource = ScreenshotDataSource(deviceId);
  }

  Future<void> _initializeCameraDataSource() async {
    // Get device ID from shared preferences
    final prefs = await SharedPreferences.getInstance();
    String? deviceId = prefs.getString('loom_device_id');
    
    if (deviceId == null) {
      deviceId = const Uuid().v4();
      await prefs.setString('loom_device_id', deviceId);
    }
    
    _cameraDataSource = CameraDataSource(deviceId);
  }

  Future<void> _captureScreenshot() async {
    if (_isCapturingScreenshot || _screenshotDataSource == null) return;
    
    setState(() {
      _isCapturingScreenshot = true;
    });
    
    try {
      await _screenshotDataSource!.captureScreenshot('Manual screenshot from app');
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Screenshot captured and uploaded!')),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to capture screenshot: $e')),
      );
    } finally {
      setState(() {
        _isCapturingScreenshot = false;
      });
    }
  }

  Future<void> _capturePhoto() async {
    if (_isCapturingPhoto || _cameraDataSource == null) return;
    
    setState(() {
      _isCapturingPhoto = true;
    });
    
    try {
      await _cameraDataSource!.capturePhoto(description: 'Manual photo from app');
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Photo captured and uploaded!')),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to capture photo: $e')),
      );
    } finally {
      setState(() {
        _isCapturingPhoto = false;
      });
    }
  }

  Future<void> _toggleDataCollection() async {
    if (!_isDataCollectionRunning) {
      // Check permission summary first
      final summary = await widget.dataService.getPermissionSummary();
      if (!summary.readyForDataCollection) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Please grant required permissions to start data collection')),
        );
        await _showPermissionDialog();
        return;
      }

      await widget.dataService.startDataCollection();
      setState(() {
        _isDataCollectionRunning = true;
      });
    } else {
      await widget.dataService.stopDataCollection();
      setState(() {
        _isDataCollectionRunning = false;
      });
    }
  }

  Future<void> _toggleService() async {
    if (!_isServiceRunning) {
      // Request permissions first
      final granted = await PermissionService.requestAllPermissions();
      if (!granted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Please grant all permissions to start the service')),
        );
        return;
      }

      await BackgroundServiceManager.startService();
      setState(() {
        _serviceStatus = 'Starting service...';
      });
    } else {
      await BackgroundServiceManager.stopService();
      setState(() {
        _serviceStatus = 'Stopping service...';
      });
    }

    // Check status after a delay
    Future.delayed(const Duration(seconds: 1), () {
      _checkServiceStatus();
      _checkPermissions();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        title: const Text('Loom'),
        actions: [
          IconButton(
            icon: _isCapturingPhoto 
                ? const SizedBox(
                    width: 24,
                    height: 24,
                    child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                  )
                : const Icon(Icons.camera_alt),
            onPressed: _isCapturingPhoto ? null : _capturePhoto,
            tooltip: 'Take Photo',
          ),
          ScreenshotButton(
            onPressed: _captureScreenshot,
            isCapturing: _isCapturingScreenshot,
          ),
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (context) => const SettingsScreen(),
                ),
              );
            },
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Data Collection Control
            Card(
              child: ListTile(
                title: const Text('Data Collection'),
                subtitle: Text(_isDataCollectionRunning
                    ? 'Collecting sensor data (Queue: ${widget.dataService.queueSize})'
                    : 'Data collection stopped'),
                trailing: Switch(
                  value: _isDataCollectionRunning,
                  onChanged: (_) => _toggleDataCollection(),
                ),
              ),
            ),
            const SizedBox(height: 8),

            // Background Service Control
            Card(
              child: ListTile(
                title: const Text('Background Service'),
                subtitle: Text(_serviceStatus),
                trailing: Switch(
                  value: _isServiceRunning,
                  onChanged: (_) => _toggleService(),
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Battery Profile Selector
            Card(
              child: ListTile(
                title: const Text('Battery Profile'),
                subtitle: Text(_currentProfile.name.toUpperCase()),
                trailing: DropdownButton<BatteryProfile>(
                  value: _currentProfile,
                  onChanged: (profile) async {
                    if (profile != null) {
                      await _changeBatteryProfile(profile);
                    }
                  },
                  items: BatteryProfile.values.map((profile) {
                    return DropdownMenuItem(
                      value: profile,
                      child: Text(profile.name.toUpperCase()),
                    );
                  }).toList(),
                ),
              ),
            ),
            const SizedBox(height: 16),
            
            // Data Sources
            const Text(
              'Data Sources',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Expanded(
              child: Card(
                child: ListView(
                  children: widget.dataService.availableDataSources.entries.map((entry) {
                    final sourceId = entry.key;
                    final dataSource = entry.value;
                    final isEnabled = _dataSourceStates[sourceId] ?? false;
                    final config = widget.dataService.getDataSourceConfig(sourceId);
                    final queueSize = widget.dataService.getQueueSizeForSource(sourceId);

                    return ExpansionTile(
                      title: Text(dataSource.displayName),
                      subtitle: Text('Queue: $queueSize ${_getDataSourceSubtitle(sourceId, config)}'),
                      leading: Icon(
                        _getDataSourceIcon(sourceId),
                        color: isEnabled ? Colors.green : Colors.grey,
                      ),
                      trailing: Switch(
                        value: isEnabled,
                        onChanged: (value) async {
                          await widget.dataService.setDataSourceEnabled(sourceId, value);
                          setState(() {
                            _dataSourceStates[sourceId] = value;
                          });
                        },
                      ),
                      children: [
                        if (config != null) ..._buildConfigTiles(sourceId, config),
                        if (sourceId == 'screenshot') ..._buildScreenshotSettings(),
                      ],
                    );
                  }).toList(),
                ),
              ),
            ),

            const SizedBox(height: 16),
            const Text(
              'Permissions',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Card(
              child: Column(
                children: [
                  if (_permissionSummary != null) ..._buildPermissionSummary(),
                  ElevatedButton(
                    onPressed: () => _showPermissionDialog(),
                    child: const Text('Manage Permissions'),
                  ),
                ],
              ),
            ),

            if (_lastUpdate != null) ...[
              const SizedBox(height: 16),
              Card(
                child: ListTile(
                  title: const Text('Service Last Active'),
                  subtitle: Text(_lastUpdate!.toLocal().toString()),
                  leading: const Icon(Icons.update),
                ),
              ),
            ],
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () async {
          await widget.dataService.uploadNow();
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Manual upload triggered')),
          );
        },
        child: const Icon(Icons.upload),
      ),
    );
  }

  Future<void> _changeBatteryProfile(BatteryProfile profile) async {
    // Apply the profile config to the data collection service
    // Apply the profile config to the data collection service
    // Note: This would require updating the service's config
    setState(() {
      _currentProfile = profile;
    });
    
    // Restart data collection with new profile
    if (_isDataCollectionRunning) {
      await widget.dataService.stopDataCollection();
      await widget.dataService.startDataCollection();
    }
  }
  
  List<Widget> _buildConfigTiles(String sourceId, DataSourceConfigParams config) {
    return [
      Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16.0),
        child: Column(
          children: [
            ListTile(
              title: const Text('Collection Interval'),
              subtitle: Text('${(config.collectionIntervalMs / 1000).toStringAsFixed(1)}s'),
              dense: true,
            ),
            ListTile(
              title: const Text('Upload Batch Size'),
              subtitle: Text('${config.uploadBatchSize} items'),
              dense: true,
            ),
            if (config.dutyCycle != null)
              ListTile(
                title: const Text('Duty Cycle'),
                subtitle: Text('${config.dutyCycle!.dutyCyclePercentage.toStringAsFixed(1)}% active'),
                dense: true,
              ),
            ListTile(
              title: const Text('Priority'),
              subtitle: Text(config.priority.name.toUpperCase()),
              dense: true,
            ),
          ],
        ),
      ),
    ];
  }
  
  List<Widget> _buildScreenshotSettings() {
    final screenshotSource = _screenshotDataSource;
    if (screenshotSource == null) return [];
    
    final settings = screenshotSource.getAutomaticCaptureSettings();
    
    return [
      Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16.0),
        child: Column(
          children: [
            SwitchListTile(
              title: const Text('Automatic Capture'),
              subtitle: Text(settings['enabled'] 
                ? 'Every ${settings['interval_seconds']} seconds' 
                : 'Manual only'),
              value: settings['enabled'],
              onChanged: (value) {
                setState(() {
                  screenshotSource.setAutomaticCapture(value);
                });
              },
              dense: true,
            ),
            if (settings['enabled'])
              ListTile(
                title: const Text('Capture Interval'),
                subtitle: Slider(
                  value: (settings['interval_seconds'] as int).toDouble(),
                  min: 60,
                  max: 1800,
                  divisions: 29,
                  label: '${settings['interval_seconds']} seconds',
                  onChanged: (value) {
                    setState(() {
                      screenshotSource.setCaptureInterval(
                        Duration(seconds: value.toInt()),
                      );
                    });
                  },
                ),
                dense: true,
              ),
            SwitchListTile(
              title: const Text('Save to Gallery'),
              value: settings['save_to_gallery'],
              onChanged: (value) {
                setState(() {
                  screenshotSource.setSaveToGallery(value);
                });
              },
              dense: true,
            ),
            if (Platform.isAndroid && settings['enabled'])
              ListTile(
                title: const Text('⚠️ Requires Special Permission'),
                subtitle: const Text('Automatic screenshots need screen recording permission'),
                leading: const Icon(Icons.warning, color: Colors.orange),
                dense: true,
              ),
          ],
        ),
      ),
    ];
  }
  
  String _getDataSourceSubtitle(String sourceId, DataSourceConfigParams? config) {
    if (config == null) return '';
    final interval = (config.collectionIntervalMs / 1000).toStringAsFixed(1);
    return '• ${interval}s • ${config.priority.name}';
  }
  
  List<Widget> _buildPermissionSummary() {
    final summary = _permissionSummary!;
    return [
      ListTile(
        title: const Text('Permission Status'),
        subtitle: Text('${summary.grantedCount}/${summary.totalDataSources} granted'),
        trailing: CircularProgressIndicator(
          value: summary.grantedPercentage,
          backgroundColor: Colors.grey[300],
          valueColor: AlwaysStoppedAnimation<Color>(
            summary.allGranted ? Colors.green : Colors.orange,
          ),
        ),
      ),
      if (summary.hasPermanentDenials)
        ListTile(
          title: const Text('Permanently Denied'),
          subtitle: Text(summary.permanentlyDeniedSources.join(', ')),
          leading: const Icon(Icons.warning, color: Colors.red),
        ),
    ];
  }
  
  Future<void> _showPermissionDialog() async {
    final summary = await widget.dataService.getPermissionSummary();
    
    if (!mounted) return;
    
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Permissions'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('${summary.grantedCount}/${summary.totalDataSources} permissions granted'),
            const SizedBox(height: 16),
            ...summary.statusBySource.entries.map((entry) {
              final granted = entry.value.isGranted;
              return ListTile(
                title: Text(entry.key),
                trailing: Icon(
                  granted ? Icons.check_circle : Icons.error,
                  color: granted ? Colors.green : Colors.red,
                ),
                onTap: granted ? null : () async {
                  await widget.dataService.requestPermissionForSource(entry.key);
                  Navigator.of(context).pop();
                  _checkPermissions();
                },
              );
            }).toList(),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Close'),
          ),
          if (!summary.allGranted)
            ElevatedButton(
              onPressed: () async {
                await PermissionManager.openAppSettings();
                Navigator.of(context).pop();
              },
              child: const Text('Open Settings'),
            ),
        ],
      ),
    );
  }
  
  IconData _getDataSourceIcon(String sourceId) {
    switch (sourceId) {
      case 'gps':
        return Icons.location_on;
      case 'accelerometer':
        return Icons.vibration;
      case 'battery':
        return Icons.battery_full;
      case 'network':
        return Icons.wifi;
      case 'audio':
        return Icons.mic;
      case 'screenshot':
        return Icons.screenshot;
      case 'camera':
        return Icons.camera_alt;
      default:
        return Icons.sensors;
    }
  }
}
