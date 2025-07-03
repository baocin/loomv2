-- Migration: Populate pipeline structure from pipeline-visualization.yaml
-- Purpose: Define pipeline flows, stages, and topic relationships in database

-- Insert pipeline flows (high-level data processing flows)
INSERT INTO pipeline_flows (flow_name, description, priority, expected_events_per_second, average_event_size_bytes, peak_multiplier)
VALUES
    ('audio_processing', 'Audio processing pipeline with VAD and STT', 'critical', 10.0, 8192, 3.0),
    ('camera_vision', 'Camera vision processing with object detection', 'critical', 0.03, 1048576, 2.0),
    ('screenshot_ocr', 'Screenshot OCR and text extraction', 'high', 0.1, 512000, 2.0),
    ('vision_language_processing', 'Vision-language analysis with MiniCPM', 'high', 0.1, 1048576, 2.0),
    ('face_emotion_recognition', 'Face emotion detection and analysis', 'high', 0.1, 256000, 2.0),
    ('location_enrichment', 'GPS location geocoding and enrichment', 'high', 0.1, 1024, 3.0),
    ('app_lifecycle', 'Application lifecycle event processing', 'high', 2.0, 512, 2.0),
    ('context_reasoning', 'High-level context inference and reasoning', 'medium', 0.1, 4096, 2.0),
    ('text_embedding', 'Text embedding generation for search', 'medium', 0.5, 2048, 2.0),
    ('motion_classification', 'Motion and activity classification', 'medium', 50.0, 128, 5.0),
    ('power_state', 'Device power state analysis', 'medium', 0.1, 256, 2.0),
    ('digital_notes_processing', 'Digital notes ingestion and processing', 'high', 0.05, 4096, 2.0)
ON CONFLICT (flow_name) DO UPDATE
SET description = EXCLUDED.description,
    priority = EXCLUDED.priority,
    expected_events_per_second = EXCLUDED.expected_events_per_second,
    updated_at = NOW();

-- Insert pipeline stages (individual processing steps)
INSERT INTO pipeline_stages (flow_name, stage_name, stage_order, service_name, service_image, replicas, processing_timeout_seconds, sla_seconds)
VALUES
    -- Audio processing stages
    ('audio_processing', 'voice_activity_detection', 1, 'silero-vad', 'loomv2-silero-vad', 1, 5, 3),
    ('audio_processing', 'speech_to_text', 2, 'kyutai-stt', 'loomv2-kyutai-stt', 1, 10, 5),

    -- Camera vision stages
    ('camera_vision', 'object_detection', 1, 'moondream-vision', 'loomv2-moondream-vision', 1, 30, 10),
    ('camera_vision', 'face_detection', 2, 'face-detector', 'loomv2-face-detector', 1, 20, 5),

    -- Screenshot OCR stages
    ('screenshot_ocr', 'image_preprocessing', 1, 'image-preprocessor', 'loomv2-image-preprocessor', 1, 10, 5),
    ('screenshot_ocr', 'ocr_extraction', 2, 'tesseract-ocr', 'loomv2-tesseract-ocr', 1, 15, 10),

    -- Vision language processing
    ('vision_language_processing', 'vision_analysis', 1, 'minicpm-vision', 'loomv2-minicpm-vision', 1, 30, 15),

    -- Face emotion recognition
    ('face_emotion_recognition', 'emotion_detection', 1, 'face-emotion-detector', 'loomv2-face-emotion', 1, 10, 5),

    -- Location enrichment stages
    ('location_enrichment', 'geocoding', 1, 'gps-geocoding-consumer', 'loomv2-gps-geocoding', 1, 15, 10),
    ('location_enrichment', 'business_identification', 2, 'business-matcher', 'loomv2-business-matcher', 1, 20, 15),

    -- App lifecycle processing
    ('app_lifecycle', 'event_enrichment', 1, 'app-lifecycle-processor', 'loomv2-app-lifecycle', 1, 5, 2),

    -- Context reasoning
    ('context_reasoning', 'context_analysis', 1, 'mistral-reasoning', 'loomv2-mistral-reasoning', 1, 60, 30),

    -- Text embedding
    ('text_embedding', 'embedding_generation', 1, 'text-embedder', 'loomv2-text-embedder', 1, 30, 15),

    -- Motion classification
    ('motion_classification', 'activity_detection', 1, 'activity-classifier', 'loomv2-activity-classifier', 1, 5, 2),

    -- Power state analysis
    ('power_state', 'power_analysis', 1, 'power-analyzer', 'loomv2-power-analyzer', 1, 10, 5),

    -- Digital notes processing
    ('digital_notes_processing', 'notes_ingestion', 1, 'notes-processor', 'loomv2-notes-processor', 1, 10, 5)
