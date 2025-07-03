"""Database connection management for the ingestion API service."""

from typing import Any

import asyncpg
import structlog

from .config import settings

logger = structlog.get_logger(__name__)


class DatabaseManager:
    """Manages database connections and operations."""

    def __init__(self):
        """Initialize database manager."""
        self.pool: asyncpg.Pool | None = None
        self.is_connected = False

    async def start(self) -> None:
        """Start database connection pool."""
        if not settings.database_url:
            logger.warning(
                "No database URL configured, skipping database initialization",
            )
            return

        logger.info("Starting database connection pool")

        try:
            self.pool = await asyncpg.create_pool(
                settings.database_url,
                min_size=2,
                max_size=10,
                command_timeout=30,
                server_settings={
                    "application_name": "ingestion-api",
                },
            )

            # Test connection
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")

            self.is_connected = True
            logger.info("Database connection pool started successfully")

        except Exception as e:
            logger.error("Failed to start database connection pool", error=str(e))
            raise

    async def stop(self) -> None:
        """Stop database connection pool."""
        logger.info("Stopping database connection pool")

        if self.pool:
            await self.pool.close()

        self.is_connected = False
        logger.info("Database connection pool stopped")

    async def get_latest_from_all_tables(self) -> dict[str, Any]:
        """Get the latest row from each table in the database.

        Returns
        -------
            Dictionary mapping table names to their latest row data

        """
        if not self.pool:
            raise RuntimeError("Database not connected")

        results = {}

        # List of tables to query - organized by category
        tables = {
            # Device Audio/Video/Image
            "device_audio_raw": "timestamp",
            "device_video_screen_raw": "timestamp",
            "device_image_camera_raw": "timestamp",
            # Device Sensors
            "device_sensor_gps_raw": "timestamp",
            "device_sensor_accelerometer_raw": "timestamp",
            "device_sensor_barometer_raw": "timestamp",
            "device_sensor_temperature_raw": "timestamp",
            "device_sensor_gyroscope_raw": "timestamp",
            "device_sensor_light_raw": "timestamp",
            "device_sensor_magnetometer_raw": "timestamp",
            # Device Health
            "device_health_heartrate_raw": "timestamp",
            "device_health_steps_raw": "timestamp",
            "device_health_sleep_raw": "timestamp",
            "device_health_blood_oxygen_raw": "timestamp",
            "device_health_blood_pressure_raw": "timestamp",
            # Device State & System
            "device_state_power_raw": "timestamp",
            "device_system_apps_macos_raw": "timestamp",
            "device_system_apps_android_raw": "timestamp",
            "device_metadata_raw": "timestamp",
            # Device Network
            "device_network_wifi_raw": "timestamp",
            "device_network_bluetooth_raw": "timestamp",
            "device_network_stats_raw": "timestamp",
            # Device Input
            "device_input_keyboard_raw": "timestamp",
            "device_input_mouse_raw": "timestamp",
            "device_input_touch_raw": "timestamp",
            # OS Events
            "os_events_app_lifecycle_raw": "timestamp",
            "os_events_system_raw": "timestamp",
            "os_events_notifications_raw": "timestamp",
            # Digital Data
            "digital_clipboard_raw": "timestamp",
            "digital_web_analytics_raw": "timestamp",
            "digital_notes_raw": "timestamp",
            "device_text_notes_raw": "timestamp",
            # External Sources
            "external_twitter_liked_raw": "timestamp",
            "external_calendar_events_raw": "timestamp",
            "external_email_events_raw": "timestamp",
            "external_hackernews_activity_raw": "timestamp",
            "external_reddit_activity_raw": "timestamp",
            "external_web_visits_raw": "timestamp",
            # Processed Media
            "media_audio_vad_filtered": "timestamp",
            "media_text_transcribed_words": "timestamp",
            "media_image_analysis_minicpm_results": "timestamp",
            # Analysis Results
            "analysis_audio_emotion_results": "timestamp",
            "analysis_image_emotion_results": "timestamp",
            "analysis_context_inference_results": "timestamp",
            "analysis_inferred_context_mistral_results": "timestamp",
            # Location
            "location_address_geocoded": "timestamp",
            "location_georegion_detected": "timestamp",
            # Motion & Activity
            "motion_events_significant": "timestamp",
            "motion_classification_activity": "timestamp",
            # Android App Usage
            "device_app_usage_android_aggregated": "timestamp",
            "device_app_usage_android_stats": "timestamp",
            "device_app_usage_android_events": "timestamp",
            # Task Results
            "task_url_processed_results": "timestamp",
            "processed_github_parsed": "timestamp",
            "processed_document_parsed": "timestamp",
            # Device Info
            "devices": "updated_at",
        }

        async with self.pool.acquire() as conn:
            for table_name, timestamp_column in tables.items():
                try:
                    # Check if table exists
                    exists = await conn.fetchval(
                        """
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables
                            WHERE table_schema = 'public'
                            AND table_name = $1
                        )
                        """,
                        table_name,
                    )

                    if not exists:
                        continue

                    # Get the latest row
                    query = f"""
                        SELECT * FROM {table_name}
                        ORDER BY {timestamp_column} DESC
                        LIMIT 1
                    """

                    row = await conn.fetchrow(query)

                    if row:
                        # Convert row to dict
                        row_dict = dict(row)

                        # Convert timestamps to ISO format for JSON serialization
                        for key, value in row_dict.items():
                            if hasattr(value, "isoformat"):
                                row_dict[key] = value.isoformat()

                        results[table_name] = {
                            "data": row_dict,
                            "row_count": await conn.fetchval(
                                f"SELECT COUNT(*) FROM {table_name}",
                            ),
                            "latest_timestamp": row_dict.get(timestamp_column),
                        }
                    else:
                        results[table_name] = {
                            "data": None,
                            "row_count": 0,
                            "latest_timestamp": None,
                        }

                except Exception as e:
                    logger.warning(
                        f"Failed to query table {table_name}",
                        table=table_name,
                        error=str(e),
                    )
                    results[table_name] = {
                        "error": str(e),
                        "data": None,
                        "row_count": None,
                        "latest_timestamp": None,
                    }

        return results


# Global database manager instance
db_manager = DatabaseManager()
