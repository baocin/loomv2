import 'dart:async';
import 'dart:io';
import 'package:flutter/services.dart';
import 'package:flutter/widgets.dart';
import '../core/services/data_source_interface.dart';
import '../core/models/os_event_data.dart';

class AppLifecycleDataSource extends BaseDataSource<OSAppLifecycleEvent> with WidgetsBindingObserver {
  static const String _sourceId = 'app_lifecycle';
  static const platform = MethodChannel('red.steele.loom/app_lifecycle');

  String? _deviceId;
  final Map<String, DateTime> _appLaunchTimes = {};
  final Map<String, DateTime> _appForegroundTimes = {};
  StreamSubscription<dynamic>? _eventSubscription;
  DateTime? _currentAppForegroundTime;
  String? _currentForegroundApp;

  AppLifecycleDataSource(this._deviceId);

  @override
  String get sourceId => _sourceId;

  @override
  String get displayName => 'App Lifecycle';

  @override
  List<String> get requiredPermissions => []; // No special permissions for app lifecycle

  @override
  Future<bool> isAvailable() async {
    // Only available on Android for now
    return Platform.isAndroid;
  }

  @override
  Future<void> onStart() async {
    if (!Platform.isAndroid) {
      print('App lifecycle monitoring is only available on Android');
      return;
    }

    try {
      // Register for app lifecycle events from native Android
      const EventChannel eventChannel = EventChannel('red.steele.loom/app_lifecycle_events');
      _eventSubscription = eventChannel.receiveBroadcastStream().listen(
        _handleAppLifecycleEvent,
        onError: (error) {
          print('Error receiving app lifecycle events: $error');
        },
      );

      // Also monitor this app's lifecycle
      WidgetsBinding.instance.addObserver(this);

      // Start monitoring other apps
      await platform.invokeMethod('startAppMonitoring');

      print('Started app lifecycle monitoring');
    } catch (e) {
      print('Failed to start app lifecycle monitoring: $e');
      throw Exception('Failed to start app lifecycle monitoring: $e');
    }
  }

  @override
  Future<void> onStop() async {
    await _eventSubscription?.cancel();
    _eventSubscription = null;

    WidgetsBinding.instance.removeObserver(this);

    try {
      await platform.invokeMethod('stopAppMonitoring');
    } catch (e) {
      print('Failed to stop app monitoring: $e');
    }

    print('Stopped app lifecycle monitoring');
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    super.didChangeAppLifecycleState(state);

    // Track this app's lifecycle
    final now = DateTime.now();
    const appIdentifier = 'red.steele.loom';
    const appName = 'Loom';

    String eventType;
    int? durationSeconds;

    switch (state) {
      case AppLifecycleState.resumed:
        eventType = 'foreground';
        _currentAppForegroundTime = now;
        break;
      case AppLifecycleState.paused:
        eventType = 'background';
        if (_currentAppForegroundTime != null) {
          durationSeconds = now.difference(_currentAppForegroundTime!).inSeconds;
        }
        break;
      case AppLifecycleState.detached:
        eventType = 'terminate';
        break;
      default:
        return;
    }

    final event = OSAppLifecycleEvent(
      deviceId: _deviceId!,
      timestamp: now,
      appIdentifier: appIdentifier,
      appName: appName,
      eventType: eventType,
      durationSeconds: durationSeconds,
      metadata: {
        'lifecycle_state': state.toString(),
        'is_self': true,
      },
    );

    print('WARNING: App lifecycle event emitted - app: $appName, event: $eventType, duration: ${durationSeconds ?? 0}s');
    emitData(event);
  }

  void _handleAppLifecycleEvent(dynamic event) {
    if (event is! Map) return;

    final String packageName = event['packageName'] ?? '';
    final String? appName = event['appName'];
    final String eventType = event['eventType'] ?? '';
    final int timestamp = event['timestamp'] ?? DateTime.now().millisecondsSinceEpoch;
    final DateTime eventTime = DateTime.fromMillisecondsSinceEpoch(timestamp);

    print('App lifecycle event: $packageName - $eventType at $eventTime');

    // Calculate duration for foreground/background events
    int? durationSeconds;

    switch (eventType) {
      case 'launch':
        _appLaunchTimes[packageName] = eventTime;
        break;
      case 'foreground':
        _appForegroundTimes[packageName] = eventTime;
        _currentForegroundApp = packageName;
        break;
      case 'background':
        if (_appForegroundTimes.containsKey(packageName)) {
          durationSeconds = eventTime.difference(_appForegroundTimes[packageName]!).inSeconds;
          _appForegroundTimes.remove(packageName);
        }
        if (_currentForegroundApp == packageName) {
          _currentForegroundApp = null;
        }
        break;
      case 'terminate':
        if (_appLaunchTimes.containsKey(packageName)) {
          durationSeconds = eventTime.difference(_appLaunchTimes[packageName]!).inSeconds;
          _appLaunchTimes.remove(packageName);
        }
        _appForegroundTimes.remove(packageName);
        break;
    }

    // Create app lifecycle event
    final lifecycleEvent = OSAppLifecycleEvent(
      deviceId: _deviceId!,
      timestamp: eventTime,
      appIdentifier: packageName,
      appName: appName ?? packageName,
      eventType: eventType,
      durationSeconds: durationSeconds,
      metadata: {
        'is_self': false,
        if (_currentForegroundApp != null)
          'current_foreground_app': _currentForegroundApp,
      },
    );

    // Emit the event
    print('WARNING: App lifecycle event emitted - app: ${appName ?? packageName}, event: $eventType, duration: ${durationSeconds ?? 0}s');
    emitData(lifecycleEvent);
  }

}
