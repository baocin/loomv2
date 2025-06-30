import 'dart:async';
import 'dart:io';
import 'package:flutter/services.dart';
import '../core/services/data_source_interface.dart';
import '../core/models/os_event_data.dart';
import '../core/utils/content_hasher.dart';
import '../core/api/loom_api_client.dart';

class AndroidAppMonitoringDataSource extends BaseDataSource<AndroidAppMonitoring> {
  static const String _sourceId = 'android_app_monitoring';
  static const platform = MethodChannel('red.steele.loom/app_monitoring');
  
  String? _deviceId;
  Timer? _pollingTimer;
  final Set<String> _knownPackages = {};
  int _collectionIntervalMs = 60000; // Default 1 minute
  LoomApiClient? _apiClient;

  AndroidAppMonitoringDataSource(this._deviceId);

  @override
  String get sourceId => _sourceId;

  @override
  String get displayName => 'App Monitoring';

  @override
  List<String> get requiredPermissions => []; // Usage stats permission checked separately

  @override
  Future<bool> isAvailable() async {
    // Only available on Android
    return Platform.isAndroid;
  }

  @override
  Future<void> onStart() async {
    if (!Platform.isAndroid) {
      print('App monitoring is only available on Android');
      return;
    }

    try {
      // Get API client for metadata uploads
      _apiClient = await LoomApiClient.createFromSettings();
      
      // Check if we have usage stats permission
      final bool hasPermission = await platform.invokeMethod('hasUsageStatsPermission');
      if (!hasPermission) {
        print('Usage stats permission not granted. Some features may be limited.');
        // We can still try to get basic app info without usage stats
      }

      // Start periodic polling for running apps
      _pollingTimer = Timer.periodic(
        Duration(milliseconds: _collectionIntervalMs),
        (_) => _collectAppData(),
      );

      // Collect initial data
      await _collectAppData();

      print('Started Android app monitoring with ${_collectionIntervalMs}ms interval');
    } catch (e) {
      print('Failed to start app monitoring: $e');
      throw Exception('Failed to start app monitoring: $e');
    }
  }

  @override
  Future<void> onStop() async {
    _pollingTimer?.cancel();
    _pollingTimer = null;
    print('Stopped Android app monitoring');
  }

  @override
  Future<void> onConfigurationUpdated(DataSourceConfig config) async {
    _collectionIntervalMs = config.frequency.inMilliseconds;
  }

  Future<void> _collectAppData() async {
    try {
      // Get list of running applications
      final List<dynamic>? runningApps = await platform.invokeMethod('getRunningApps');
      
      if (runningApps == null || runningApps.isEmpty) {
        logger.d('No running apps detected');
        return;
      }

      final List<Map<String, dynamic>> appInfoList = [];
      
      for (final app in runningApps) {
        if (app is! Map) continue;
        
        final String packageName = app['packageName'] ?? '';
        final String appName = app['appName'] ?? packageName;
        final bool isForeground = app['isForeground'] ?? false;
        final int pid = app['pid'] ?? 0;
        
        // Track new packages for device metadata
        if (!_knownPackages.contains(packageName)) {
          _knownPackages.add(packageName);
          await _uploadDeviceMetadata(packageName, appName, app);
        }
        
        appInfoList.add({
          'pid': pid,
          'name': appName,
          'package_name': packageName,
          'active': isForeground,
          'hidden': !isForeground,
          'launch_date': app['launchTime'],
          'version_code': app['versionCode'],
          'version_name': app['versionName'],
        });
      }

      if (appInfoList.isNotEmpty) {
        // Create Android app monitoring data
        final appMonitoring = AndroidAppMonitoring(
          deviceId: _deviceId!,
          timestamp: DateTime.now(),
          runningApplications: appInfoList.map((info) => AndroidAppInfo(
            pid: info['pid'] as int,
            name: info['name'] as String,
            packageName: info['package_name'] as String,
            active: info['active'] as bool,
            hidden: info['hidden'] as bool,
            launchDate: info['launch_date'] as double?,
            versionCode: info['version_code'] as int?,
            versionName: info['version_name'] as String?,
          )).toList(),
        );
        
        emitData(appMonitoring);
        print('Collected data for ${appInfoList.length} running apps');
      }

      // Also collect aggregated usage stats if available
      await _collectUsageStats();
      
    } catch (e) {
      print('Failed to collect app data: $e');
    }
  }

  Future<void> _collectUsageStats() async {
    try {
      // Get aggregated usage statistics
      final Map<dynamic, dynamic>? usageStats = await platform.invokeMethod('getUsageStats', {
        'intervalMinutes': 60, // Last hour
      });
      
      if (usageStats == null) {
        return;
      }

      final List<Map<String, dynamic>> appUsageList = [];
      final apps = usageStats['apps'] as List<dynamic>? ?? [];
      
      for (final app in apps) {
        if (app is! Map) continue;
        
        appUsageList.add({
          'package_name': app['packageName'] ?? '',
          'app_name': app['appName'],
          'total_time_foreground_ms': app['totalTimeInForeground'] ?? 0,
          'last_time_used': DateTime.fromMillisecondsSinceEpoch(
            app['lastTimeUsed'] ?? DateTime.now().millisecondsSinceEpoch
          ).toIso8601String(),
          'launch_count': app['launchCount'] ?? 0,
        });
      }

      if (appUsageList.isNotEmpty) {
        // Upload aggregated usage stats
        await _uploadUsageStats({
          'aggregation_period_start': DateTime.fromMillisecondsSinceEpoch(
            usageStats['startTime'] ?? DateTime.now().subtract(Duration(hours: 1)).millisecondsSinceEpoch
          ).toIso8601String(),
          'aggregation_period_end': DateTime.fromMillisecondsSinceEpoch(
            usageStats['endTime'] ?? DateTime.now().millisecondsSinceEpoch
          ).toIso8601String(),
          'aggregation_interval_minutes': 60,
          'total_screen_time_ms': usageStats['totalScreenTime'] ?? 0,
          'total_unlocks': usageStats['totalUnlocks'] ?? 0,
          'app_usage_stats': appUsageList,
        });
      }
    } catch (e) {
      print('Failed to collect usage stats: $e');
    }
  }

  Future<void> _uploadDeviceMetadata(String packageName, String appName, Map<dynamic, dynamic> appInfo) async {
    try {
      // Upload app metadata to device metadata endpoint
      await apiClient.post(
        '/system/metadata',
        data: {
          'device_id': deviceId,
          'recorded_at': DateTime.now().toIso8601String(),
          'metadata_type': 'android_app_info',
          'metadata': {
            'package_name': packageName,
            'app_name': appName,
            'version_name': appInfo['versionName'],
            'version_code': appInfo['versionCode'],
            'install_time': appInfo['installTime'],
            'update_time': appInfo['updateTime'],
            'permissions': appInfo['permissions'] ?? [],
            'is_system_app': appInfo['isSystemApp'] ?? false,
          },
        },
      );
      print('Uploaded metadata for app: $packageName');
    } catch (e) {
      print('Failed to upload app metadata: $e');
    }
  }

  Future<void> _uploadUsageStats(Map<String, dynamic> stats) async {
    try {
      final response = await apiClient.post(
        '/system/apps/android/usage',
        data: {
          'device_id': deviceId,
          'recorded_at': DateTime.now().toIso8601String(),
          ...stats,
        },
      );

      if (response.statusCode == 201) {
        print('Usage stats uploaded successfully');
      } else {
        print('Failed to upload usage stats: ${response.statusCode}');
      }
    } catch (e) {
      print('Failed to upload usage stats: $e');
    }
  }
}