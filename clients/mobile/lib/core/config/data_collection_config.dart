import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

/// Configuration for data collection with duty cycles and sending rates
class DataCollectionConfig {
  static const String _configKey = 'data_collection_config';

  // Default configurations per data type (optimized for battery life)
  static const Map<String, DataSourceConfigParams> _defaultConfigs = {
    'gps': DataSourceConfigParams(
      enabled: true,
      collectionIntervalMs: 30000, // 30 seconds
      uploadBatchSize: 10,
      uploadIntervalMs: 300000, // 5 minutes
      priority: DataPriority.high,
    ),
    'accelerometer': DataSourceConfigParams(
      enabled: false, // Disabled by default (high frequency)
      collectionIntervalMs: 100, // 10Hz when enabled
      uploadBatchSize: 50,
      uploadIntervalMs: 60000, // 1 minute
      priority: DataPriority.medium,
    ),
    'battery': DataSourceConfigParams(
      enabled: true,
      collectionIntervalMs: 60000, // 1 minute
      uploadBatchSize: 5,
      uploadIntervalMs: 600000, // 10 minutes
      priority: DataPriority.low,
    ),
    'network': DataSourceConfigParams(
      enabled: true,
      collectionIntervalMs: 120000, // 2 minutes
      uploadBatchSize: 5,
      uploadIntervalMs: 600000, // 10 minutes
      priority: DataPriority.low,
    ),
    'audio': DataSourceConfigParams(
      enabled: false, // Disabled by default (privacy/battery)
      collectionIntervalMs: 30000, // 30 second chunks
      uploadBatchSize: 2,
      uploadIntervalMs: 120000, // 2 minutes
      priority: DataPriority.high,
    ),
    'screen_state': DataSourceConfigParams(
      enabled: true,
      collectionIntervalMs: 0, // Event-driven, no polling
      uploadBatchSize: 20,
      uploadIntervalMs: 60000, // 1 minute
      priority: DataPriority.medium,
    ),
    'app_lifecycle': DataSourceConfigParams(
      enabled: true,
      collectionIntervalMs: 0, // Event-driven, no polling
      uploadBatchSize: 20,
      uploadIntervalMs: 60000, // 1 minute
      priority: DataPriority.medium,
    ),
    'android_app_monitoring': DataSourceConfigParams(
      enabled: true,
      collectionIntervalMs: 300000, // 5 minutes
      uploadBatchSize: 1,
      uploadIntervalMs: 300000, // 5 minutes
      priority: DataPriority.low,
    ),
  };

  Map<String, DataSourceConfigParams> _configs = {};

  DataCollectionConfig() {
    _configs = Map.from(_defaultConfigs);
  }

  /// Load configuration from persistent storage
  static Future<DataCollectionConfig> load() async {
    final config = DataCollectionConfig();
    final prefs = await SharedPreferences.getInstance();
    final configJson = prefs.getString(_configKey);

    if (configJson != null) {
      try {
        final Map<String, dynamic> data = json.decode(configJson);
        config._configs = data.map(
          (key, value) => MapEntry(
            key,
            DataSourceConfigParams.fromJson(value),
          ),
        );
      } catch (e) {
        print('Error loading config: $e, using defaults');
      }
    }

    return config;
  }

  /// Save configuration to persistent storage
  Future<void> save() async {
    final prefs = await SharedPreferences.getInstance();
    final configJson = json.encode(
      _configs.map((key, value) => MapEntry(key, value.toJson())),
    );
    await prefs.setString(_configKey, configJson);
  }

  /// Get configuration for a data source
  DataSourceConfigParams getConfig(String sourceId) {
    return _configs[sourceId] ?? _defaultConfigs[sourceId] ??
           const DataSourceConfigParams();
  }

  /// Update configuration for a data source
  Future<void> updateConfig(String sourceId, DataSourceConfigParams config) async {
    _configs[sourceId] = config;
    await save();
  }

  /// Enable/disable a data source
  Future<void> setEnabled(String sourceId, bool enabled) async {
    final current = getConfig(sourceId);
    await updateConfig(sourceId, current.copyWith(enabled: enabled));
  }

  /// Get all configured source IDs
  List<String> get sourceIds => _configs.keys.toList();

  /// Get enabled source IDs
  List<String> get enabledSourceIds =>
      _configs.entries
          .where((e) => e.value.enabled)
          .map((e) => e.key)
          .toList();

  /// Reset to defaults
  Future<void> resetToDefaults() async {
    _configs = Map.from(_defaultConfigs);
    await save();
  }
}

/// Configuration parameters for a data source
class DataSourceConfigParams {
  final bool enabled;
  final int collectionIntervalMs;
  final int uploadBatchSize;
  final int uploadIntervalMs;
  final DataPriority priority;
  final Map<String, dynamic> customParams;

  const DataSourceConfigParams({
    this.enabled = false,
    this.collectionIntervalMs = 60000,
    this.uploadBatchSize = 10,
    this.uploadIntervalMs = 300000,
    this.priority = DataPriority.medium,
    this.customParams = const {},
  });

