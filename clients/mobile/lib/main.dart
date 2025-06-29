import 'package:flutter/material.dart';
import 'package:flutter_background_service/flutter_background_service.dart';
import 'services/background_service.dart';
import 'services/permission_handler.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize background service
  await BackgroundServiceManager.initialize();

  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  // This widget is the root of your application.
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Loom Mobile',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue),
        useMaterial3: true,
      ),
      home: const HomePage(),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  bool _isServiceRunning = false;
  Map<String, bool> _permissions = {};
  String _serviceStatus = 'Initializing...';
  DateTime? _lastUpdate;

  @override
  void initState() {
    super.initState();
    _checkServiceStatus();
    _checkPermissions();
    _listenToServiceUpdates();
  }

  Future<void> _checkServiceStatus() async {
    final service = FlutterBackgroundService();
    final isRunning = await service.isRunning();
    setState(() {
      _isServiceRunning = isRunning;
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
            const SizedBox(height: 16),
            if (_lastUpdate != null) ...[
              const Text(
                'Last Update',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              Card(
                child: ListTile(
                  title: const Text('Service Last Active'),
                  subtitle: Text(_lastUpdate!.toLocal().toString()),
                ),
              ),
            ],
            const Spacer(),
            Center(
              child: Column(
                children: [
                  const Text(
                    'Loom will continue running in the background',
                    style: TextStyle(fontSize: 12, color: Colors.grey),
                  ),
                  const Text(
                    'even when the app is closed.',
                    style: TextStyle(fontSize: 12, color: Colors.grey),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
