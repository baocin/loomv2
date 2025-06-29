import 'package:flutter/material.dart';
import 'package:flutter_background_service/flutter_background_service.dart';
import 'services/background_service.dart';
import 'services/permission_handler.dart';
import 'core/api/loom_api_client.dart';
import 'core/services/device_manager.dart';
import 'services/data_collection_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize API client and device manager
  final apiClient = await LoomApiClient.createFromSettings();
  final deviceManager = DeviceManager(apiClient);
  
  // Initialize data collection service
  final dataService = DataCollectionService(deviceManager, apiClient);
  await dataService.initialize();

  // Initialize background service
  await BackgroundServiceManager.initialize();

  runApp(MyApp(dataService: dataService));
}

class MyApp extends StatelessWidget {
  final DataCollectionService dataService;
  
  const MyApp({super.key, required this.dataService});

  // This widget is the root of your application.
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Loom Mobile',
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
  Map<String, bool> _permissions = {};
  String _serviceStatus = 'Initializing...';
  DateTime? _lastUpdate;
  Map<String, bool> _dataSourceStates = {};

  @override
  void initState() {
    super.initState();
    _checkServiceStatus();
    _checkPermissions();
    _listenToServiceUpdates();
    _initializeDataSources();
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
    final permissions = await PermissionService.checkPermissionStatus();
    setState(() {
      _permissions = permissions;
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
    for (final sourceId in dataSources.keys) {
      _dataSourceStates[sourceId] = true; // Default enabled
    }
    setState(() {});
  }

  Future<void> _toggleDataCollection() async {
    if (!_isDataCollectionRunning) {
      // Request permissions first
      final granted = await PermissionService.requestAllPermissions();
      if (!granted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Please grant all permissions to start data collection')),
        );
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
        title: const Text('Loom Mobile'),
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
                    
                    return ListTile(
                      title: Text(dataSource.displayName),
                      subtitle: Text('Source: $sourceId'),
                      trailing: Switch(
                        value: isEnabled,
                        onChanged: (value) async {
                          await widget.dataService.setDataSourceEnabled(sourceId, value);
                          setState(() {
                            _dataSourceStates[sourceId] = value;
                          });
                        },
                      ),
                      leading: Icon(
                        _getDataSourceIcon(sourceId),
                        color: isEnabled ? Colors.green : Colors.grey,
                      ),
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
                  ListTile(
                    title: const Text('Notification Permission'),
                    trailing: Icon(
                      _permissions['notification'] == true ? Icons.check_circle : Icons.error,
                      color: _permissions['notification'] == true ? Colors.green : Colors.red,
                    ),
                  ),
                  ListTile(
                    title: const Text('Battery Optimization'),
                    subtitle: const Text('Exemption status'),
                    trailing: Icon(
                      _permissions['batteryOptimization'] == true ? Icons.check_circle : Icons.error,
                      color: _permissions['batteryOptimization'] == true ? Colors.green : Colors.red,
                    ),
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
      default:
        return Icons.sensors;
    }
  }
}
