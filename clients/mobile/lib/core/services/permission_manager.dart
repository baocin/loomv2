import 'dart:io';
import 'package:permission_handler/permission_handler.dart' as permission_handler;
import 'package:shared_preferences/shared_preferences.dart';

/// Comprehensive permission management with persistent state
class PermissionManager {
  static const String _permissionStateKey = 'permission_states';
  static const String _lastRequestKey = 'last_permission_request';
  
  static final Map<String, List<permission_handler.Permission>> _dataSourcePermissions = {
    'gps': [
      permission_handler.Permission.location,
      permission_handler.Permission.locationWhenInUse,
      if (Platform.isAndroid) permission_handler.Permission.locationAlways,
    ],
    'accelerometer': [], // No special permissions needed
    'battery': [], // No special permissions needed
    'network': [
      if (Platform.isAndroid) permission_handler.Permission.location, // For WiFi SSID
    ],
    'audio': [
      permission_handler.Permission.microphone,
      if (Platform.isAndroid) permission_handler.Permission.storage,
    ],
    'screenshot': [
      // On Android, screenshots require special permissions (handled by app)
      if (Platform.isAndroid) permission_handler.Permission.systemAlertWindow,
    ],
    'camera': [
      permission_handler.Permission.camera,
      if (Platform.isAndroid) permission_handler.Permission.storage,
    ],
    'background_service': [
      permission_handler.Permission.notification,
      if (Platform.isAndroid) permission_handler.Permission.ignoreBatteryOptimizations,
    ],
  };

  static final List<permission_handler.Permission> _criticalPermissions = [
    permission_handler.Permission.notification,
    permission_handler.Permission.location,
    permission_handler.Permission.microphone,
    permission_handler.Permission.camera,
  ];

  /// Check current permission status for all data sources
  static Future<Map<String, permission_handler.PermissionStatus>> checkAllPermissions() async {
    final Map<String, permission_handler.PermissionStatus> status = {};
    
    for (final entry in _dataSourcePermissions.entries) {
      final sourceId = entry.key;
      final permissions = entry.value;
      
      if (permissions.isEmpty) {
        status[sourceId] = permission_handler.PermissionStatus.granted;
        continue;
      }

      // Check if all permissions for this source are granted
      bool allGranted = true;
      for (final permission in permissions) {
        final permStatus = await permission.status;
        if (!permStatus.isGranted) {
          allGranted = false;
          status[sourceId] = permStatus;
          break;
        }
      }
      
      if (allGranted) {
        status[sourceId] = permission_handler.PermissionStatus.granted;
      }
    }

    await _savePermissionState(status);
    return status;
  }

  /// Request permissions for a specific data source
  static Future<PermissionRequestResult> requestDataSourcePermissions(
    String sourceId,
  ) async {
    final permissions = _dataSourcePermissions[sourceId] ?? [];
    
    if (permissions.isEmpty) {
      return PermissionRequestResult(
        sourceId: sourceId,
        granted: true,
        results: {},
      );
    }

    final results = <permission_handler.Permission, permission_handler.PermissionStatus>{};
    bool allGranted = true;
    
    for (final permission in permissions) {
      // Check current status first
      final currentStatus = await permission.status;
      
      if (currentStatus.isGranted) {
        results[permission] = currentStatus;
        continue;
      }

      // Request permission if not granted
      final newStatus = await permission.request();
      results[permission] = newStatus;
      
      if (!newStatus.isGranted) {
        allGranted = false;
      }
    }

    await _updateLastRequestTime();
    
    return PermissionRequestResult(
      sourceId: sourceId,
      granted: allGranted,
      results: results,
    );
  }

  /// Request all critical permissions at once
  static Future<Map<String, PermissionRequestResult>> requestAllCriticalPermissions() async {
    final results = <String, PermissionRequestResult>{};
    
    // Request permissions for each data source that needs them
    for (final sourceId in _dataSourcePermissions.keys) {
      final permissions = _dataSourcePermissions[sourceId] ?? [];
      if (permissions.any((p) => _criticalPermissions.contains(p))) {
        results[sourceId] = await requestDataSourcePermissions(sourceId);
      }
    }
    
    return results;
  }

  /// Check if we should show permission rationale
  static Future<bool> shouldShowRationale(String sourceId) async {
    final permissions = _dataSourcePermissions[sourceId] ?? [];
    
    for (final permission in permissions) {
      if (await permission.shouldShowRequestRationale) {
        return true;
      }
    }
    
    return false;
  }

  /// Open app settings for manual permission grant
  static Future<bool> openAppSettings() async {
    return await permission_handler.openAppSettings();
  }

  /// Check if permissions were permanently denied
  static Future<Map<String, bool>> checkPermanentlyDenied() async {
    final Map<String, bool> denied = {};
    
    for (final entry in _dataSourcePermissions.entries) {
      final sourceId = entry.key;
      final permissions = entry.value;
      
      bool anyPermanentlyDenied = false;
      for (final permission in permissions) {
        final status = await permission.status;
        if (status.isPermanentlyDenied) {
          anyPermanentlyDenied = true;
          break;
        }
      }
      
      denied[sourceId] = anyPermanentlyDenied;
    }
    
    return denied;
  }

