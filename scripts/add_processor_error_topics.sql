-- Add error topics to processors in pipeline_stage_topics
-- Each processor should have an error topic output

-- First, let's see what processors we have
SELECT
    ps.id,
    ps.stage_name,
    ps.service_name,
    COUNT(pst.topic_name) FILTER (WHERE pst.topic_role = 'error') as error_topics
FROM pipeline_stages ps
LEFT JOIN pipeline_stage_topics pst ON ps.id = pst.stage_id AND pst.topic_role = 'error'
WHERE ps.service_name LIKE '%processor%'
   OR ps.service_name LIKE '%consumer%'
   OR ps.service_name LIKE '%detector%'
   OR ps.service_name LIKE '%classifier%'
   OR ps.service_name LIKE '%fetcher%'
   OR ps.service_name LIKE '%scraper%'
   OR ps.service_name LIKE '%matcher%'
   OR ps.service_name LIKE '%stt%'
   OR ps.service_name LIKE '%vad%'
GROUP BY ps.id, ps.stage_name, ps.service_name
ORDER BY ps.stage_name;

-- Add error topics for processors that don't have them
-- This is a template - we'll need to match actual processor names with error topics

-- Helper function to add error topic to a processor
CREATE OR REPLACE FUNCTION add_error_topic_to_processor(
    p_service_name TEXT,
    p_error_topic TEXT
) RETURNS VOID AS $$
DECLARE
    v_stage_id INTEGER;
BEGIN
    -- Find the stage ID for this processor
    SELECT id INTO v_stage_id
    FROM pipeline_stages
    WHERE service_name = p_service_name
    LIMIT 1;

    IF v_stage_id IS NOT NULL THEN
        -- Add the error topic if it doesn't exist
        INSERT INTO pipeline_stage_topics (stage_id, topic_name, topic_role)
        VALUES (v_stage_id, p_error_topic, 'error')
        ON CONFLICT (stage_id, topic_name, topic_role) DO NOTHING;

        RAISE NOTICE 'Added error topic % to processor %', p_error_topic, p_service_name;
    ELSE
        RAISE NOTICE 'Processor % not found', p_service_name;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Add error topics based on common patterns
-- Map service names to their expected error topics

-- Accelerometer processor
SELECT add_error_topic_to_processor('accelerometer-aggregator', 'processing.errors.accelerometer');
SELECT add_error_topic_to_processor('activity-classifier', 'processing.errors.activity_classification');

-- Audio processors
SELECT add_error_topic_to_processor('silero-vad', 'processing.errors.vad');
SELECT add_error_topic_to_processor('kyutai-stt', 'processing.errors.stt');
SELECT add_error_topic_to_processor('audio-classifier', 'processing.errors.audio_classifier');

-- Vision processors
SELECT add_error_topic_to_processor('face-detector', 'processing.errors.face_detection');
SELECT add_error_topic_to_processor('vision-preprocessor', 'processing.errors.vision_preprocessing');
SELECT add_error_topic_to_processor('image-preprocessor', 'processing.errors.image_preprocessing');
SELECT add_error_topic_to_processor('ocr-processor', 'processing.errors.ocr');
SELECT add_error_topic_to_processor('moondream-vision', 'processing.errors.object_detection');
SELECT add_error_topic_to_processor('minicpm-vision', 'processing.errors.vision_preprocessing');

-- Location processors
SELECT add_error_topic_to_processor('gps-geocoding-consumer', 'processing.errors.geocoding');
SELECT add_error_topic_to_processor('georegion-detector', 'processing.errors.georegion');
SELECT add_error_topic_to_processor('business-matcher', 'processing.errors.business_match');

-- External data processors
SELECT add_error_topic_to_processor('calendar-fetcher', 'processing.errors.calendar_fetch');
SELECT add_error_topic_to_processor('email-fetcher', 'processing.errors.email_fetch');
SELECT add_error_topic_to_processor('hn-scraper', 'processing.errors.hn_scrape');

-- Other processors
SELECT add_error_topic_to_processor('embedding-generator', 'processing.errors.embedding');
SELECT add_error_topic_to_processor('text-embedder', 'processing.errors.embedding');
SELECT add_error_topic_to_processor('app-lifecycle-processor', 'processing.errors.app_lifecycle');
SELECT add_error_topic_to_processor('step-counter', 'processing.errors.activity_classification');
SELECT add_error_topic_to_processor('notes-processor', 'processing.errors.embedding');

-- Also try with underscores instead of hyphens (in case naming convention differs)
SELECT add_error_topic_to_processor('accelerometer_aggregator', 'processing.errors.accelerometer');
SELECT add_error_topic_to_processor('activity_classifier', 'processing.errors.activity_classification');
SELECT add_error_topic_to_processor('silero_vad', 'processing.errors.vad');
SELECT add_error_topic_to_processor('kyutai_stt', 'processing.errors.stt');
SELECT add_error_topic_to_processor('face_detector', 'processing.errors.face_detection');
SELECT add_error_topic_to_processor('gps_geocoding_consumer', 'processing.errors.geocoding');
SELECT add_error_topic_to_processor('georegion_detector', 'processing.errors.georegion');

-- Show the results
SELECT
    ps.stage_name,
    ps.service_name,
    pst.topic_name as error_topic,
    pst.topic_role
FROM pipeline_stages ps
LEFT JOIN pipeline_stage_topics pst ON ps.id = pst.stage_id AND pst.topic_role = 'error'
WHERE ps.service_name LIKE '%processor%'
   OR ps.service_name LIKE '%consumer%'
   OR ps.service_name LIKE '%detector%'
   OR ps.service_name LIKE '%classifier%'
   OR ps.service_name LIKE '%fetcher%'
   OR ps.service_name LIKE '%scraper%'
   OR ps.service_name LIKE '%matcher%'
   OR ps.service_name LIKE '%stt%'
   OR ps.service_name LIKE '%vad%'
ORDER BY ps.stage_name;

-- Clean up the helper function
DROP FUNCTION IF EXISTS add_error_topic_to_processor(TEXT, TEXT);
