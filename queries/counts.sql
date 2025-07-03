-- Simple table counts query
-- Returns table_name and count for all tables

SELECT 'analysis_audio_emotion_results' as table_name, COUNT(*) as count FROM analysis_audio_emotion_results
UNION ALL
SELECT 'analysis_audio_emotion_scores_raw', COUNT(*) FROM analysis_audio_emotion_scores_raw
UNION ALL
SELECT 'analysis_context_inference_results', COUNT(*) FROM analysis_context_inference_results
UNION ALL
SELECT 'analysis_context_reasoning_chains_raw', COUNT(*) FROM analysis_context_reasoning_chains_raw
UNION ALL
SELECT 'analysis_image_emotion_results', COUNT(*) FROM analysis_image_emotion_results
UNION ALL
SELECT 'analysis_image_face_emotions_raw', COUNT(*) FROM analysis_image_face_emotions_raw
UNION ALL
SELECT 'analysis_image_recognition_results', COUNT(*) FROM analysis_image_recognition_results
UNION ALL
SELECT 'analysis_inferred_context_mistral_results', COUNT(*) FROM analysis_inferred_context_mistral_results
UNION ALL
SELECT 'analysis_text_embedded_notes', COUNT(*) FROM analysis_text_embedded_notes
UNION ALL
SELECT 'analysis_text_embedded_notifications', COUNT(*) FROM analysis_text_embedded_notifications
UNION ALL
SELECT 'analysis_transcription_results', COUNT(*) FROM analysis_transcription_results
UNION ALL
SELECT 'cached_geocoding', COUNT(*) FROM cached_geocoding
UNION ALL
SELECT 'device_app_usage_android_aggregated', COUNT(*) FROM device_app_usage_android_aggregated
UNION ALL
SELECT 'device_app_usage_android_categories', COUNT(*) FROM device_app_usage_android_categories
UNION ALL
SELECT 'device_app_usage_android_events', COUNT(*) FROM device_app_usage_android_events
UNION ALL
SELECT 'device_app_usage_android_notifications', COUNT(*) FROM device_app_usage_android_notifications
UNION ALL
SELECT 'device_app_usage_android_stats', COUNT(*) FROM device_app_usage_android_stats
UNION ALL
SELECT 'device_audio_raw', COUNT(*) FROM device_audio_raw
UNION ALL
SELECT 'device_health_blood_oxygen_raw', COUNT(*) FROM device_health_blood_oxygen_raw
UNION ALL
SELECT 'device_health_blood_pressure_raw', COUNT(*) FROM device_health_blood_pressure_raw
UNION ALL
SELECT 'device_health_heartrate_raw', COUNT(*) FROM device_health_heartrate_raw
UNION ALL
SELECT 'device_health_sleep_raw', COUNT(*) FROM device_health_sleep_raw
UNION ALL
SELECT 'device_health_steps_raw', COUNT(*) FROM device_health_steps_raw
UNION ALL
SELECT 'device_image_camera_raw', COUNT(*) FROM device_image_camera_raw
UNION ALL
SELECT 'device_input_keyboard_raw', COUNT(*) FROM device_input_keyboard_raw
UNION ALL
SELECT 'device_input_mouse_raw', COUNT(*) FROM device_input_mouse_raw
UNION ALL
SELECT 'device_input_touch_raw', COUNT(*) FROM device_input_touch_raw
UNION ALL
SELECT 'device_metadata_raw', COUNT(*) FROM device_metadata_raw
UNION ALL
SELECT 'device_network_bluetooth_raw', COUNT(*) FROM device_network_bluetooth_raw
UNION ALL
SELECT 'device_network_stats_raw', COUNT(*) FROM device_network_stats_raw
UNION ALL
SELECT 'device_network_wifi_raw', COUNT(*) FROM device_network_wifi_raw
UNION ALL
SELECT 'device_sensor_accelerometer_raw', COUNT(*) FROM device_sensor_accelerometer_raw
UNION ALL
SELECT 'device_sensor_barometer_raw', COUNT(*) FROM device_sensor_barometer_raw
UNION ALL
SELECT 'device_sensor_gps_raw', COUNT(*) FROM device_sensor_gps_raw
UNION ALL
SELECT 'device_sensor_gyroscope_raw', COUNT(*) FROM device_sensor_gyroscope_raw
UNION ALL
SELECT 'device_sensor_light_raw', COUNT(*) FROM device_sensor_light_raw
UNION ALL
SELECT 'device_sensor_magnetometer_raw', COUNT(*) FROM device_sensor_magnetometer_raw
UNION ALL
SELECT 'device_sensor_temperature_raw', COUNT(*) FROM device_sensor_temperature_raw
UNION ALL
SELECT 'device_state_power_raw', COUNT(*) FROM device_state_power_raw
UNION ALL
SELECT 'device_system_apps_android_raw', COUNT(*) FROM device_system_apps_android_raw
UNION ALL
SELECT 'device_system_apps_macos_raw', COUNT(*) FROM device_system_apps_macos_raw
UNION ALL
SELECT 'device_text_notes_raw', COUNT(*) FROM device_text_notes_raw
UNION ALL
SELECT 'device_video_screen_raw', COUNT(*) FROM device_video_screen_raw
UNION ALL
SELECT 'devices', COUNT(*) FROM devices
UNION ALL
SELECT 'digital_clipboard_raw', COUNT(*) FROM digital_clipboard_raw
UNION ALL
SELECT 'digital_notes_raw', COUNT(*) FROM digital_notes_raw
UNION ALL
SELECT 'digital_web_analytics_raw', COUNT(*) FROM digital_web_analytics_raw
UNION ALL
SELECT 'emails_with_embeddings', COUNT(*) FROM emails_with_embeddings
UNION ALL
SELECT 'embeddings_image_nomic', COUNT(*) FROM embeddings_image_nomic
UNION ALL
SELECT 'embeddings_text_nomic', COUNT(*) FROM embeddings_text_nomic
UNION ALL
SELECT 'external_calendar_events_raw', COUNT(*) FROM external_calendar_events_raw
UNION ALL
SELECT 'external_email_events_raw', COUNT(*) FROM external_email_events_raw
UNION ALL
SELECT 'external_hackernews_activity_raw', COUNT(*) FROM external_hackernews_activity_raw
UNION ALL
SELECT 'external_twitter_images_raw', COUNT(*) FROM external_twitter_images_raw
UNION ALL
SELECT 'external_twitter_liked_raw', COUNT(*) FROM external_twitter_liked_raw
UNION ALL
SELECT 'external_web_visits_raw', COUNT(*) FROM external_web_visits_raw
UNION ALL
SELECT 'georegions', COUNT(*) FROM georegions
UNION ALL
SELECT 'internal_scheduled_jobs_status', COUNT(*) FROM internal_scheduled_jobs_status
UNION ALL
SELECT 'location_address_geocoded', COUNT(*) FROM location_address_geocoded
UNION ALL
SELECT 'location_georegion_detected', COUNT(*) FROM location_georegion_detected
UNION ALL
SELECT 'media_audio_vad_filtered', COUNT(*) FROM media_audio_vad_filtered
UNION ALL
SELECT 'media_audio_voice_segments_raw', COUNT(*) FROM media_audio_voice_segments_raw
UNION ALL
SELECT 'media_image_analysis_minicpm_results', COUNT(*) FROM media_image_analysis_minicpm_results
UNION ALL
SELECT 'media_image_vision_annotations_raw', COUNT(*) FROM media_image_vision_annotations_raw
UNION ALL
SELECT 'media_text_transcribed_words', COUNT(*) FROM media_text_transcribed_words
UNION ALL
SELECT 'media_text_word_timestamps_raw', COUNT(*) FROM media_text_word_timestamps_raw
UNION ALL
SELECT 'motion_classification_activity', COUNT(*) FROM motion_classification_activity
UNION ALL
SELECT 'motion_events_significant', COUNT(*) FROM motion_events_significant
UNION ALL
SELECT 'os_events_app_lifecycle_raw', COUNT(*) FROM os_events_app_lifecycle_raw
UNION ALL
SELECT 'os_events_notifications_raw', COUNT(*) FROM os_events_notifications_raw
UNION ALL
SELECT 'os_events_system_raw', COUNT(*) FROM os_events_system_raw
UNION ALL
SELECT 'processed_document_parsed', COUNT(*) FROM processed_document_parsed
UNION ALL
SELECT 'processed_github_parsed', COUNT(*) FROM processed_github_parsed
UNION ALL
SELECT 'schema_migrations', COUNT(*) FROM schema_migrations
UNION ALL
SELECT 'task_url_ingest', COUNT(*) FROM task_url_ingest
UNION ALL
SELECT 'task_url_processed_content_raw', COUNT(*) FROM task_url_processed_content_raw
UNION ALL
SELECT 'task_url_processed_results', COUNT(*) FROM task_url_processed_results
UNION ALL
SELECT 'twitter_extraction_results', COUNT(*) FROM twitter_extraction_results
UNION ALL
SELECT 'twitter_likes_with_embeddings', COUNT(*) FROM twitter_likes_with_embeddings
UNION ALL
SELECT 'twitter_posts', COUNT(*) FROM twitter_posts
ORDER BY count DESC, table_name;
