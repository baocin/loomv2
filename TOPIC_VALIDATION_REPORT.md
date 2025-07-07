# Kafka Topic Mappings Validation Report

## Summary

This report validates the topic mappings defined in `/services/kafka-to-db-consumer/config/topic_mappings.yml` against the actual service implementations in the codebase.

## Validation Results

### ✅ Verified Producer-Consumer Pairs

1. **device.audio.raw**
   - **Producer**: `ingestion-api` (via `/audio/upload` and WebSocket endpoints)
   - **Consumers**: `silero-vad`, `kyutai-stt`
   - **Database Table**: `device_audio_raw`
   - **Status**: ✅ Fully implemented and mapped correctly

2. **device.sensor.gps.raw**
   - **Producer**: `ingestion-api` (via `/sensor/gps` endpoint)
   - **Consumers**: `gps-geocoding-consumer`, `georegion-detector`
   - **Database Table**: `device_sensor_gps_raw`
   - **Status**: ✅ Fully implemented and mapped correctly

3. **device.sensor.accelerometer.raw**
   - **Producer**: `ingestion-api` (via `/sensor/accelerometer` endpoint)
   - **Consumers**: `significant-motion-detector`, `activity-classifier`
   - **Database Table**: `device_sensor_accelerometer_raw`
   - **Status**: ✅ Fully implemented and mapped correctly

4. **device.network.bluetooth.raw**
   - **Producer**: `ingestion-api` (via `/sensor/bluetooth` endpoint)
   - **Consumer**: `kafka-to-db-consumer`
   - **Database Table**: `device_network_bluetooth_raw`
   - **Status**: ✅ Fully implemented and mapped correctly

5. **os.events.app_lifecycle.raw**
   - **Producer**: `ingestion-api` (via `/os-events/app-lifecycle` endpoint)
   - **Consumer**: `kafka-to-db-consumer`
   - **Database Table**: `os_events_app_lifecycle_raw`
   - **Status**: ✅ Fully implemented and mapped correctly

6. **os.events.system.raw**
   - **Producer**: `ingestion-api` (via `/os-events/system` endpoint)
   - **Consumer**: `kafka-to-db-consumer`
   - **Database Table**: `os_events_system_raw`
   - **Status**: ✅ Fully implemented and mapped correctly

7. **device.system.apps.android.raw**
   - **Producer**: `ingestion-api` (via `/system/apps/android` endpoint)
   - **Consumer**: `kafka-to-db-consumer`
   - **Database Table**: `device_system_apps_android_raw`
   - **Status**: ✅ Fully implemented and mapped correctly

8. **external.calendar.events.raw**
   - **Producer**: `calendar-fetcher` service
   - **Consumer**: `kafka-to-db-consumer`
   - **Database Table**: `external_calendar_events_raw`
   - **Status**: ✅ Fully implemented and mapped correctly

9. **external.email.events.raw**
   - **Producer**: `email-fetcher` service
   - **Consumer**: `kafka-to-db-consumer`
   - **Database Table**: `external_email_events_raw`
   - **Status**: ✅ Fully implemented and mapped correctly

10. **media.audio.vad_filtered**
    - **Producer**: `silero-vad` service
    - **Consumer**: `kafka-to-db-consumer`, `kyutai-stt`
    - **Database Table**: `media_audio_voice_segments_raw`
    - **Status**: ✅ Fully implemented and mapped correctly

### ⚠️ Topics Defined but Not Actively Used

These topics are defined in the mappings but don't have active producers yet:

1. **device.video.screen.raw** - No active screen recording implementation
2. **device.sensor.barometer.raw** - No barometer sensor endpoint
3. **device.sensor.temperature.raw** - No temperature sensor endpoint
4. **device.health.steps.raw** - No step counter endpoint
5. **device.metadata.raw** - Endpoint exists but usage unclear
6. **os.events.notifications.raw** - No notification tracking implementation
7. **digital.clipboard.raw** - No clipboard monitoring implementation

### 📊 Field Mapping Validation

The field mappings are generally correct with the following patterns:

1. **Nested Data Access**: The mappings correctly handle nested JSON structures using dot notation (e.g., `data.latitude`, `metadata.activity`)

2. **Multiple Path Support**: Some fields support multiple input paths for backwards compatibility (e.g., `chunk_data`, `data.chunk_data`, `data.audio_data` all map to `audio_data`)

3. **Type Conversions**: Proper data type definitions for PostgreSQL mapping (e.g., `timestamp`, `float`, `integer`, `boolean`)

4. **Array Mappings**: Complex array handling for topics like `media.text.transcribed.words` with proper element mapping

### 🔧 Recommendations

1. **Remove Unused Topics**: Consider removing topic mappings that don't have corresponding producers to reduce confusion

2. **Standardize Field Names**: Some inconsistencies exist in field naming (e.g., `chunk_data` vs `audio_data`)

3. **Document Required Fields**: The `required_fields` lists should be validated against actual API endpoints

4. **Version Management**: Consider adding version checks to ensure schema compatibility

## Conclusion

The topic mappings are largely accurate and properly maintained. The system successfully routes data from producers through Kafka topics to the database tables. The main area for improvement is cleaning up unused topic definitions and standardizing field naming conventions.

All active data flows are properly configured and the kafka-to-db-consumer service correctly handles the field mappings for database insertion.
