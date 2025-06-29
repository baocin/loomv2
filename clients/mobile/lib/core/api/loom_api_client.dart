import 'package:dio/dio.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/device_info.dart';
import '../models/sensor_data.dart';
import '../models/audio_data.dart';

class LoomApiClient {
  static const String defaultBaseUrl = 'http://10.0.2.2:8000'; // Android emulator host IP
  static const String apiKey = 'apikeyhere';
  
  late final Dio _dio;
  final String baseUrl;

  LoomApiClient({String? baseUrl}) : baseUrl = baseUrl ?? defaultBaseUrl {
    _dio = Dio(BaseOptions(
      baseUrl: this.baseUrl,
      headers: {
        'X-API-Key': apiKey,
        'Content-Type': 'application/json',
      },
      connectTimeout: const Duration(seconds: 5),
      receiveTimeout: const Duration(seconds: 10),
    ));

    // Add logging interceptor for debugging
    _dio.interceptors.add(LogInterceptor(
      requestBody: true,
      responseBody: true,
      logPrint: (obj) => print('[API] $obj'),
    ));
  }

  // Device Management
  Future<DeviceResponse> registerDevice(DeviceCreate device) async {
    final response = await _dio.post('/devices', data: device.toJson());
    return DeviceResponse.fromJson(response.data);
  }

  Future<DeviceResponse> getDevice(String deviceId) async {
    final response = await _dio.get('/devices/$deviceId');
    return DeviceResponse.fromJson(response.data);
  }

  Future<List<DeviceResponse>> getDevices({
    String? deviceType,
    String? serviceName,
    bool? isActive,
  }) async {
    final queryParams = <String, dynamic>{};
    if (deviceType != null) queryParams['device_type'] = deviceType;
    if (serviceName != null) queryParams['service_name'] = serviceName;
    if (isActive != null) queryParams['is_active'] = isActive;

    final response = await _dio.get('/devices', queryParameters: queryParams);
    return (response.data as List)
        .map((json) => DeviceResponse.fromJson(json))
        .toList();
  }

  // Health Endpoints
  Future<Map<String, dynamic>> getHealthz() async {
    final response = await _dio.get('/healthz');
    return response.data;
  }

  Future<Map<String, dynamic>> getReadyz() async {
    final response = await _dio.get('/readyz');
    return response.data;
  }

  // Audio Data
  Future<ApiResponse> uploadAudioChunk(AudioChunk audioChunk) async {
    final response = await _dio.post('/audio/upload', data: audioChunk.toJsonForApi());
    return ApiResponse.fromJson(response.data);
  }

  // Sensor Data
  Future<ApiResponse> uploadGPSReading(GPSReading reading) async {
    final response = await _dio.post('/sensor/gps', data: reading.toJsonForApi());
    return ApiResponse.fromJson(response.data);
  }

  Future<ApiResponse> uploadAccelerometerReading(AccelerometerReading reading) async {
    final response = await _dio.post('/sensor/accelerometer', data: reading.toJsonForApi());
    return ApiResponse.fromJson(response.data);
  }

  Future<ApiResponse> uploadHeartRateReading(HeartRateReading reading) async {
    final response = await _dio.post('/sensor/heartrate', data: reading.toJsonForApi());
    return ApiResponse.fromJson(response.data);
  }

  Future<ApiResponse> uploadPowerState(PowerState state) async {
    final response = await _dio.post('/sensor/power', data: state.toJsonForApi());
    return ApiResponse.fromJson(response.data);
  }

  Future<ApiResponse> uploadWiFiReading(NetworkWiFiReading reading) async {
    final response = await _dio.post('/sensor/wifi', data: reading.toJsonForApi());
    return ApiResponse.fromJson(response.data);
  }

  Future<ApiResponse> uploadBluetoothReading(NetworkBluetoothReading reading) async {
    final response = await _dio.post('/sensor/bluetooth', data: reading.toJsonForApi());
    return ApiResponse.fromJson(response.data);
  }

  Future<ApiResponse> uploadTemperatureReading(TemperatureReading reading) async {
    final response = await _dio.post('/sensor/temperature', data: reading.toJsonForApi());
    return ApiResponse.fromJson(response.data);
  }

  Future<ApiResponse> uploadBarometerReading(BarometerReading reading) async {
    final response = await _dio.post('/sensor/barometer', data: reading.toJsonForApi());
    return ApiResponse.fromJson(response.data);
  }

  Future<ApiResponse> uploadGenericSensorReading(SensorReading reading) async {
    final response = await _dio.post('/sensor/generic', data: reading.toJsonForApi());
    return ApiResponse.fromJson(response.data);
  }

  Future<BatchApiResponse> uploadBatchSensorReadings(List<SensorReading> readings) async {
    final data = readings.map((r) => r.toJsonForApi()).toList();
    final response = await _dio.post('/sensor/batch', data: data);
    return BatchApiResponse.fromJson(response.data);
  }

  // Settings Management
  Future<void> saveApiSettings({
    required String baseUrl,
    String? apiKey,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('loom_api_base_url', baseUrl);
    if (apiKey != null) {
      await prefs.setString('loom_api_key', apiKey);
    }
  }

  Future<Map<String, String?>> loadApiSettings() async {
    final prefs = await SharedPreferences.getInstance();
    return {
      'base_url': prefs.getString('loom_api_base_url'),
      'api_key': prefs.getString('loom_api_key'),
    };
  }

  static Future<LoomApiClient> createFromSettings() async {
    final prefs = await SharedPreferences.getInstance();
    final baseUrl = prefs.getString('loom_api_base_url') ?? defaultBaseUrl;
    return LoomApiClient(baseUrl: baseUrl);
  }
}

class ApiResponse {
  final String status;
  final String? messageId;
  final String? topic;
  final String? traceId;
  final List<String>? servicesEncountered;

  const ApiResponse({
    required this.status,
    this.messageId,
    this.topic,
    this.traceId,
    this.servicesEncountered,
  });

  factory ApiResponse.fromJson(Map<String, dynamic> json) {
    return ApiResponse(
      status: json['status'],
      messageId: json['message_id'],
      topic: json['topic'],
      traceId: json['trace_id'],
      servicesEncountered: json['services_encountered']?.cast<String>(),
    );
  }

  bool get isSuccess => status == 'success';
}

class BatchApiResponse {
  final String status;
  final int total;
  final int processed;
  final int failed;
  final List<String>? errors;
  final String? traceId;

  const BatchApiResponse({
    required this.status,
    required this.total,
    required this.processed,
    required this.failed,
    this.errors,
    this.traceId,
  });

  factory BatchApiResponse.fromJson(Map<String, dynamic> json) {
    return BatchApiResponse(
      status: json['status'],
      total: json['total'],
      processed: json['processed'],
      failed: json['failed'],
      errors: json['errors']?.cast<String>(),
      traceId: json['trace_id'],
    );
  }

  bool get isSuccess => status == 'success';
  double get successRate => total > 0 ? processed / total : 0.0;
}