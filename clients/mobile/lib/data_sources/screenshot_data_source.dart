import 'dart:async';
import 'dart:typed_data';
import 'dart:convert';
import 'dart:ui' as ui;
import 'package:screenshot/screenshot.dart';
import 'package:image_gallery_saver/image_gallery_saver.dart';
import '../core/services/data_source_interface.dart';
import '../core/api/loom_api_client.dart';

class ScreenshotDataSource extends BaseDataSource<Map<String, dynamic>> {
  final ScreenshotController _screenshotController = ScreenshotController();
  DateTime? _lastCaptureTime;
  bool _saveToGallery = false;
  
  ScreenshotDataSource(String? deviceId) : super(deviceId);

  @override
  String get sourceId => 'screenshot';

  @override
  String get displayName => 'Screenshots';

  @override
  Future<bool> isAvailable() async {
    // Screenshots are always available
    return true;
  }

  @override
  Future<void> startCollection() async {
    // Screenshots are captured manually, not continuously
    isActive = true;
  }

  @override
  Future<void> stopCollection() async {
    isActive = false;
  }

  /// Enable/disable saving screenshots to device gallery
  void setSaveToGallery(bool save) {
    _saveToGallery = save;
  }

  /// Capture a screenshot manually
  Future<void> captureScreenshot(String? description) async {
    if (!isActive) return;
    
    try {
      // Note: In a real implementation, you would capture the current screen
      // This is a placeholder that would need platform-specific implementation
      print('Screenshot capture requested: $description');
      
      // For now, we'll just emit a placeholder event
      final timestamp = DateTime.now();
      final data = {
        'device_id': deviceId,
        'timestamp': timestamp.toIso8601String(),
        'description': description ?? 'Manual screenshot',
        'capture_method': 'manual',
      };
      
      dataController.add(data);
      _lastCaptureTime = timestamp;
    } catch (e) {
      print('Error capturing screenshot: $e');
      throw Exception('Screenshot capture failed: $e');
    }
  }

  /// Capture and upload a screenshot with image data
  Future<void> captureAndUpload(Uint8List imageBytes, {String? description}) async {
    if (!isActive) return;
    
    try {
      final timestamp = DateTime.now();
      
      // Save to gallery if enabled
      if (_saveToGallery) {
        try {
          final result = await ImageGallerySaver.saveImage(
            imageBytes,
            quality: 100,
            name: "loom_screenshot_${timestamp.millisecondsSinceEpoch}",
          );
          print('Screenshot saved to gallery: $result');
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
      await apiClient.uploadScreenshot(
        deviceId: deviceId!,
        base64Image: base64Encode(imageBytes),
        timestamp: timestamp,
        width: width,
        height: height,
        description: description,
        metadata: {
          'capture_method': 'manual',
          'image_size': imageBytes.length,
        },
      );
      
      print('Screenshot uploaded successfully: ${imageBytes.length} bytes');
      _lastCaptureTime = timestamp;
      
      // Emit to stream for tracking
      final data = {
        'device_id': deviceId,
        'timestamp': timestamp.toIso8601String(),
        'description': description ?? 'Manual screenshot',
        'capture_method': 'manual',
        'uploaded': true,
        'size_bytes': imageBytes.length,
      };
      
      dataController.add(data);
    } catch (e) {
      print('Failed to upload screenshot: $e');
      throw Exception('Screenshot upload failed: $e');
    }
  }

  /// Get last capture time
  DateTime? get lastCaptureTime => _lastCaptureTime;

  /// Get screenshot controller for widget capture
  ScreenshotController get screenshotController => _screenshotController;
}