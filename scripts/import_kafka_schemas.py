#!/usr/bin/env python3
"""
Import existing Kafka topic definitions, schemas, and flow configurations
into the new schema management tables in TimescaleDB.
"""

import asyncio
import json
import os
import re
import sys
from pathlib import Path

import asyncpg
import yaml


class KafkaSchemaImporter:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.conn = None
        self.base_path = Path(__file__).parent.parent

    async def connect(self):
        """Connect to the database."""
        self.conn = await asyncpg.connect(self.database_url)

    async def disconnect(self):
        """Disconnect from the database."""
        if self.conn:
            await self.conn.close()

    async def clear_existing_data(self):
        """Clear existing data from schema management tables."""
        print("Clearing existing schema management data...")
        tables = [
            "pipeline_stage_topics",
            "topic_field_mappings",
            "topic_table_configs",
            "pipeline_stages",
            "pipeline_flows",
            "kafka_topic_schemas",
            "kafka_topics",
        ]

        for table in tables:
            await self.conn.execute(f"TRUNCATE TABLE {table} CASCADE")
        print("✓ Cleared existing data")

    async def import_kafka_topics_from_claude_md(self):
        """Import Kafka topics from CLAUDE.md documentation."""
        print("\nImporting Kafka topics from CLAUDE.md...")

        claude_md_path = self.base_path / "CLAUDE.md"
        with open(claude_md_path, "r") as f:
            content = f.read()

        # Extract the Kafka Topics section
        topics_section = re.search(r"### Kafka Topics.*?(?=###|\Z)", content, re.DOTALL)
        if not topics_section:
            print("✗ Could not find Kafka Topics section in CLAUDE.md")
            return

        # Parse topics by section
        topic_configs = {
            # Raw Data Ingestion Topics
            "device.audio.raw": {"retention": 7, "desc": "Raw microphone audio chunks"},
            "device.video.screen.raw": {
                "retention": 7,
                "desc": "Keyframes from screen recordings",
            },
            "device.image.camera.raw": {
                "retention": 7,
                "desc": "Photos from cameras and screenshots",
            },
            "device.image.screenshot.raw": {
                "retention": 7,
                "desc": "Raw screenshot images from device",
            },
            "device.sensor.gps.raw": {
                "retention": 30,
                "desc": "GPS coordinates with accuracy",
            },
            "device.sensor.accelerometer.raw": {
                "retention": 30,
                "desc": "3-axis motion data",
            },
            "device.sensor.barometer.raw": {
                "retention": 30,
                "desc": "Atmospheric pressure data",
            },
            "device.sensor.temperature.raw": {
                "retention": 30,
                "desc": "Device temperature readings",
            },
            "device.health.heartrate.raw": {
                "retention": 60,
                "desc": "Heart rate measurements",
            },
            "device.health.steps.raw": {"retention": 60, "desc": "Step count data"},
            "device.state.power.raw": {
                "retention": 30,
                "desc": "Battery level and charging status",
            },
            "device.system.apps.macos.raw": {
                "retention": 30,
                "desc": "macOS app monitoring data",
            },
            "device.system.apps.android.raw": {
                "retention": 30,
                "desc": "Android app monitoring data",
            },
            "device.metadata.raw": {
                "retention": 90,
                "desc": "Arbitrary device metadata",
            },
            "device.network.wifi.raw": {
                "retention": 30,
                "desc": "Wi-Fi connection state",
            },
            "device.network.bluetooth.raw": {
                "retention": 30,
                "desc": "Nearby Bluetooth devices",
            },
            "os.events.app_lifecycle.raw": {
                "retention": 30,
                "desc": "Android app lifecycle events",
            },
            "os.events.system.raw": {
                "retention": 30,
                "desc": "System events (screen on/off, lock/unlock, power)",
            },
            "os.events.notifications.raw": {
                "retention": 30,
                "desc": "System notifications",
            },
            "digital.clipboard.raw": {"retention": 30, "desc": "Clipboard content"},
            "digital.web_analytics.raw": {
                "retention": 30,
                "desc": "Website analytics data",
            },
            "digital.notes.raw": {
                "retention": 30,
                "desc": "Digital notes and text documents",
            },
            "digital.documents.raw": {
                "retention": 30,
                "desc": "Various document types (PDFs, docs, etc)",
            },
            "external.twitter.liked.raw": {
                "retention": 90,
                "desc": "Scraped liked Twitter/X posts",
            },
            "external.calendar.events.raw": {
                "retention": 90,
                "desc": "Calendar events (CalDAV)",
            },
            "external.email.events.raw": {
                "retention": 90,
                "desc": "Email events (all IMAP accounts)",
            },
            "task.url.ingest": {
                "retention": 7,
                "desc": "URLs to be processed (Twitter links, PDFs, web pages)",
            },
            # Processed Data Topics
            "media.audio.vad_filtered": {
                "retention": 7,
                "desc": "Audio chunks identified as speech",
            },
            "media.audio.environment_classified": {
                "retention": 7,
                "desc": "Audio environment classification (indoor/outdoor/vehicle)",
            },
            "media.text.transcribed.words": {
                "retention": 30,
                "desc": "Word-by-word transcripts from speech",
            },
            "media.text.ocr_extracted": {
                "retention": 30,
                "desc": "Raw OCR text from images",
            },
            "media.text.ocr_cleaned": {
                "retention": 30,
                "desc": "Cleaned and structured OCR text",
            },
            "media.image.camera.preprocessed": {
                "retention": 7,
                "desc": "Normalized camera images",
            },
            "media.image.screenshot.preprocessed": {
                "retention": 7,
                "desc": "Preprocessed screenshots for OCR",
            },
            "media.image.objects_detected": {
                "retention": 30,
                "desc": "Detected objects with bounding boxes",
            },
            "media.image.objects_hashed": {
                "retention": 30,
                "desc": "Perceptual hashes for object tracking",
            },
            "media.image.faces_detected": {
                "retention": 30,
                "desc": "Detected faces with landmarks",
            },
            "media.image.pose_detected": {
                "retention": 30,
                "desc": "Body and hand pose keypoints",
            },
            "media.image.gaze_detected": {"retention": 30, "desc": "Eye gaze vectors"},
            "media.image.analysis.moondream_results": {
                "retention": 30,
                "desc": "Image analysis (captions, gaze, objects)",
            },
            "media.image.analysis.minicpm_results": {
                "retention": 30,
                "desc": "Vision-language analysis results",
            },
            "media.video.analysis.yolo_results": {
                "retention": 30,
                "desc": "Object detection/tracking from video",
            },
            # Analysis Results
            "analysis.3d_reconstruction.dustr_results": {
                "retention": 30,
                "desc": "3D environment reconstruction",
            },
            "analysis.inferred_context.qwen_results": {
                "retention": 30,
                "desc": "High-level context inferences",
            },
            "analysis.inferred_context.mistral_results": {
                "retention": 30,
                "desc": "Mistral reasoning outputs",
            },
            "analysis.audio.emotion_results": {
                "retention": 30,
                "desc": "Speech emotion recognition",
            },
            "analysis.image.emotion_results": {
                "retention": 30,
                "desc": "Face emotion recognition",
            },
            # Task Results
            "task.url.processed.twitter_archived": {
                "retention": 90,
                "desc": "Archived X.com/Twitter content",
            },
            "task.url.processed.hackernews_archived": {
                "retention": 90,
                "desc": "Archived HackerNews content",
            },
            "task.url.processed.pdf_extracted": {
                "retention": 90,
                "desc": "Extracted PDF content/summaries",
            },
            # Location Processing
            "location.georegion.detected": {
                "retention": 30,
                "desc": "Detected presence in saved georegions (home/work/custom)",
            },
            "location.address.geocoded": {
                "retention": 30,
                "desc": "Geocoded addresses from GPS",
            },
            "location.business.identified": {
                "retention": 30,
                "desc": "Identified businesses at locations",
            },
            # Motion & Activity
            "device.sensor.accelerometer.windowed": {
                "retention": 7,
                "desc": "Windowed accelerometer features",
            },
            "motion.events.significant": {
                "retention": 30,
                "desc": "Significant motion events detected",
            },
            "motion.classification.activity": {
                "retention": 30,
                "desc": "Classified activities (walking/driving/etc)",
            },
            # Device State Processing
            "device.state.power.enriched": {
                "retention": 30,
                "desc": "Enriched power state with patterns",
            },
            "device.state.power.patterns": {
                "retention": 30,
                "desc": "Detected charging patterns",
            },
            "os.events.app_lifecycle.enriched": {
                "retention": 30,
                "desc": "Enriched app lifecycle events",
            },
            # External Data Processing
            "external.email.raw": {"retention": 90, "desc": "Raw fetched emails"},
            "external.email.parsed": {
                "retention": 90,
                "desc": "Parsed email structure",
            },
            "external.email.embedded": {
                "retention": 90,
                "desc": "Email text embeddings",
            },
            "external.calendar.raw": {"retention": 90, "desc": "Raw calendar events"},
            "external.calendar.enriched": {
                "retention": 90,
                "desc": "Enriched calendar data",
            },
            "external.calendar.embedded": {
                "retention": 90,
                "desc": "Calendar event embeddings",
            },
            "external.hackernews.liked": {"retention": 90, "desc": "Liked HN items"},
            "external.hackernews.content_fetched": {
                "retention": 90,
                "desc": "Fetched article content",
            },
            "external.hackernews.embedded": {
                "retention": 90,
                "desc": "HN content embeddings",
            },
            # Spatial Data
            "spatial.slam.mapping": {"retention": 30, "desc": "SLAM-generated 3D maps"},
            # Processing Error Topics
            "processing.errors.accelerometer": {
                "retention": 7,
                "desc": "Error messages from accelerometer processing",
            },
            "processing.errors.activity_classification": {
                "retention": 7,
                "desc": "Error messages from activity classification",
            },
            "processing.errors.app_lifecycle": {
                "retention": 7,
                "desc": "Error messages from app lifecycle processing",
            },
            "processing.errors.audio_classifier": {
                "retention": 7,
                "desc": "Error messages from audio classification",
            },
            "processing.errors.business_match": {
                "retention": 7,
                "desc": "Error messages from business matching",
            },
            "processing.errors.calendar_fetch": {
                "retention": 7,
                "desc": "Error messages from calendar fetching",
            },
            "processing.errors.email_fetch": {
                "retention": 7,
                "desc": "Error messages from email fetching",
            },
            "processing.errors.embedding": {
                "retention": 7,
                "desc": "Error messages from embedding generation",
            },
            "processing.errors.face_detection": {
                "retention": 7,
                "desc": "Error messages from face detection",
            },
            "processing.errors.geocoding": {
                "retention": 7,
                "desc": "Error messages from geocoding",
            },
            "processing.errors.georegion": {
                "retention": 7,
                "desc": "Error messages from georegion processing",
            },
            "processing.errors.hn_scrape": {
                "retention": 7,
                "desc": "Error messages from HackerNews scraping",
            },
            "processing.errors.image_preprocessing": {
                "retention": 7,
                "desc": "Error messages from image preprocessing",
            },
            "processing.errors.object_detection": {
                "retention": 7,
                "desc": "Error messages from object detection",
            },
            "processing.errors.ocr": {
                "retention": 7,
                "desc": "Error messages from OCR processing",
            },
            "processing.errors.stt": {
                "retention": 7,
                "desc": "Error messages from speech-to-text",
            },
            "processing.errors.vad": {
                "retention": 7,
                "desc": "Error messages from VAD processing",
            },
            "processing.errors.vision_preprocessing": {
                "retention": 7,
                "desc": "Error messages from vision preprocessing",
            },
        }

        # Insert topics
        inserted = 0
        for topic_name, config in topic_configs.items():
            parts = topic_name.split(".")
            category = parts[0]
            source = parts[1] if len(parts) > 1 else ""
            datatype = parts[2] if len(parts) > 2 else ""
            stage = parts[3] if len(parts) > 3 else None

            try:
                await self.conn.execute(
                    """
                    INSERT INTO kafka_topics (
                        topic_name, category, source, datatype, stage,
                        description, retention_days
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (topic_name) DO NOTHING
                """,
                    topic_name,
                    category,
                    source,
                    datatype,
                    stage,
                    config["desc"],
                    config["retention"],
                )
                inserted += 1
            except Exception as e:
                print(f"✗ Error inserting topic {topic_name}: {e}")

        print(f"✓ Imported {inserted} Kafka topics")

    async def import_json_schemas(self):
        """Import JSON schemas from shared/schemas directory."""
        print("\nImporting JSON schemas...")

        schemas_dir = self.base_path / "shared" / "schemas"
        if not schemas_dir.exists():
            print("✗ schemas directory not found")
            return

        inserted = 0
        for schema_file in schemas_dir.rglob("*.json"):
            relative_path = schema_file.relative_to(schemas_dir)

            # Extract topic name from path
            # e.g., device/audio/raw/v1.json -> device.audio.raw
            parts = relative_path.parts[:-1]  # Remove version file
            topic_name = ".".join(parts)

            # Extract version from filename
            version = schema_file.stem  # e.g., v1

            try:
                with open(schema_file, "r") as f:
                    schema_json = json.load(f)

                # Check if topic exists
                topic_exists = await self.conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM kafka_topics WHERE topic_name = $1)",
                    topic_name,
                )

                if topic_exists:
                    # Set current version (assuming v1 is current for now)
                    is_current = version == "v1"

                    await self.conn.execute(
                        """
                        INSERT INTO kafka_topic_schemas (
                            topic_name, version, schema_json, schema_path, is_current
                        ) VALUES ($1, $2, $3, $4, $5)
                        ON CONFLICT (topic_name, version) DO NOTHING
                    """,
                        topic_name,
                        version,
                        json.dumps(schema_json),
                        str(relative_path),
                        is_current,
                    )
                    inserted += 1

            except Exception as e:
                print(f"✗ Error importing schema {schema_file}: {e}")

        print(f"✓ Imported {inserted} JSON schemas")

    async def import_flow_definitions(self):
        """Import pipeline flow definitions from docs/flows/*.yaml."""
        print("\nImporting pipeline flow definitions...")

        flows_dir = self.base_path / "docs" / "flows"
        if not flows_dir.exists():
            print("✗ flows directory not found")
            return

        inserted_flows = 0
        inserted_stages = 0

        for flow_file in flows_dir.glob("*.yaml"):
            if flow_file.name.startswith("_"):
                continue  # Skip schema files

            try:
                with open(flow_file, "r") as f:
                    flow_data = yaml.safe_load(f)

                if not flow_data:
                    continue

                # Insert flow
                flow_name = flow_data.get("name")
                if not flow_name:
                    continue

                await self.conn.execute(
                    """
                    INSERT INTO pipeline_flows (
                        flow_name, description, priority,
                        expected_events_per_second, average_event_size_bytes, peak_multiplier
                    ) VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (flow_name) DO NOTHING
                """,
                    flow_name,
                    flow_data.get("description", ""),
                    flow_data.get("priority", "medium"),
                    flow_data.get("data_volume", {}).get("expected_events_per_second"),
                    flow_data.get("data_volume", {}).get("average_event_size_bytes"),
                    flow_data.get("data_volume", {}).get("peak_multiplier", 3),
                )
                inserted_flows += 1

                # Insert stages
                stages = flow_data.get("stages", [])
                for order, stage in enumerate(stages):
                    stage_id = await self.conn.fetchval(
                        """
                        INSERT INTO pipeline_stages (
                            flow_name, stage_name, stage_order,
                            service_name, service_image, replicas,
                            configuration, processing_timeout_seconds,
                            retry_max_attempts, retry_backoff_seconds,
                            sla_seconds, error_rate_threshold
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                        ON CONFLICT (flow_name, stage_name) DO NOTHING
                        RETURNING id
                    """,
                        flow_name,
                        stage.get("name"),
                        order,
                        stage.get("service", {}).get("name"),
                        stage.get("service", {}).get("image"),
                        stage.get("service", {}).get("replicas", 1),
                        json.dumps(stage.get("configuration", {})),
                        stage.get("processing", {}).get("timeout_seconds"),
                        stage.get("processing", {})
                        .get("retry_policy", {})
                        .get("max_retries", 3),
                        stage.get("processing", {})
                        .get("retry_policy", {})
                        .get("backoff_seconds", 1),
                        stage.get("monitoring", {}).get("sla_seconds"),
                        stage.get("monitoring", {}).get("alert_on_error_rate"),
                    )

                    if stage_id:
                        inserted_stages += 1

                        # Insert topic relationships
                        for topic in stage.get("input_topics", []):
                            await self.conn.execute(
                                """
                                INSERT INTO pipeline_stage_topics (stage_id, topic_name, topic_role)
                                VALUES ($1, $2, 'input')
                                ON CONFLICT DO NOTHING
                            """,
                                stage_id,
                                topic,
                            )

                        for topic in stage.get("output_topics", []):
                            await self.conn.execute(
                                """
                                INSERT INTO pipeline_stage_topics (stage_id, topic_name, topic_role)
                                VALUES ($1, $2, 'output')
                                ON CONFLICT DO NOTHING
                            """,
                                stage_id,
                                topic,
                            )

                        error_topic = stage.get("error_topic")
                        if error_topic:
                            await self.conn.execute(
                                """
                                INSERT INTO pipeline_stage_topics (stage_id, topic_name, topic_role)
                                VALUES ($1, $2, 'error')
                                ON CONFLICT DO NOTHING
                            """,
                                stage_id,
                                error_topic,
                            )

            except Exception as e:
                print(f"✗ Error importing flow {flow_file}: {e}")

        print(f"✓ Imported {inserted_flows} flows with {inserted_stages} stages")

    async def import_topic_mappings(self):
        """Import topic mappings from kafka-to-db-consumer configuration."""
        print("\nImporting kafka-to-db consumer mappings...")

        mappings_file = (
            self.base_path
            / "services"
            / "kafka-to-db-consumer"
            / "config"
            / "topic_mappings.yml"
        )
        if not mappings_file.exists():
            print("✗ topic_mappings.yml not found")
            return

        with open(mappings_file, "r") as f:
            mappings = yaml.safe_load(f)

        topics = mappings.get("topics", {})
        inserted_configs = 0
        inserted_mappings = 0

        for topic_name, config in topics.items():
            # Skip if topic doesn't exist
            topic_exists = await self.conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM kafka_topics WHERE topic_name = $1)",
                topic_name,
            )
            if not topic_exists:
                continue

            # Insert table config
            table_name = config.get("table")
            if table_name:
                upsert_key = config.get(
                    "upsert_key",
                    mappings.get("defaults", {}).get(
                        "upsert_key", "device_id, timestamp"
                    ),
                )
                conflict_strategy = config.get(
                    "conflict_strategy",
                    mappings.get("defaults", {}).get("conflict_strategy", "ignore"),
                )

                await self.conn.execute(
                    """
                    INSERT INTO topic_table_configs (topic_name, table_name, upsert_key, conflict_strategy)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (topic_name) DO NOTHING
                """,
                    topic_name,
                    table_name,
                    upsert_key,
                    conflict_strategy,
                )
                inserted_configs += 1

                # Insert field mappings
                field_mappings = config.get("field_mappings", {})
                data_types = config.get("data_types", {})
                transforms = config.get("transforms", {})
                required_fields = config.get("required_fields", [])

                for source_path, target_column in field_mappings.items():
                    data_type = data_types.get(target_column)
                    transformation = transforms.get(target_column)
                    is_required = (
                        source_path in required_fields
                        or target_column in required_fields
                    )

                    await self.conn.execute(
                        """
                        INSERT INTO topic_field_mappings (
                            topic_name, table_name, source_field_path, target_column,
                            data_type, transformation, is_required
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                        ON CONFLICT (topic_name, source_field_path, target_column) DO NOTHING
                    """,
                        topic_name,
                        table_name,
                        source_path,
                        target_column,
                        data_type,
                        transformation,
                        is_required,
                    )
                    inserted_mappings += 1

        print(
            f"✓ Imported {inserted_configs} table configs with {inserted_mappings} field mappings"
        )

    async def run_import(self, skip_confirmation=False):
        """Run the complete import process."""
        try:
            await self.connect()

            # Ask for confirmation before clearing data
            if not skip_confirmation:
                response = input(
                    "\nThis will clear existing schema management data. Continue? (y/N): "
                )
                if response.lower() != "y":
                    print("Import cancelled.")
                    return

            await self.clear_existing_data()
            await self.import_kafka_topics_from_claude_md()
            await self.import_json_schemas()
            await self.import_flow_definitions()
            await self.import_topic_mappings()

            # Print summary
            print("\n=== Import Summary ===")

            topic_count = await self.conn.fetchval("SELECT COUNT(*) FROM kafka_topics")
            schema_count = await self.conn.fetchval(
                "SELECT COUNT(*) FROM kafka_topic_schemas"
            )
            flow_count = await self.conn.fetchval("SELECT COUNT(*) FROM pipeline_flows")
            stage_count = await self.conn.fetchval(
                "SELECT COUNT(*) FROM pipeline_stages"
            )

            print(f"Topics: {topic_count}")
            print(f"Schemas: {schema_count}")
            print(f"Flows: {flow_count}")
            print(f"Stages: {stage_count}")

            print("\n✓ Import completed successfully!")

        except Exception as e:
            print(f"\n✗ Import failed: {e}")
            raise
        finally:
            await self.disconnect()


async def main():
    # Get database URL from environment or use default
    database_url = os.getenv(
        "DATABASE_URL", "postgresql://loom:loom@localhost:5432/loom"
    )

    # Check for --yes flag
    skip_confirmation = "--yes" in sys.argv or "-y" in sys.argv

    importer = KafkaSchemaImporter(database_url)
    await importer.run_import(skip_confirmation=skip_confirmation)


if __name__ == "__main__":
    asyncio.run(main())
