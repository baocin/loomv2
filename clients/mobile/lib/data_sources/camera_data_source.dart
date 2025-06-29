import 'dart:async';
import 'dart:typed_data';
import 'dart:convert';
import 'dart:ui' as ui;
import 'package:flutter/services.dart';
import 'package:camera/camera.dart';
import 'package:image_gallery_saver/image_gallery_saver.dart';
import '../core/services/data_source_interface.dart';
import '../core/api/loom_api_client.dart';

class CameraDataSource extends BaseDataSource<Map<String, dynamic>> {
  List<CameraDescription>? _cameras;
  CameraController? _controller;
  bool _isInitialized = false;
  bool _saveToGallery = false;
  DateTime? _lastCaptureTime;
  Timer? _captureTimer;
  Duration _captureInterval = const Duration(minutes: 10);
  bool _automaticCaptureEnabled = false;
  bool _captureBothCameras = true;
  CameraLensDirection _currentAutoDirection = CameraLensDirection.back;
  
  CameraDataSource(String? deviceId) : super(deviceId);

  @override
  String get sourceId => 'camera';

  @override
  String get displayName => 'Camera Photos';

  @override
  Future<bool> isAvailable() async {
    try {
      _cameras = await availableCameras();
      return _cameras != null && _cameras!.isNotEmpty;
    } catch (e) {
      print('Camera not available: $e');
      return false;
    }
  }

  @override
  Future<void> startCollection() async {
    isActive = true;
    if (_automaticCaptureEnabled) {
      _startAutomaticCapture();
    }
  }

  @override
  Future<void> stopCollection() async {
    isActive = false;
    _stopAutomaticCapture();
    await _disposeController();
  }

  /// Initialize camera controller
  Future<bool> initializeCamera([CameraLensDirection direction = CameraLensDirection.back]) async {
    if (_cameras == null || _cameras!.isEmpty) return false;
    
    try {
      // Find camera with specified direction
      final camera = _cameras!.firstWhere(
        (cam) => cam.lensDirection == direction,
        orElse: () => _cameras!.first,
      );
      
      _controller = CameraController(
        camera,
        ResolutionPreset.high,
        enableAudio: false,
      );
      
      await _controller!.initialize();
      _isInitialized = true;
      return true;
    } catch (e) {
      print('Failed to initialize camera: $e');
      _isInitialized = false;
      return false;
    }
  }

  /// Dispose of camera controller
  Future<void> _disposeController() async {
    if (_controller != null) {
      await _controller!.dispose();
      _controller = null;
      _isInitialized = false;
    }
  }

  /// Enable/disable saving photos to device gallery
  void setSaveToGallery(bool save) {
    _saveToGallery = save;
  }

  /// Enable/disable automatic camera capture
  void setAutomaticCapture(bool enabled) {
    _automaticCaptureEnabled = enabled;
    if (isActive) {
      if (enabled) {
        _startAutomaticCapture();
      } else {
        _stopAutomaticCapture();
      }
    }
  }

  /// Set whether to capture from both cameras
  void setCaptureBothCameras(bool both) {
    _captureBothCameras = both;
  }

  /// Set capture interval
  void setCaptureInterval(Duration interval) {
    _captureInterval = interval;
    if (_captureTimer != null) {
      _stopAutomaticCapture();
      _startAutomaticCapture();
    }
  }

  /// Start automatic camera capture
  void _startAutomaticCapture() {
    _stopAutomaticCapture(); // Cancel any existing timer
    
    if (!_automaticCaptureEnabled) return;
    
    _captureTimer = Timer.periodic(_captureInterval, (timer) async {
      try {
        if (_captureBothCameras && _cameras != null && _cameras!.length > 1) {
          // Capture from back camera first
          await _captureAutomaticPhoto(CameraLensDirection.back);
          
          // Wait a bit before switching cameras
          await Future.delayed(const Duration(seconds: 2));
          
          // Capture from front camera
          await _captureAutomaticPhoto(CameraLensDirection.front);
        } else {
          // Capture from current/default camera
          await _captureAutomaticPhoto(_currentAutoDirection);
        }
      } catch (e) {
        print('Automatic camera capture failed: $e');
      }
    });
    
    print('Automatic camera capture started with interval: ${_captureInterval.inSeconds}s');
  }

