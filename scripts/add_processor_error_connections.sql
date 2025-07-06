-- Add missing processor to error topic connections
-- Each processor should emit to its corresponding error topic

-- Accelerometer processor to error topic
INSERT INTO pipeline_connections (source_id, target_id, connection_type, handle_type, created_at)
SELECT 'processor_accelerometer_aggregator', 'topic_processing_errors_accelerometer', 'produces', 'error', NOW()
WHERE EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'processor_accelerometer_aggregator')
  AND EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'topic_processing_errors_accelerometer')
ON CONFLICT (source_id, target_id) DO NOTHING;

-- Activity classifier to error topic
INSERT INTO pipeline_connections (source_id, target_id, connection_type, handle_type, created_at)
SELECT 'processor_activity_classifier', 'topic_processing_errors_activity_classification', 'produces', 'error', NOW()
WHERE EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'processor_activity_classifier')
  AND EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'topic_processing_errors_activity_classification')
ON CONFLICT (source_id, target_id) DO NOTHING;

-- App lifecycle processor to error topic
INSERT INTO pipeline_connections (source_id, target_id, connection_type, handle_type, created_at)
SELECT 'processor_app_lifecycle_processor', 'topic_processing_errors_app_lifecycle', 'produces', 'error', NOW()
WHERE EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'processor_app_lifecycle_processor')
  AND EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'topic_processing_errors_app_lifecycle')
ON CONFLICT (source_id, target_id) DO NOTHING;

-- Audio classifier to error topic
INSERT INTO pipeline_connections (source_id, target_id, connection_type, handle_type, created_at)
SELECT 'processor_audio_classifier', 'topic_processing_errors_audio_classifier', 'produces', 'error', NOW()
WHERE EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'processor_audio_classifier')
  AND EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'topic_processing_errors_audio_classifier')
ON CONFLICT (source_id, target_id) DO NOTHING;

-- Business matcher to error topic
INSERT INTO pipeline_connections (source_id, target_id, connection_type, handle_type, created_at)
SELECT 'processor_business_matcher', 'topic_processing_errors_business_match', 'produces', 'error', NOW()
WHERE EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'processor_business_matcher')
  AND EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'topic_processing_errors_business_match')
ON CONFLICT (source_id, target_id) DO NOTHING;

-- Calendar fetcher to error topic
INSERT INTO pipeline_connections (source_id, target_id, connection_type, handle_type, created_at)
SELECT 'processor_calendar_fetcher', 'topic_processing_errors_calendar_fetch', 'produces', 'error', NOW()
WHERE EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'processor_calendar_fetcher')
  AND EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'topic_processing_errors_calendar_fetch')
ON CONFLICT (source_id, target_id) DO NOTHING;

-- Email fetcher to error topic
INSERT INTO pipeline_connections (source_id, target_id, connection_type, handle_type, created_at)
SELECT 'processor_email_fetcher', 'topic_processing_errors_email_fetch', 'produces', 'error', NOW()
WHERE EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'processor_email_fetcher')
  AND EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'topic_processing_errors_email_fetch')
ON CONFLICT (source_id, target_id) DO NOTHING;

-- Embedding generator to error topic
INSERT INTO pipeline_connections (source_id, target_id, connection_type, handle_type, created_at)
SELECT 'processor_embedding_generator', 'topic_processing_errors_embedding', 'produces', 'error', NOW()
WHERE EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'processor_embedding_generator')
  AND EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'topic_processing_errors_embedding')
ON CONFLICT (source_id, target_id) DO NOTHING;

-- Face detector to error topic
INSERT INTO pipeline_connections (source_id, target_id, connection_type, handle_type, created_at)
SELECT 'processor_face_detector', 'topic_processing_errors_face_detection', 'produces', 'error', NOW()
WHERE EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'processor_face_detector')
  AND EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'topic_processing_errors_face_detection')
ON CONFLICT (source_id, target_id) DO NOTHING;

-- GPS geocoding consumer to error topic
INSERT INTO pipeline_connections (source_id, target_id, connection_type, handle_type, created_at)
SELECT 'processor_gps_geocoding_consumer', 'topic_processing_errors_geocoding', 'produces', 'error', NOW()
WHERE EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'processor_gps_geocoding_consumer')
  AND EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'topic_processing_errors_geocoding')
ON CONFLICT (source_id, target_id) DO NOTHING;

-- Georegion detector to error topic
INSERT INTO pipeline_connections (source_id, target_id, connection_type, handle_type, created_at)
SELECT 'processor_georegion_detector', 'topic_processing_errors_georegion', 'produces', 'error', NOW()
WHERE EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'processor_georegion_detector')
  AND EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'topic_processing_errors_georegion')
ON CONFLICT (source_id, target_id) DO NOTHING;

-- HackerNews scraper to error topic
INSERT INTO pipeline_connections (source_id, target_id, connection_type, handle_type, created_at)
SELECT 'processor_hn_scraper', 'topic_processing_errors_hn_scrape', 'produces', 'error', NOW()
WHERE EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'processor_hn_scraper')
  AND EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'topic_processing_errors_hn_scrape')