  /// Get permission status summary
  static Future<PermissionSummary> getPermissionSummary() async {
    final allStatus = await checkAllPermissions();
    final permanentlyDenied = await checkPermanentlyDenied();
    
    int granted = 0;
    int denied = 0;
    int permanentDenials = 0;
    
    for (final entry in allStatus.entries) {
      if (entry.value.isGranted) {
        granted++;
      } else {
        denied++;
        if (permanentlyDenied[entry.key] == true) {
          permanentDenials++;
        }
      }
    }
    
    return PermissionSummary(
      totalDataSources: allStatus.length,
      grantedCount: granted,
      deniedCount: denied,
      permanentlyDeniedCount: permanentDenials,
      allGranted: denied == 0,
      hasPermanentDenials: permanentDenials > 0,
      statusBySource: allStatus,
      permanentlyDeniedSources: permanentlyDenied.entries
          .where((e) => e.value)
          .map((e) => e.key)
          .toList(),
    );
  }

  /// Get human-readable permission descriptions
  static Map<String, String> getPermissionDescriptions() {
    return {
      'gps': 'Location access for GPS tracking and context awareness',
      'audio': 'Microphone access for audio recording and voice detection',
      'network': 'Network info for WiFi network detection and connectivity',
      'background_service': 'Background processing for continuous data collection',
      'screenshot': 'Screen capture access for taking screenshots',
      'camera': 'Camera access for taking photos',
      'accelerometer': 'Motion sensor data (no permission needed)',
      'battery': 'Battery status monitoring (no permission needed)',
    };
  }

  /// Get required permissions for a data source
  static List<permission_handler.Permission> getDataSourcePermissions(String sourceId) {
    return _dataSourcePermissions[sourceId] ?? [];
  }

  /// Save permission state to persistent storage
  static Future<void> _savePermissionState(
    Map<String, permission_handler.PermissionStatus> status,
  ) async {
    final prefs = await SharedPreferences.getInstance();
    final Map<String, String> statusMap = status.map(
      (key, value) => MapEntry(key, value.name),
    );
    
    await prefs.setString(_permissionStateKey, statusMap.toString());
  }

  /// Update last permission request time
  static Future<void> _updateLastRequestTime() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(_lastRequestKey, DateTime.now().millisecondsSinceEpoch);
  }

  /// Get time since last permission request
  static Future<Duration?> getTimeSinceLastRequest() async {
    final prefs = await SharedPreferences.getInstance();
    final lastRequest = prefs.getInt(_lastRequestKey);
    
    if (lastRequest == null) return null;
    
    final lastTime = DateTime.fromMillisecondsSinceEpoch(lastRequest);
    return DateTime.now().difference(lastTime);
  }

  /// Check if enough time has passed since last request (avoid spam)
  static Future<bool> canRequestPermissions() async {
    final timeSince = await getTimeSinceLastRequest();
    
    if (timeSince == null) return true;
    
    // Wait at least 1 minute between permission requests
    return timeSince.inMinutes >= 1;
  }
}

/// Result of a permission request for a data source
class PermissionRequestResult {
  final String sourceId;
  final bool granted;
  final Map<permission_handler.Permission, permission_handler.PermissionStatus> results;
  final String? errorMessage;

  const PermissionRequestResult({
    required this.sourceId,
    required this.granted,
    required this.results,
    this.errorMessage,
  });

  List<permission_handler.Permission> get grantedPermissions => results.entries
      .where((e) => e.value.isGranted)
      .map((e) => e.key)
      .toList();

  List<permission_handler.Permission> get deniedPermissions => results.entries
      .where((e) => !e.value.isGranted)
      .map((e) => e.key)
      .toList();

  bool get hasPartialGrant => grantedPermissions.isNotEmpty && deniedPermissions.isNotEmpty;
}

/// Summary of all permission states
class PermissionSummary {
  final int totalDataSources;
  final int grantedCount;
  final int deniedCount;
  final int permanentlyDeniedCount;
  final bool allGranted;
  final bool hasPermanentDenials;
  final Map<String, permission_handler.PermissionStatus> statusBySource;
  final List<String> permanentlyDeniedSources;

  const PermissionSummary({
    required this.totalDataSources,
    required this.grantedCount,
    required this.deniedCount,
    required this.permanentlyDeniedCount,
    required this.allGranted,
    required this.hasPermanentDenials,
    required this.statusBySource,
    required this.permanentlyDeniedSources,
  });

  double get grantedPercentage => 
      totalDataSources > 0 ? grantedCount / totalDataSources : 0.0;

  bool get readyForDataCollection => 
      allGranted || (grantedCount > 0 && !hasPermanentDenials);
}