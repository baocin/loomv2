import 'dart:async';
import 'dart:typed_data';
import 'dart:convert';
import 'dart:ui' as ui;
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
    // Camera is used for manual capture only
    isActive = true;
  }

  @override
  Future<void> stopCollection() async {
    isActive = false;
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

  @override
  void dispose() {
    _disposeController();
    super.dispose();
  }
}