ON CONFLICT (flow_name, stage_name) DO UPDATE
SET service_name = EXCLUDED.service_name,
    processing_timeout_seconds = EXCLUDED.processing_timeout_seconds;

-- Insert topic relationships for each stage
INSERT INTO pipeline_stage_topics (stage_id, topic_name, topic_role)
SELECT ps.id, topic_mapping.topic_name, topic_mapping.topic_role
FROM pipeline_stages ps
CROSS JOIN (
    VALUES
    -- Audio processing: VAD stage
    (1, 'silero-vad', 'device.audio.raw', 'input'),
    (1, 'silero-vad', 'media.audio.vad_filtered', 'output'),

    -- Audio processing: STT stage
    (2, 'kyutai-stt', 'media.audio.vad_filtered', 'input'),
    (2, 'kyutai-stt', 'media.text.transcribed.words', 'output'),

    -- Camera vision: Object detection
    (1, 'moondream-vision', 'device.image.camera.raw', 'input'),
    (1, 'moondream-vision', 'media.image.objects_detected', 'output'),
    (1, 'moondream-vision', 'media.image.analysis.moondream_results', 'output'),

    -- Camera vision: Face detection
    (2, 'face-detector', 'device.image.camera.raw', 'input'),
    (2, 'face-detector', 'media.image.faces_detected', 'output'),

    -- Screenshot OCR: Image preprocessing
    (1, 'image-preprocessor', 'device.image.screenshot.raw', 'input'),
    (1, 'image-preprocessor', 'device.video.screen.raw', 'input'),
    (1, 'image-preprocessor', 'media.image.screenshot.preprocessed', 'output'),

    -- Screenshot OCR: OCR extraction
    (2, 'tesseract-ocr', 'media.image.screenshot.preprocessed', 'input'),
    (2, 'tesseract-ocr', 'media.text.ocr_extracted', 'output'),
    (2, 'tesseract-ocr', 'media.text.ocr_cleaned', 'output'),

    -- Vision language processing
    (1, 'minicpm-vision', 'device.image.camera.raw', 'input'),
    (1, 'minicpm-vision', 'device.video.screen.raw', 'input'),
    (1, 'minicpm-vision', 'media.image.analysis.minicpm_results', 'output'),

    -- Face emotion recognition
    (1, 'face-emotion-detector', 'media.image.faces_detected', 'input'),
    (1, 'face-emotion-detector', 'analysis.image.emotion_results', 'output'),

    -- Location enrichment: Geocoding
    (1, 'gps-geocoding-consumer', 'device.sensor.gps.raw', 'input'),
    (1, 'gps-geocoding-consumer', 'location.address.geocoded', 'output'),
    (1, 'gps-geocoding-consumer', 'location.georegion.detected', 'output'),

    -- Location enrichment: Business identification
    (2, 'business-matcher', 'location.address.geocoded', 'input'),
    (2, 'business-matcher', 'location.business.identified', 'output'),

    -- App lifecycle processing
    (1, 'app-lifecycle-processor', 'os.events.app_lifecycle.raw', 'input'),
    (1, 'app-lifecycle-processor', 'os.events.app_lifecycle.enriched', 'output'),

    -- Context reasoning
    (1, 'mistral-reasoning', 'media.text.transcribed.words', 'input'),
    (1, 'mistral-reasoning', 'media.image.analysis.minicpm_results', 'input'),
    (1, 'mistral-reasoning', 'media.image.analysis.moondream_results', 'input'),
    (1, 'mistral-reasoning', 'analysis.inferred_context.mistral_results', 'output'),

    -- Text embedding
    (1, 'text-embedder', 'media.text.transcribed.words', 'input'),
    (1, 'text-embedder', 'media.text.ocr_extracted', 'input'),
    (1, 'text-embedder', 'digital.notes.raw', 'input'),
    (1, 'text-embedder', 'analysis.text.embedded.notes', 'output'),

    -- Motion classification
    (1, 'activity-classifier', 'device.sensor.accelerometer.raw', 'input'),
    (1, 'activity-classifier', 'motion.events.significant', 'output'),
    (1, 'activity-classifier', 'motion.classification.activity', 'output'),

    -- Power state analysis
    (1, 'power-analyzer', 'device.state.power.raw', 'input'),
    (1, 'power-analyzer', 'device.state.power.enriched', 'output'),
    (1, 'power-analyzer', 'device.state.power.patterns', 'output'),

    -- Digital notes processing
    (1, 'notes-processor', 'digital.notes.raw', 'input'),
    (1, 'notes-processor', 'media.text.notes_extracted', 'output')
) AS topic_mapping(stage_order, service_name, topic_name, topic_role)
WHERE ps.stage_order = topic_mapping.stage_order
  AND ps.service_name = topic_mapping.service_name
