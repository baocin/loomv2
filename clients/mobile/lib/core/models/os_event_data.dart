import 'package:freezed_annotation/freezed_annotation.dart';

part 'os_event_data.freezed.dart';
part 'os_event_data.g.dart';

@freezed
class OSSystemEvent with _$OSSystemEvent {
  const factory OSSystemEvent({
    required String deviceId,
    required DateTime timestamp,
    required String eventType,
    required String eventCategory,
    required String severity,
    String? description,
    Map<String, dynamic>? metadata,
  }) = _OSSystemEvent;

  factory OSSystemEvent.fromJson(Map<String, dynamic> json) =>
      _$OSSystemEventFromJson(json);
}

@freezed
class OSAppLifecycleEvent with _$OSAppLifecycleEvent {
  const factory OSAppLifecycleEvent({
    required String deviceId,
    required DateTime timestamp,
    required String appIdentifier,
    String? appName,
    required String eventType,
    int? durationSeconds,
    Map<String, dynamic>? metadata,
  }) = _OSAppLifecycleEvent;

  factory OSAppLifecycleEvent.fromJson(Map<String, dynamic> json) =>
      _$OSAppLifecycleEventFromJson(json);
}

@freezed
class AndroidAppInfo with _$AndroidAppInfo {
  const factory AndroidAppInfo({
    required int pid,
    required String name,
    required String packageName,
    required bool active,
    required bool hidden,
    double? launchDate,
    int? versionCode,
    String? versionName,
  }) = _AndroidAppInfo;

  factory AndroidAppInfo.fromJson(Map<String, dynamic> json) =>
      _$AndroidAppInfoFromJson(json);
}

@freezed
class AndroidAppMonitoring with _$AndroidAppMonitoring {
  const factory AndroidAppMonitoring({
    required String deviceId,
    required DateTime timestamp,
    required List<AndroidAppInfo> runningApplications,
  }) = _AndroidAppMonitoring;

  factory AndroidAppMonitoring.fromJson(Map<String, dynamic> json) =>
      _$AndroidAppMonitoringFromJson(json);
}