ON CONFLICT (source_id, target_id) DO NOTHING;

-- Image preprocessor to error topic
INSERT INTO pipeline_connections (source_id, target_id, connection_type, handle_type, created_at)
SELECT 'processor_image_preprocessor', 'topic_processing_errors_image_preprocessing', 'produces', 'error', NOW()
WHERE EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'processor_image_preprocessor')
  AND EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'topic_processing_errors_image_preprocessing')
ON CONFLICT (source_id, target_id) DO NOTHING;

-- Moondream processor to error topic
INSERT INTO pipeline_connections (source_id, target_id, connection_type, handle_type, created_at)
SELECT 'processor_moondream_processor', 'topic_processing_errors_object_detection', 'produces', 'error', NOW()
WHERE EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'processor_moondream_processor')
  AND EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'topic_processing_errors_object_detection')
ON CONFLICT (source_id, target_id) DO NOTHING;

-- OCR processor to error topic
INSERT INTO pipeline_connections (source_id, target_id, connection_type, handle_type, created_at)
SELECT 'processor_ocr_processor', 'topic_processing_errors_ocr', 'produces', 'error', NOW()
WHERE EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'processor_ocr_processor')
  AND EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'topic_processing_errors_ocr')
ON CONFLICT (source_id, target_id) DO NOTHING;

-- Kyutai STT to error topic
INSERT INTO pipeline_connections (source_id, target_id, connection_type, handle_type, created_at)
SELECT 'processor_kyutai_stt', 'topic_processing_errors_stt', 'produces', 'error', NOW()
WHERE EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'processor_kyutai_stt')
  AND EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'topic_processing_errors_stt')
ON CONFLICT (source_id, target_id) DO NOTHING;

-- Silero VAD to error topic
INSERT INTO pipeline_connections (source_id, target_id, connection_type, handle_type, created_at)
SELECT 'processor_silero_vad', 'topic_processing_errors_vad', 'produces', 'error', NOW()
WHERE EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'processor_silero_vad')
  AND EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'topic_processing_errors_vad')
ON CONFLICT (source_id, target_id) DO NOTHING;

-- Vision preprocessor to error topic
INSERT INTO pipeline_connections (source_id, target_id, connection_type, handle_type, created_at)
SELECT 'processor_vision_preprocessor', 'topic_processing_errors_vision_preprocessing', 'produces', 'error', NOW()
WHERE EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'processor_vision_preprocessor')
  AND EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'topic_processing_errors_vision_preprocessing')
ON CONFLICT (source_id, target_id) DO NOTHING;

-- MiniCPM Vision to error topic (assuming it exists)
INSERT INTO pipeline_connections (source_id, target_id, connection_type, handle_type, created_at)
SELECT 'processor_minicpm_vision', 'topic_processing_errors_vision_preprocessing', 'produces', 'error', NOW()
WHERE EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'processor_minicpm_vision')
  AND EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'topic_processing_errors_vision_preprocessing')
ON CONFLICT (source_id, target_id) DO NOTHING;

-- Mistral processor to error topic (assuming it exists)
INSERT INTO pipeline_connections (source_id, target_id, connection_type, handle_type, created_at)
SELECT 'processor_mistral_processor', 'topic_processing_errors_embedding', 'produces', 'error', NOW()
WHERE EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'processor_mistral_processor')
  AND EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'topic_processing_errors_embedding')
ON CONFLICT (source_id, target_id) DO NOTHING;

-- Notes processor to error topic (assuming it exists)
INSERT INTO pipeline_connections (source_id, target_id, connection_type, handle_type, created_at)
SELECT 'processor_notes_processor', 'topic_processing_errors_embedding', 'produces', 'error', NOW()
WHERE EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'processor_notes_processor')
  AND EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'topic_processing_errors_embedding')
ON CONFLICT (source_id, target_id) DO NOTHING;

-- Text embedder to error topic (assuming it exists)
INSERT INTO pipeline_connections (source_id, target_id, connection_type, handle_type, created_at)
SELECT 'processor_text_embedder', 'topic_processing_errors_embedding', 'produces', 'error', NOW()
WHERE EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'processor_text_embedder')
  AND EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'topic_processing_errors_embedding')
ON CONFLICT (source_id, target_id) DO NOTHING;

-- Step counter to error topic (assuming it exists)
INSERT INTO pipeline_connections (source_id, target_id, connection_type, handle_type, created_at)
SELECT 'processor_step_counter', 'topic_processing_errors_activity_classification', 'produces', 'error', NOW()
WHERE EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'processor_step_counter')
  AND EXISTS (SELECT 1 FROM pipeline_nodes WHERE node_id = 'topic_processing_errors_activity_classification')
ON CONFLICT (source_id, target_id) DO NOTHING;

-- Count the connections added
SELECT COUNT(*) as connections_added
FROM pipeline_connections
WHERE connection_type = 'produces'
  AND handle_type = 'error'
  AND created_at >= NOW() - INTERVAL '1 minute';