ON CONFLICT (stage_id, topic_name, topic_role) DO NOTHING;

-- Add all remaining topics to kafka_topics if they don't exist
INSERT INTO kafka_topics (topic_name, category, source, datatype, stage, description, retention_days)
VALUES
    ('media.audio.vad_filtered', 'media', 'audio', 'vad_filtered', NULL, 'Audio segments with voice activity detected', 7),
    ('media.image.objects_detected', 'media', 'image', 'objects_detected', NULL, 'Detected objects in images with bounding boxes', 30),
    ('media.image.faces_detected', 'media', 'image', 'faces_detected', NULL, 'Detected faces in images with landmarks', 30),
    ('media.image.screenshot.preprocessed', 'media', 'image', 'screenshot', 'preprocessed', 'Preprocessed screenshots for OCR', 7),
    ('media.text.ocr_extracted', 'media', 'text', 'ocr_extracted', NULL, 'Raw OCR text from images', 30),
    ('media.text.ocr_cleaned', 'media', 'text', 'ocr_cleaned', NULL, 'Cleaned and structured OCR text', 30),
    ('media.image.analysis.moondream_results', 'media', 'image', 'analysis', 'moondream_results', 'Moondream vision analysis results', 30),
    ('media.image.analysis.minicpm_results', 'media', 'image', 'analysis', 'minicpm_results', 'MiniCPM vision-language analysis results', 30),
    ('analysis.image.emotion_results', 'analysis', 'image', 'emotion_results', NULL, 'Face emotion recognition results', 90),
    ('location.address.geocoded', 'location', 'address', 'geocoded', NULL, 'Geocoded addresses from GPS coordinates', 90),
    ('location.georegion.detected', 'location', 'georegion', 'detected', NULL, 'Detected presence in saved georegions', 90),
    ('location.business.identified', 'location', 'business', 'identified', NULL, 'Identified businesses at locations', 90),
    ('os.events.app_lifecycle.enriched', 'os', 'events', 'app_lifecycle', 'enriched', 'Enriched app lifecycle events', 30),
    ('analysis.inferred_context.mistral_results', 'analysis', 'inferred_context', 'mistral_results', NULL, 'High-level context inferences from Mistral', 180),
    ('analysis.text.embedded.notes', 'analysis', 'text', 'embedded', 'notes', 'Text embeddings for notes', 365),
    ('motion.events.significant', 'motion', 'events', 'significant', NULL, 'Significant motion events detected', 30),
    ('motion.classification.activity', 'motion', 'classification', 'activity', NULL, 'Classified activities from motion', 90),
    ('device.state.power.enriched', 'device', 'state', 'power', 'enriched', 'Enriched power state with patterns', 30),
    ('device.state.power.patterns', 'device', 'state', 'power', 'patterns', 'Detected charging patterns', 90),
    ('media.text.notes_extracted', 'media', 'text', 'notes_extracted', NULL, 'Extracted text from digital notes', 365)
ON CONFLICT (topic_name) DO UPDATE
SET description = EXCLUDED.description,
    retention_days = EXCLUDED.retention_days,
    updated_at = NOW();

-- Verify the pipeline structure was created
SELECT
    pf.flow_name,
    pf.priority,
    COUNT(DISTINCT ps.id) as stages,
    COUNT(DISTINCT pst.topic_name) as topics
FROM pipeline_flows pf
LEFT JOIN pipeline_stages ps ON pf.flow_name = ps.flow_name
LEFT JOIN pipeline_stage_topics pst ON ps.id = pst.stage_id
GROUP BY pf.flow_name, pf.priority
ORDER BY
    CASE pf.priority
        WHEN 'critical' THEN 1
        WHEN 'high' THEN 2
        WHEN 'medium' THEN 3
        WHEN 'low' THEN 4
    END,
    pf.flow_name;