  /// Stop automatic camera capture
  void _stopAutomaticCapture() {
    _captureTimer?.cancel();
    _captureTimer = null;
  }

  /// Capture automatic photo from specified camera
  Future<void> _captureAutomaticPhoto(CameraLensDirection direction) async {
    try {
      await capturePhoto(
        description: 'Automatic capture - ${direction == CameraLensDirection.front ? 'Front' : 'Back'} camera',
        direction: direction,
      );
      
      final data = {
        'device_id': deviceId,
        'timestamp': DateTime.now().toIso8601String(),
        'description': 'Automatic camera capture',
        'camera_type': direction == CameraLensDirection.front ? 'front' : 'rear',
        'capture_method': 'automatic',
        'interval_seconds': _captureInterval.inSeconds,
      };
      
      dataController.add(data);
    } catch (e) {
      print('Failed to capture automatic photo from ${direction.name}: $e');
    }
  }

  /// Take a photo and upload it
  Future<void> capturePhoto({String? description, CameraLensDirection? direction}) async {
    if (!isActive) return;
    
    try {
      // Initialize camera if needed
      if (!_isInitialized || (direction != null && _controller?.description.lensDirection != direction)) {
        await _disposeController();
        final initialized = await initializeCamera(direction ?? CameraLensDirection.back);
        if (!initialized) {
          throw Exception('Failed to initialize camera');
        }
      }
      
      if (_controller == null || !_controller!.value.isInitialized) {
        throw Exception('Camera not initialized');
      }
      
      // Take the picture
      final XFile photo = await _controller!.takePicture();
      final Uint8List imageBytes = await photo.readAsBytes();
      final timestamp = DateTime.now();
      
      // Save to gallery if enabled
      if (_saveToGallery) {
        try {
          final result = await ImageGallerySaver.saveImage(
            imageBytes,
            quality: 100,
            name: "loom_photo_${timestamp.millisecondsSinceEpoch}",
          );
          print('Photo saved to gallery: $result');
        } catch (e) {
          print('Failed to save to gallery: $e');
        }
      }
      
      // Get image dimensions
      final codec = await ui.instantiateImageCodec(imageBytes);
      final frame = await codec.getNextFrame();
      final width = frame.image.width;
      final height = frame.image.height;
      
      // Upload via API
      final apiClient = await LoomApiClient.createFromSettings();
      await apiClient.uploadPhoto(
        deviceId: deviceId!,
        base64Image: base64Encode(imageBytes),
        timestamp: timestamp,
        width: width,
        height: height,
        cameraType: _controller!.description.lensDirection == CameraLensDirection.front ? 'front' : 'rear',
        description: description,
        metadata: {
          'capture_method': 'manual',
          'image_size': imageBytes.length,
          'camera_name': _controller!.description.name,
        },
      );
      
      print('Photo uploaded successfully: ${imageBytes.length} bytes');
      _lastCaptureTime = timestamp;
      
      // Emit to stream for tracking
      final data = {
        'device_id': deviceId,
        'timestamp': timestamp.toIso8601String(),
        'description': description ?? 'Camera photo',
        'camera_type': _controller!.description.lensDirection == CameraLensDirection.front ? 'front' : 'rear',
        'capture_method': 'manual',
        'uploaded': true,
        'size_bytes': imageBytes.length,
      };
      
      dataController.add(data);
    } catch (e) {
      print('Failed to capture photo: $e');
      throw Exception('Photo capture failed: $e');
    }
  }

  /// Get available cameras
  List<CameraDescription>? get cameras => _cameras;

  /// Get current camera controller
  CameraController? get controller => _controller;

  /// Check if camera is initialized
  bool get isInitialized => _isInitialized;

  /// Get last capture time
  DateTime? get lastCaptureTime => _lastCaptureTime;

  /// Get automatic capture settings
  Map<String, dynamic> getAutomaticCaptureSettings() {
    return {
      'enabled': _automaticCaptureEnabled,
      'interval_seconds': _captureInterval.inSeconds,
      'capture_both_cameras': _captureBothCameras,
      'save_to_gallery': _saveToGallery,
    };
  }

  @override
  void dispose() {
    _stopAutomaticCapture();
    _disposeController().then((_) => super.dispose());
  }
}