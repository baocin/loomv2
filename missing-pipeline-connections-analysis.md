# Loom Pipeline Missing Connections Analysis

## Summary Statistics
- Total Topics: 89
- Total Processors: 40
- Total Connections: 128
- Orphaned Topics (no incoming connections): 42
- Processors with no inputs: 3

## 1. Orphaned Topics (No Incoming Connections)

### Device Input Topics Missing from API
These topics exist but have no producer (should connect from `api_ingestion`):
- `topic_device_image_camera_raw` - Camera images
- `topic_device_image_screenshot_raw` - Screenshots
- `topic_device_video_screen_raw` - Screen recordings
- `topic_device_health_steps_raw` - Step count data
- `topic_device_metadata_raw` - Device metadata
- `topic_device_network_bluetooth_raw` - Bluetooth state
- `topic_device_network_wifi_raw` - WiFi state
- `topic_device_sensor_barometer_raw` - Barometer data
- `topic_device_sensor_temperature_raw` - Temperature data
- `topic_device_system_apps_macos_raw` - macOS app monitoring
- `topic_digital_clipboard_raw` - Clipboard content
- `topic_digital_documents_raw` - Document data
- `topic_digital_notes_raw` - Notes data
- `topic_digital_web_analytics_raw` - Web analytics
- `topic_os_events_notifications_raw` - System notifications

### Analysis Result Topics Without Producers
These topics have no processors producing them:
- `topic_analysis_3d_reconstruction_dustr_results` - Should be produced by a DUSTR 3D reconstruction processor
- `topic_analysis_audio_emotion_results` - Should be produced by an audio emotion processor
- `topic_analysis_inferred_context_qwen_results` - Should be produced by a Qwen reasoning processor
- `topic_media_video_analysis_yolo_results` - Should be produced by a YOLO video processor

### Task Result Topics Without Producers
- `topic_task_url_processed_hackernews_archived`
- `topic_task_url_processed_pdf_extracted`
- `topic_task_url_processed_twitter_archived`

### External Email Topic
- `topic_external_email_events_raw` - Appears unused (replaced by `external.email.raw`?)

### Error Topics (All Orphaned)
All error topics have no producers - processors should emit errors:
- `topic_processing_errors_accelerometer`
- `topic_processing_errors_activity_classification`
- `topic_processing_errors_app_lifecycle`
- `topic_processing_errors_audio_classifier`
- `topic_processing_errors_business_match`
- `topic_processing_errors_calendar_fetch`
- `topic_processing_errors_email_fetch`
- `topic_processing_errors_embedding`
- `topic_processing_errors_face_detection`
- `topic_processing_errors_geocoding`
- `topic_processing_errors_georegion`
- `topic_processing_errors_hn_scrape`
- `topic_processing_errors_image_preprocessing`
- `topic_processing_errors_object_detection`
- `topic_processing_errors_ocr`
- `topic_processing_errors_stt`
- `topic_processing_errors_vad`
- `topic_processing_errors_vision_preprocessing`

## 2. Processors Without Input Topics

These processors exist but have no input connections:
- `processor_calendar_fetcher` - Should consume from a scheduler/trigger topic?
- `processor_email_fetcher` - Should consume from a scheduler/trigger topic?
- `processor_hn_scraper` - Should consume from a scheduler/trigger topic?

Note: These are likely scheduled jobs rather than stream processors.

## 3. Topics Consumed But Never Produced

These topics are consumed by processors but have no producer:
- `topic_device_image_camera_raw` - Consumed by face_detector, minicpm_vision, moondream_vision, vision_preprocessor
- `topic_device_image_screenshot_raw` - Consumed by image_preprocessor
- `topic_device_network_wifi_raw` - Consumed by kafka_to_db_saver
- `topic_device_video_screen_raw` - Consumed by minicpm_vision
- `topic_digital_notes_raw` - Consumed by notes_processor, text_embedder

## 4. Missing Connections Based on Architecture

