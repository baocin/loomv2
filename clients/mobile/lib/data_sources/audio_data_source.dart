import 'dart:async';
import 'dart:io';
import 'dart:typed_data';
import 'package:record/record.dart';
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart' as permission_handler;
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
    print('AUDIO: Starting audio data source...');
    
    // Check permissions
    print('AUDIO: Checking permissions...');
    final hasPermission = await _checkPermissions();
    if (!hasPermission) {
      print('AUDIO: ERROR - Microphone permission not granted');
      throw Exception('Microphone permission not granted');
    }
    print('AUDIO: Permissions granted, proceeding with recording setup');

    // Start recording
    print('AUDIO: Starting recording...');
    await _startRecording();
    print('AUDIO: Recording started successfully');
    
    // Set up chunking timer
    final chunkDuration = Duration(
      milliseconds: configuration['chunk_duration_ms'] ?? 5000, // Default 5 seconds
    );
    print('AUDIO: Setting up chunk timer with duration: ${chunkDuration.inMilliseconds}ms');

    _chunkTimer = Timer.periodic(chunkDuration, (_) async {
      print('AUDIO: Chunk timer triggered - processing audio chunk...');
      await _processAudioChunk();
    });
    print('AUDIO: Audio data source started successfully');
  }

  @override
  Future<void> onStop() async {
    print('AUDIO: Stopping audio data source...');
    
    _chunkTimer?.cancel();
    _chunkTimer = null;
    print('AUDIO: Chunk timer cancelled');

    if (await _recorder.isRecording()) {
      print('AUDIO: Stopping active recording...');
      await _recorder.stop();
      print('AUDIO: Recording stopped');
    } else {
      print('AUDIO: No active recording to stop');
    }

    // Clean up temporary files
    print('AUDIO: Cleaning up temporary files...');
    await _cleanupTempFiles();
    print('AUDIO: Audio data source stopped successfully');
  }

  Future<void> _startRecording() async {
    final tempDir = await getTemporaryDirectory();
    _currentRecordingPath = '${tempDir.path}/audio_recording_${DateTime.now().millisecondsSinceEpoch}.wav';
    _recordingStartTime = DateTime.now();
    _chunkCounter = 0;

    print('AUDIO: Recording path: $_currentRecordingPath');
    print('AUDIO: Recording start time: $_recordingStartTime');

    final config = RecordConfig(
      encoder: AudioEncoder.wav,
      sampleRate: configuration['sample_rate'] ?? 16000,
      bitRate: configuration['bit_rate'] ?? 128000,
      numChannels: configuration['channels'] ?? 1,
    );

    print('AUDIO: Recording config - sampleRate: ${config.sampleRate}, bitRate: ${config.bitRate}, channels: ${config.numChannels}');
    
    try {
      await _recorder.start(config, path: _currentRecordingPath!);
      print('AUDIO: Recorder.start() completed successfully');
      
      // Verify recording is actually running
      final isRecording = await _recorder.isRecording();
      print('AUDIO: Recording status after start: $isRecording');
      
      if (!isRecording) {
        throw Exception('Failed to start recording - recorder reports not recording');
      }
    } catch (e) {
      print('AUDIO: ERROR starting recording: $e');
      rethrow;
    }
  }

  Future<void> _processAudioChunk() async {
    print('AUDIO: _processAudioChunk() called');
    
    if (_deviceId == null) {
      print('AUDIO: ERROR - Device ID is null, cannot process chunk');
      return;
    }
    
    if (_currentRecordingPath == null) {
      print('AUDIO: ERROR - Current recording path is null, cannot process chunk');
      return;
    }

    print('AUDIO: Processing chunk for device: $_deviceId');
    print('AUDIO: Recording path: $_currentRecordingPath');

    try {
      // Check if recorder is actually recording
      final isRecordingBefore = await _recorder.isRecording();
      print('AUDIO: Recording status before stop: $isRecordingBefore');
      
      // Stop current recording
      if (isRecordingBefore) {
        print('AUDIO: Stopping current recording...');
        await _recorder.stop();
        print('AUDIO: Recording stopped successfully');
      } else {
        print('AUDIO: WARNING - Recorder was not recording when chunk timer fired');
      }

      // Read the recorded file
      final file = File(_currentRecordingPath!);
      print('AUDIO: Checking if file exists: ${file.path}');
      
      if (!await file.exists()) {
        print('AUDIO: ERROR - Audio file does not exist: $_currentRecordingPath');
        return;
      }

      final audioBytes = await file.readAsBytes();
      final fileSize = audioBytes.length;
      print('AUDIO: Read audio file successfully - size: $fileSize bytes');
      
      if (fileSize == 0) {
        print('AUDIO: WARNING - Audio file is empty (0 bytes)');
        return;
      }

      final now = DateTime.now();
      final chunkDuration = now.difference(_recordingStartTime ?? now);
      print('AUDIO: Chunk duration: ${chunkDuration.inMilliseconds}ms');

      // Create audio chunk
      print('AUDIO: Creating AudioChunk object...');
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
      print('AUDIO: AudioChunk created - fileId: ${audioChunk.fileId}, size: ${audioChunk.chunkData.length} bytes');

      print('AUDIO: Emitting audio chunk to data stream...');
      emitData(audioChunk);
      print('AUDIO: Audio chunk emitted successfully');

      // Clean up the file
      print('AUDIO: Deleting temporary audio file...');
      await file.delete();
      print('AUDIO: Temporary file deleted');

      // Start recording the next chunk
      print('AUDIO: Starting recording for next chunk...');
      await _startRecording();
      print('AUDIO: Next chunk recording started');
    } catch (e) {
      print('AUDIO: ERROR processing audio chunk: $e');
      print('AUDIO: Stack trace: ${StackTrace.current}');
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
      print('AUDIO: Checking permissions with PermissionManager...');
      
      // Use centralized permission manager
      final permissionStatus = await PermissionManager.checkAllPermissions();
      final audioStatus = permissionStatus['audio'];
      
      print('AUDIO: Permission status for audio: $audioStatus');
      
      // Check if permission is granted using the correct enum comparison
      if (audioStatus != null && audioStatus == permission_handler.PermissionStatus.granted) {
        print('AUDIO: Microphone permission already granted');
        return true;
      }
      
      print('AUDIO: Microphone permission not granted, requesting...');
      
      // Try to request permission if not granted
      final result = await PermissionManager.requestDataSourcePermissions('audio');
      print('AUDIO: Permission request result: granted=${result.granted}');
      
      return result.granted;
    } catch (e) {
      print('AUDIO: ERROR checking microphone permissions: $e');
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