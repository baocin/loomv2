import 'dart:async';
import 'dart:io';
import 'dart:typed_data';
import 'package:record/record.dart';
import 'package:path_provider/path_provider.dart';
import '../core/services/data_source_interface.dart';
import '../core/services/permission_manager.dart';
import '../core/models/audio_data.dart';
import '../core/utils/content_hasher.dart';

class AudioDataSource extends BaseDataSource<AudioChunk> {
  static const String _sourceId = 'audio';
  
  final AudioRecorder _recorder = AudioRecorder();
  Timer? _chunkTimer;
  String? _deviceId;
  String? _currentRecordingPath;
  DateTime? _recordingStartTime;
  int _chunkCounter = 0;

  AudioDataSource(this._deviceId);

  @override
  String get sourceId => _sourceId;

  @override
  String get displayName => 'Microphone';

  @override
  List<String> get requiredPermissions => [
    'microphone',
  ];

  @override
  Future<bool> isAvailable() async {
    try {
      return await _recorder.hasPermission();
    } catch (e) {
      return false;
    }
  }

  @override
  Future<void> onStart() async {
    // Check permissions
    final hasPermission = await _checkPermissions();
    if (!hasPermission) {
      throw Exception('Microphone permission not granted');
    }

    // Start recording
    await _startRecording();
    
    // Set up chunking timer
    final chunkDuration = Duration(
      milliseconds: configuration['chunk_duration_ms'] ?? 5000, // Default 5 seconds
    );

    _chunkTimer = Timer.periodic(chunkDuration, (_) async {
      await _processAudioChunk();
    });
  }

  @override
  Future<void> onStop() async {
    _chunkTimer?.cancel();
    _chunkTimer = null;

    if (await _recorder.isRecording()) {
      await _recorder.stop();
    }

    // Clean up temporary files
    await _cleanupTempFiles();
  }

  Future<void> _startRecording() async {
    final tempDir = await getTemporaryDirectory();
    _currentRecordingPath = '${tempDir.path}/audio_recording_${DateTime.now().millisecondsSinceEpoch}.wav';
    _recordingStartTime = DateTime.now();
    _chunkCounter = 0;

    final config = RecordConfig(
      encoder: AudioEncoder.wav,
      sampleRate: configuration['sample_rate'] ?? 16000,
      bitRate: configuration['bit_rate'] ?? 128000,
      numChannels: configuration['channels'] ?? 1,
    );

    await _recorder.start(config, path: _currentRecordingPath!);
  }

  Future<void> _processAudioChunk() async {
    if (_deviceId == null || _currentRecordingPath == null) return;

    try {
      // Stop current recording
      await _recorder.stop();

      // Read the recorded file
      final file = File(_currentRecordingPath!);
      if (!await file.exists()) {
        print('Audio file does not exist: $_currentRecordingPath');
        return;
      }

      final audioBytes = await file.readAsBytes();
      final now = DateTime.now();
      final chunkDuration = now.difference(_recordingStartTime ?? now);

      // Create audio chunk
      final audioChunk = AudioChunk(
        deviceId: _deviceId!,
        recordedAt: _recordingStartTime ?? now,
        chunkData: Uint8List.fromList(audioBytes),
        sampleRate: configuration['sample_rate'] ?? 16000,
        channels: configuration['channels'] ?? 1,
        format: 'wav',
        durationMs: chunkDuration.inMilliseconds,
        fileId: 'chunk_${_chunkCounter++}',
        contentHash: ContentHasher.generateAudioHash(
          timestamp: _recordingStartTime ?? now,
          audioData: Uint8List.fromList(audioBytes),
          sampleRate: configuration['sample_rate'] ?? 16000,
          channels: configuration['channels'] ?? 1,
          durationMs: chunkDuration.inMilliseconds,
        ),
      );

      emitData(audioChunk);

      // Clean up the file
      await file.delete();

      // Start recording the next chunk
      await _startRecording();
    } catch (e) {
      print('Error processing audio chunk: $e');
      _updateStatus(errorMessage: e.toString());
      
      // Try to restart recording
      try {
        await _startRecording();
      } catch (restartError) {
        print('Error restarting recording: $restartError');
      }
    }
  }

  Future<bool> _checkPermissions() async {
    try {
      // Use centralized permission manager
      final permissionStatus = await PermissionManager.checkAllPermissions();
      final audioStatus = permissionStatus['audio'];
      
      if (audioStatus != null && audioStatus.isGranted) {
        return true;
      }
      
      // Try to request permission if not granted
      final result = await PermissionManager.requestDataSourcePermissions('audio');
      return result.granted;
    } catch (e) {
      print('Error checking microphone permissions: $e');
      return false;
    }
  }

  Future<void> _cleanupTempFiles() async {
    try {
      if (_currentRecordingPath != null) {
        final file = File(_currentRecordingPath!);
        if (await file.exists()) {
          await file.delete();
        }
      }
    } catch (e) {
      print('Error cleaning up temp files: $e');
    }
  }

  /// Record a single audio chunk manually
  Future<AudioChunk?> recordSingleChunk({
    Duration duration = const Duration(seconds: 5),
  }) async {
    if (_deviceId == null) return null;

    try {
      final hasPermission = await _checkPermissions();
      if (!hasPermission) return null;

      final tempDir = await getTemporaryDirectory();
      final filePath = '${tempDir.path}/single_chunk_${DateTime.now().millisecondsSinceEpoch}.wav';
      
      final config = RecordConfig(
        encoder: AudioEncoder.wav,
        sampleRate: configuration['sample_rate'] ?? 16000,
        bitRate: configuration['bit_rate'] ?? 128000,
        numChannels: configuration['channels'] ?? 1,
      );

      final startTime = DateTime.now();
      await _recorder.start(config, path: filePath);
      
      // Wait for the duration
      await Future.delayed(duration);
      
      await _recorder.stop();

      // Read the file
      final file = File(filePath);
      if (!await file.exists()) {
        return null;
      }

      final audioBytes = await file.readAsBytes();
      final actualDuration = DateTime.now().difference(startTime);

      final audioChunk = AudioChunk(
        deviceId: _deviceId!,
        recordedAt: startTime,
        chunkData: Uint8List.fromList(audioBytes),
        sampleRate: configuration['sample_rate'] ?? 16000,
        channels: configuration['channels'] ?? 1,
        format: 'wav',
        durationMs: actualDuration.inMilliseconds,
        fileId: 'manual_chunk',
        contentHash: ContentHasher.generateAudioHash(
          timestamp: startTime,
          audioData: Uint8List.fromList(audioBytes),
          sampleRate: configuration['sample_rate'] ?? 16000,
          channels: configuration['channels'] ?? 1,
          durationMs: actualDuration.inMilliseconds,
        ),
      );

      // Clean up
      await file.delete();

      return audioChunk;
    } catch (e) {
      print('Error recording single chunk: $e');
      return null;
    }
  }

  /// Check if currently recording
  Future<bool> get isRecording async {
    try {
      return await _recorder.isRecording();
    } catch (e) {
      return false;
    }
  }

  void _updateStatus({String? errorMessage}) {
    // This would normally update the parent class status
    // For now, just print the error
    if (errorMessage != null) {
      print('Audio Status Error: $errorMessage');
    }
  }

  @override
  void dispose() {
    _cleanupTempFiles();
    super.dispose();
  }
}