### Missing API Endpoints → Topics
The API should produce to these topics:
```
api_ingestion -> topic_device_image_camera_raw
api_ingestion -> topic_device_image_screenshot_raw
api_ingestion -> topic_device_video_screen_raw
api_ingestion -> topic_device_health_steps_raw
api_ingestion -> topic_device_metadata_raw
api_ingestion -> topic_device_network_bluetooth_raw
api_ingestion -> topic_device_network_wifi_raw
api_ingestion -> topic_device_sensor_barometer_raw
api_ingestion -> topic_device_sensor_temperature_raw
api_ingestion -> topic_device_system_apps_macos_raw
api_ingestion -> topic_digital_clipboard_raw
api_ingestion -> topic_digital_documents_raw
api_ingestion -> topic_digital_notes_raw
api_ingestion -> topic_digital_web_analytics_raw
api_ingestion -> topic_os_events_notifications_raw
```

### Missing Processor → Error Topic Connections
Each processor should emit to its error topic:
```
processor_accelerometer_aggregator -> topic_processing_errors_accelerometer
processor_activity_classifier -> topic_processing_errors_activity_classification
processor_app_lifecycle_processor -> topic_processing_errors_app_lifecycle
processor_audio_classifier -> topic_processing_errors_audio_classifier
processor_business_matcher -> topic_processing_errors_business_match
processor_calendar_fetcher -> topic_processing_errors_calendar_fetch
processor_email_fetcher -> topic_processing_errors_email_fetch
processor_embedding_generator -> topic_processing_errors_embedding
processor_face_detector -> topic_processing_errors_face_detection
processor_gps_geocoding_consumer -> topic_processing_errors_geocoding
processor_georegion_detector -> topic_processing_errors_georegion
processor_hn_scraper -> topic_processing_errors_hn_scrape
processor_image_preprocessor -> topic_processing_errors_image_preprocessing
processor_moondream_processor -> topic_processing_errors_object_detection
processor_ocr_processor -> topic_processing_errors_ocr
processor_kyutai_stt -> topic_processing_errors_stt
processor_silero_vad -> topic_processing_errors_vad
processor_vision_preprocessor -> topic_processing_errors_vision_preprocessing
```

### Missing Processor Implementations
These processors are missing based on orphaned output topics:
- DUSTR 3D reconstruction processor → `topic_analysis_3d_reconstruction_dustr_results`
- Audio emotion processor → `topic_analysis_audio_emotion_results`
- Qwen reasoning processor → `topic_analysis_inferred_context_qwen_results`
- YOLO video processor → `topic_media_video_analysis_yolo_results`
- URL processing consumers for:
  - HackerNews archiver → `topic_task_url_processed_hackernews_archived`
  - PDF extractor → `topic_task_url_processed_pdf_extracted`
  - Twitter archiver → `topic_task_url_processed_twitter_archived`

### Missing Analysis Pipeline Connections
- `topic_media_audio_vad_filtered` should connect to an audio emotion processor
- `topic_task_url_ingest` should connect to URL processing consumers

## 5. Other Structural Issues

### Duplicate/Ambiguous Topics
- `topic_external_email_events_raw` vs `topic_external_email_raw` - unclear distinction
- `topic_external_calendar_events_raw` vs `topic_external_calendar_raw` - unclear distinction

### Missing Table Writers
Some topics have no path to database storage:
- All error topics
- `topic_analysis_3d_reconstruction_dustr_results`
- `topic_analysis_audio_emotion_results`
- `topic_device_health_steps_raw`
- `topic_device_metadata_raw`
- Many device sensor topics

## Recommendations

1. **Fix API Connections**: Add the 15 missing connections from `api_ingestion` to device/digital topics
2. **Implement Error Handling**: Connect all processors to their respective error topics
3. **Add Missing Processors**: Implement the 7 missing processors identified
4. **Create Schedulers**: Add scheduler/trigger mechanisms for fetcher processors
5. **Database Writers**: Ensure all important topics have a path to persistent storage
6. **Remove Duplicates**: Clarify or consolidate duplicate topic patterns
7. **Documentation**: Update pipeline documentation to reflect actual topology
