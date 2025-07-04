import 'package:flutter_test/flutter_test.dart';
import 'package:loom/data_sources/screenshot_data_source.dart';
import 'package:loom/data_sources/camera_data_source.dart';

void main() {
  group('Screenshot and Camera Tests', () {
    test('ScreenshotDataSource initializes correctly', () {
      final screenshotSource = ScreenshotDataSource('test-device-id');

      expect(screenshotSource.sourceId, equals('screenshot'));
      expect(screenshotSource.displayName, equals('Screenshots'));
      expect(screenshotSource.requiredPermissions, isEmpty);
    });

    test('CameraDataSource initializes correctly', () {
      final cameraSource = CameraDataSource('test-device-id');

      expect(cameraSource.sourceId, equals('camera'));
      expect(cameraSource.displayName, equals('Camera Photos'));
      expect(cameraSource.requiredPermissions, contains('camera'));
    });

    test('Screenshot automatic capture settings', () {
      final screenshotSource = ScreenshotDataSource('test-device-id');

      // Test default settings
      var settings = screenshotSource.getAutomaticCaptureSettings();
      expect(settings['enabled'], isFalse);
      expect(settings['interval_seconds'], equals(300)); // 5 minutes
      expect(settings['save_to_gallery'], isFalse);

      // Test changing settings
      screenshotSource.setAutomaticCapture(true);
      screenshotSource.setCaptureInterval(Duration(minutes: 10));
      screenshotSource.setSaveToGallery(true);

      settings = screenshotSource.getAutomaticCaptureSettings();
      expect(settings['enabled'], isTrue);
      expect(settings['interval_seconds'], equals(600)); // 10 minutes
      expect(settings['save_to_gallery'], isTrue);
    });

    test('Camera automatic capture settings', () {
      final cameraSource = CameraDataSource('test-device-id');

      // Test default settings
      var settings = cameraSource.getAutomaticCaptureSettings();
      expect(settings['enabled'], isFalse);
      expect(settings['interval_seconds'], equals(600)); // 10 minutes
      expect(settings['capture_both_cameras'], isTrue);
      expect(settings['save_to_gallery'], isFalse);

      // Test changing settings
      cameraSource.setAutomaticCapture(true);
      cameraSource.setCaptureInterval(Duration(minutes: 30));
      cameraSource.setCaptureBothCameras(false);
      cameraSource.setSaveToGallery(true);

      settings = cameraSource.getAutomaticCaptureSettings();
      expect(settings['enabled'], isTrue);
      expect(settings['interval_seconds'], equals(1800)); // 30 minutes
      expect(settings['capture_both_cameras'], isFalse);
      expect(settings['save_to_gallery'], isTrue);
    });
  });
}