  DataSourceConfigParams copyWith({
    bool? enabled,
    int? collectionIntervalMs,
    int? uploadBatchSize,
    int? uploadIntervalMs,
    DataPriority? priority,
    Map<String, dynamic>? customParams,
  }) {
    return DataSourceConfigParams(
      enabled: enabled ?? this.enabled,
      collectionIntervalMs: collectionIntervalMs ?? this.collectionIntervalMs,
      uploadBatchSize: uploadBatchSize ?? this.uploadBatchSize,
      uploadIntervalMs: uploadIntervalMs ?? this.uploadIntervalMs,
      priority: priority ?? this.priority,
      customParams: customParams ?? this.customParams,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'enabled': enabled,
      'collectionIntervalMs': collectionIntervalMs,
      'uploadBatchSize': uploadBatchSize,
      'uploadIntervalMs': uploadIntervalMs,
      'priority': priority.name,
      'customParams': customParams,
    };
  }

  factory DataSourceConfigParams.fromJson(Map<String, dynamic> json) {
    return DataSourceConfigParams(
      enabled: json['enabled'] ?? false,
      collectionIntervalMs: json['collectionIntervalMs'] ?? 60000,
      uploadBatchSize: json['uploadBatchSize'] ?? 10,
      uploadIntervalMs: json['uploadIntervalMs'] ?? 300000,
      priority: DataPriority.values.firstWhere(
        (p) => p.name == json['priority'],
        orElse: () => DataPriority.medium,
      ),
      customParams: Map<String, dynamic>.from(json['customParams'] ?? {}),
    );
  }
}

/// Data priority levels for upload ordering
enum DataPriority {
  low,
  medium,
  high,
  critical,
}

/// Battery optimization profiles
enum BatteryProfile {
  performance,   // High frequency, minimal duty cycling
  balanced,      // Default balanced approach
  powersaver,    // Low frequency, aggressive duty cycling
  custom,        // User-defined settings
}

/// Battery profile configurations
class BatteryProfileManager {
  static const Map<BatteryProfile, Map<String, DataSourceConfigParams>> _profiles = {
    BatteryProfile.performance: {
      'gps': DataSourceConfigParams(
        enabled: true,
        collectionIntervalMs: 10000,
        uploadBatchSize: 1,  // Performance mode = immediate upload
        uploadIntervalMs: 60000,
      ),
      'accelerometer': DataSourceConfigParams(
        enabled: true,
        collectionIntervalMs: 1000, // 1 second interval (was 50ms = too aggressive)
        uploadBatchSize: 1,  // Performance mode = immediate upload
        uploadIntervalMs: 30000,
      ),
      'battery': DataSourceConfigParams(
        enabled: true,
        collectionIntervalMs: 30000,
        uploadBatchSize: 1,  // Performance mode = immediate upload
        uploadIntervalMs: 300000,
      ),
      'network': DataSourceConfigParams(
        enabled: true,
        collectionIntervalMs: 60000,
        uploadBatchSize: 1,  // Performance mode = immediate upload
        uploadIntervalMs: 300000,
      ),
      'audio': DataSourceConfigParams(
        enabled: true,
        collectionIntervalMs: 15000,
        uploadBatchSize: 1,  // Performance mode = immediate upload
        uploadIntervalMs: 60000,
      ),
      'screen_state': DataSourceConfigParams(
        enabled: true,
        collectionIntervalMs: 0, // Event-driven
        uploadBatchSize: 1,  // Performance mode = immediate upload
        uploadIntervalMs: 30000,
      ),
      'app_lifecycle': DataSourceConfigParams(
        enabled: true,
        collectionIntervalMs: 0, // Event-driven
        uploadBatchSize: 1,  // Performance mode = immediate upload
        uploadIntervalMs: 30000,
      ),
      'android_app_monitoring': DataSourceConfigParams(
        enabled: true,
        collectionIntervalMs: 60000, // 1 minute
        uploadBatchSize: 1,
        uploadIntervalMs: 60000,
      ),
    },
    BatteryProfile.powersaver: {
      'gps': DataSourceConfigParams(
        enabled: true,
        collectionIntervalMs: 120000,
        uploadIntervalMs: 1800000,
      ),
      'accelerometer': DataSourceConfigParams(
        enabled: false,
      ),
      'battery': DataSourceConfigParams(
        enabled: true,
        collectionIntervalMs: 300000,
        uploadIntervalMs: 1800000,
      ),
      'network': DataSourceConfigParams(
        enabled: true,
        collectionIntervalMs: 300000,
        uploadIntervalMs: 1800000,
      ),
      'audio': DataSourceConfigParams(
        enabled: false,
      ),
      'screen_state': DataSourceConfigParams(
        enabled: true,
        collectionIntervalMs: 0, // Event-driven
        uploadBatchSize: 50,  // Batch many events
        uploadIntervalMs: 600000, // 10 minutes
      ),
      'app_lifecycle': DataSourceConfigParams(
        enabled: true,
        collectionIntervalMs: 0, // Event-driven
        uploadBatchSize: 50,  // Batch many events
        uploadIntervalMs: 600000, // 10 minutes
      ),
      'android_app_monitoring': DataSourceConfigParams(
        enabled: false, // Disabled in power saver
      ),
    },
  };

  static DataCollectionConfig getProfileConfig(BatteryProfile profile) {
    final config = DataCollectionConfig();
    final profileConfigs = _profiles[profile];

    if (profileConfigs != null) {
      for (final entry in profileConfigs.entries) {
        config._configs[entry.key] = entry.value;
      }
    }

    return config;
  }
}
