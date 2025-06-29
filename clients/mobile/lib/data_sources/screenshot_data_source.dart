import 'dart:async';
import 'dart:typed_data';
import 'dart:convert';
import 'dart:ui' as ui;
import 'dart:io' show Platform;
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:screenshot/screenshot.dart';
import 'package:image_gallery_saver/image_gallery_saver.dart';
import '../core/services/data_source_interface.dart';
import '../core/api/loom_api_client.dart';
import '../services/platform_screenshot_service.dart';

class ScreenshotDataSource extends BaseDataSource<Map<String, dynamic>> {
  final ScreenshotController _screenshotController = ScreenshotController();
  DateTime? _lastCaptureTime;
  bool _saveToGallery = false;
  Timer? _captureTimer;
  Duration _captureInterval = const Duration(minutes: 5);
  bool _automaticCaptureEnabled = false;
  
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
    isActive = true;
    if (_automaticCaptureEnabled) {
      _startAutomaticCapture();
    }
  }

  @override
  Future<void> stopCollection() async {
    isActive = false;
    _stopAutomaticCapture();
  }

  /// Enable/disable saving screenshots to device gallery
  void setSaveToGallery(bool save) {
    _saveToGallery = save;
  }

  /// Enable/disable automatic screenshot capture
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

  /// Set capture interval
  void setCaptureInterval(Duration interval) {
    _captureInterval = interval;
    if (_captureTimer != null) {
      _stopAutomaticCapture();
      _startAutomaticCapture();
    }
  }

  /// Start automatic screenshot capture
  void _startAutomaticCapture() async {
    _stopAutomaticCapture(); // Cancel any existing timer
    
    if (!_automaticCaptureEnabled) return;
    
    // Try platform-specific implementation first (Android only)
    if (Platform.isAndroid) {
      final hasPermission = await PlatformScreenshotService.hasScreenshotPermission();
      if (!hasPermission) {
        final granted = await PlatformScreenshotService.requestScreenshotPermission();
        if (!granted) {
          print('Screenshot permission not granted');
          return;
        }
      }
      
      final started = await PlatformScreenshotService.startAutomaticCapture(
        interval: _captureInterval,
        onScreenshot: (Uint8List imageBytes) async {
          await _handlePlatformScreenshot(imageBytes);
        },
      );
      
      if (started) {
        print('Platform screenshot service started with interval: ${_captureInterval.inSeconds}s');
        return;
      }
    }
    
    // Fallback to timer-based approach (limited functionality)
    _captureTimer = Timer.periodic(_captureInterval, (timer) async {
      try {
        // This is limited - can only capture app's own UI
        print('Timer-based screenshot capture (limited to app UI)');
        
        final data = {
          'device_id': deviceId,
          'timestamp': DateTime.now().toIso8601String(),
          'description': 'Automatic screenshot (app UI only)',
          'capture_method': 'automatic_limited',
          'interval_seconds': _captureInterval.inSeconds,
        };
        
        dataController.add(data);
      } catch (e) {
        print('Automatic screenshot failed: $e');
      }
    });
    
    print('Timer-based screenshot capture started with interval: ${_captureInterval.inSeconds}s');
  }

  /// Stop automatic screenshot capture
  void _stopAutomaticCapture() async {
    _captureTimer?.cancel();
    _captureTimer = null;
    
    // Stop platform service if running
    if (Platform.isAndroid) {
      await PlatformScreenshotService.stopAutomaticCapture();
    }
  }
  
  /// Handle screenshot from platform service
  Future<void> _handlePlatformScreenshot(Uint8List imageBytes) async {
    try {
      final timestamp = DateTime.now();
      
      // Save to gallery if enabled
      if (_saveToGallery) {
        try {
          final result = await ImageGallerySaver.saveImage(
            imageBytes,
            quality: 100,
            name: "loom_auto_screenshot_${timestamp.millisecondsSinceEpoch}",
          );
          print('Auto screenshot saved to gallery: $result');
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
        description: 'Automatic screenshot',
        metadata: {
          'capture_method': 'automatic',
          'image_size': imageBytes.length,
          'interval_seconds': _captureInterval.inSeconds,
        },
      );
      
      print('Automatic screenshot uploaded successfully: ${imageBytes.length} bytes');
      _lastCaptureTime = timestamp;
      
      // Emit to stream for tracking
      final data = {
        'device_id': deviceId,
        'timestamp': timestamp.toIso8601String(),
        'description': 'Automatic screenshot',
        'capture_method': 'automatic',
        'uploaded': true,
        'size_bytes': imageBytes.length,
      };
      
      dataController.add(data);
    } catch (e) {
      print('Failed to handle platform screenshot: $e');
    }
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

  /// Get automatic capture settings
  Map<String, dynamic> getAutomaticCaptureSettings() {
    return {
      'enabled': _automaticCaptureEnabled,
      'interval_seconds': _captureInterval.inSeconds,
      'save_to_gallery': _saveToGallery,
    };
  }

  @override
  void dispose() {
    _stopAutomaticCapture();
    super.dispose();
  }
}