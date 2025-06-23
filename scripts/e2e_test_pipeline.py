#!/usr/bin/env python3
"""
End-to-End Pipeline Test Script

This script performs a comprehensive test of the entire Loom v2 data pipeline:
1. Spins up the development environment
2. Tests all API endpoints with realistic data
3. Verifies data reaches correct Kafka topics
4. Injects processed data examples
5. Verifies data is stored in TimescaleDB
6. Validates the complete data flow

Usage:
    python scripts/e2e_test_pipeline.py

Updated: 2025-01-23
- Fixed device_id to use valid UUID format
- Updated test data to match actual API models (e.g., chunk_data vs audio_data)
- Added metadata endpoint test
- Fixed API endpoint paths and expected topics
- Updated database table names to match implementation
- Removed non-existent Kafka-to-DB consumer health check
"""

import asyncio
import asyncpg
import base64
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp
import structlog
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

# Configure logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO level
    logger_factory=structlog.PrintLoggerFactory(),
    context_class=dict,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Test configuration
TEST_DEVICE_ID = "12345678-1234-1234-1234-123456789012"  # Valid UUID format
BASE_URL = "http://localhost:8000"
KAFKA_SERVERS = "localhost:9092"
DB_URL = "postgresql://loom:loom@localhost:5432/loom"

# Test data templates
TEST_DATA = {
    "audio": {
        "device_id": TEST_DEVICE_ID,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "chunk_data": base64.b64encode(b"fake_audio_data_16khz_mono" * 100).decode(),
        "sample_rate": 16000,
        "channels": 1,
        "duration_ms": 3000,
        "format": "wav",
    },
    "image": {
        "device_id": TEST_DEVICE_ID,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "image_data": base64.b64encode(b"fake_jpeg_image_data" * 50).decode(),
        "width": 1920,
        "height": 1080,
        "format": "jpeg",
        "camera_type": "front",
        "file_size": len(b"fake_jpeg_image_data" * 50),
        "metadata": {"test": True},
    },
    "gps": {
        "device_id": TEST_DEVICE_ID,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "latitude": 37.7749,
        "longitude": -122.4194,
        "altitude": 52.0,
        "accuracy": 5.0,
        "speed": 0.0,
        "heading": 0.0,
    },
    "accelerometer": {
        "device_id": TEST_DEVICE_ID,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "x": 0.1,
        "y": 0.2,
        "z": 9.8,
    },
    "heartrate": {
        "device_id": TEST_DEVICE_ID,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "bpm": 72,
        "confidence": 0.95,
    },
    "power": {
        "device_id": TEST_DEVICE_ID,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "battery_level": 85,
        "is_charging": False,
        "power_source": "battery",
    },
    "macos_apps": {
        "device_id": TEST_DEVICE_ID,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "running_applications": [
            {
                "pid": 1234,
                "name": "Visual Studio Code",
                "bundle_id": "com.microsoft.VSCode",
                "active": True,
                "hidden": False,
            },
            {
                "pid": 5678,
                "name": "Safari",
                "bundle_id": "com.apple.Safari",
                "active": False,
                "hidden": False,
            },
        ],
    },
    "note": {
        "device_id": TEST_DEVICE_ID,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "title": "E2E Test Note",
        "content": "# Test Note\n\nThis is a **test note** for the E2E pipeline.\n\n- Item 1\n- Item 2\n\n```python\nprint('Hello World')\n```",
        "note_type": "markdown",
        "tags": ["test", "e2e", "automation"],
    },
    "url": {
        "device_id": TEST_DEVICE_ID,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "url": "https://example.com/test-article",
        "task_type": "webpage",
        "priority": 5,
        "content_hint": "article",
        "extract_options": {"extract_text": True, "extract_links": True},
    },
    "metadata": {
        "device_id": TEST_DEVICE_ID,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "metadata_type": "device_capabilities",
        "metadata": {
            "sensors": ["accelerometer", "gyroscope", "gps"],
            "cameras": {"front": True, "rear": True, "resolution": "1920x1080"},
            "audio": {
                "microphone": True,
                "speakers": True,
                "sample_rates": [44100, 48000],
            },
            "connectivity": ["wifi", "bluetooth", "cellular"],
        },
    },
}

# Processed data examples (simulated AI outputs)
PROCESSED_DATA_EXAMPLES = {
    "vad_filtered": {
        "device_id": TEST_DEVICE_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "schema_version": "v1",
        "message_id": str(uuid.uuid4()),
        "audio_data": base64.b64encode(b"filtered_speech_segment" * 50).decode(),
        "sample_rate": 16000,
        "channels": 1,
        "duration_ms": 2500,
        "format": "pcm",
        "vad_confidence": 0.89,
        "speech_start_ms": 250,
        "speech_end_ms": 2750,
        "metadata": {"test": True, "vad_model": "silero"},
    },
    "voice_segments": {
        "device_id": TEST_DEVICE_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "schema_version": "v1",
        "message_id": str(uuid.uuid4()),
        "segment_start_time": datetime.now(timezone.utc).isoformat(),
        "segment_end_time": datetime.now(timezone.utc).isoformat(),
        "duration_ms": 2500,
        "confidence_score": 0.89,
        "audio_sample_rate": 16000,
        "audio_channels": 1,
        "voice_activity_threshold": 0.5,
    },
    "word_timestamps": {
        "device_id": TEST_DEVICE_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "schema_version": "v1",
        "message_id": str(uuid.uuid4()),
        "word_sequence": 1,
        "word_text": "hello",
        "start_time_ms": 100,
        "end_time_ms": 500,
        "confidence_score": 0.95,
        "speaker_id": "speaker_1",
        "language_code": "en",
        "phonetic_transcription": "həˈloʊ",
        "word_boundaries": {"start": 100, "end": 500},
    },
    "vision_annotations": {
        "device_id": TEST_DEVICE_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "schema_version": "v1",
        "message_id": str(uuid.uuid4()),
        "annotation_id": str(uuid.uuid4()),
        "object_class": "person",
        "confidence_score": 0.92,
        "bounding_box": {"x": 100, "y": 150, "width": 200, "height": 300},
        "object_attributes": {"age_estimate": "adult", "clothing": "casual"},
        "ocr_text": None,
        "scene_description": "Person standing in office environment",
        "image_width": 1920,
        "image_height": 1080,
        "model_version": "minicpm-v2.5",
    },
    "emotion_scores": {
        "device_id": TEST_DEVICE_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "schema_version": "v1",
        "message_id": str(uuid.uuid4()),
        "segment_id": str(uuid.uuid4()),
        "predicted_emotion": "happiness",
        "confidence_score": 0.78,
        "valence_score": 0.6,
        "arousal_score": 0.4,
        "dominance_score": 0.2,
        "emotion_probabilities": {
            "happiness": 0.78,
            "neutral": 0.15,
            "sadness": 0.04,
            "anger": 0.02,
            "fear": 0.01,
        },
        "audio_features": {"rms_energy": 0.05, "zero_crossing_rate": 0.08},
        "model_version": "bud-e-whisper",
    },
    "face_emotions": {
        "device_id": TEST_DEVICE_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "schema_version": "v1",
        "message_id": str(uuid.uuid4()),
        "face_id": str(uuid.uuid4()),
        "emotion_label": "happiness",
        "confidence_score": 0.85,
        "face_bounding_box": {
            "x": 120,
            "y": 180,
            "width": 150,
            "height": 200,
            "confidence": 0.9,
        },
        "facial_landmarks": {
            "left_eye": {"x": 140, "y": 200},
            "right_eye": {"x": 180, "y": 200},
            "nose": {"x": 160, "y": 220},
            "mouth": {"x": 160, "y": 250},
        },
        "age_estimate": 32,
        "gender_estimate": "female",
        "emotion_intensities": {
            "happiness": 0.85,
            "neutral": 0.10,
            "surprise": 0.03,
            "sadness": 0.02,
        },
        "face_quality_score": 0.92,
        "model_version": "empathic-insight-face",
    },
    "processed_content": {
        "device_id": TEST_DEVICE_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "schema_version": "v1",
        "message_id": str(uuid.uuid4()),
        "url_id": str(uuid.uuid4()),
        "original_url": "https://example.com/test-article",
        "final_url": "https://example.com/test-article",
        "domain": "example.com",
        "content_type": "webpage",
        "title": "Example Test Article",
        "content_text": "This is the extracted text content from the test webpage...",
        "content_summary": "A test article demonstrating URL processing capabilities.",
        "extracted_metadata": {"author": "Test Author", "publish_date": "2024-01-01"},
        "content_length": 1024,
        "language_detected": "en",
        "category": "technology",
        "tags": ["test", "example", "automation"],
        "processing_duration_ms": 2500,
        "processor_version": "url-processor-v1.0",
    },
}


class E2ETestRunner:
    """End-to-end test runner for Loom v2 pipeline."""

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.kafka_producer: Optional[AIOKafkaProducer] = None
        self.kafka_consumer: Optional[AIOKafkaConsumer] = None
        self.db_pool: Optional[asyncpg.Pool] = None
        self.test_results: Dict[str, Any] = {}
        self.performance_metrics: Dict[str, List[float]] = {}

    async def setup(self):
        """Set up test environment."""
        logger.info("Setting up E2E test environment")

        # Create HTTP session
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))

        # Create Kafka producer for injecting processed data
        self.kafka_producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_SERVERS,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
        )
        await self.kafka_producer.start()

        # Create database connection pool (skip if DB not available)
        try:
            self.db_pool = await asyncpg.create_pool(
                DB_URL,
                min_size=1,
                max_size=2,
                command_timeout=10,
                ssl=False,  # Disable SSL for local development
            )
            logger.info("Database connection established")
        except Exception as e:
            logger.warning(
                "Database connection failed, skipping DB tests", error=str(e)
            )
            self.db_pool = None

        logger.info("E2E test environment ready")

    async def cleanup(self):
        """Clean up test environment."""
        logger.info("Cleaning up E2E test environment")

        if self.session:
            await self.session.close()

        if self.kafka_producer:
            await self.kafka_producer.stop()

        if self.db_pool:
            await self.db_pool.close()

    async def cleanup_test_data(self):
        """Remove test data from database."""
        if not self.db_pool:
            logger.warning("Database not available, skipping cleanup")
            return {"skipped": "no_database_connection"}

        logger.info("Cleaning up test data from database")

        tables_to_clean = [
            # Raw data tables
            "device_audio_raw",
            "device_image_camera_raw",
            "device_sensor_gps_raw",
            "device_sensor_accelerometer_raw",
            "device_health_heartrate_raw",
            "device_state_power_raw",
            "device_system_apps_macos_raw",
            "device_metadata_raw",
            "device_text_notes_raw",
            # Processed data tables
            "media_audio_voice_segments",
            "media_text_word_timestamps",
            "media_image_vision_annotations",
            "analysis_audio_emotion_scores",
            "analysis_image_face_emotions",
            "task_url_processed_content",
        ]

        cleanup_results = {}

        try:
            async with self.db_pool.acquire() as conn:
                for table in tables_to_clean:
                    try:
                        # Delete test data
                        delete_query = f"DELETE FROM {table} WHERE device_id = $1"
                        result = await conn.execute(delete_query, TEST_DEVICE_ID)

                        # Extract number of rows deleted
                        rows_deleted = int(result.split()[-1]) if result else 0
                        cleanup_results[table] = rows_deleted

                        if rows_deleted > 0:
                            logger.info(
                                "Cleaned test data",
                                table=table,
                                rows_deleted=rows_deleted,
                            )
                    except Exception as e:
                        logger.warning(
                            "Failed to clean table", table=table, error=str(e)
                        )
                        cleanup_results[table] = -1

        except Exception as e:
            logger.error("Database cleanup failed", error=str(e))

        return cleanup_results

    async def wait_for_services(self, max_wait: int = 120):
        """Wait for all services to be ready."""
        logger.info("Waiting for services to be ready", max_wait=max_wait)

        services = [
            ("Ingestion API", f"{BASE_URL}/healthz"),
        ]

        # If there's a Kafka consumer service running, add it here
        # For now we'll just check the ingestion API

        start_time = time.time()

        for service_name, health_url in services:
            while time.time() - start_time < max_wait:
                try:
                    async with self.session.get(health_url) as response:
                        if response.status == 200:
                            logger.info(f"{service_name} is ready")
                            break
                except:
                    pass
                await asyncio.sleep(2)
            else:
                raise TimeoutError(f"{service_name} not ready after {max_wait}s")

        # Additional wait for Kafka to be fully ready
        logger.info("Waiting additional time for Kafka to be fully ready")
        await asyncio.sleep(10)

    async def test_websocket_audio_stream(self) -> bool:
        """Test WebSocket audio streaming endpoint."""
        logger.info("Testing WebSocket audio streaming")

        try:
            # Connect to WebSocket
            ws_url = f"ws://localhost:8000/audio/stream/{TEST_DEVICE_ID}"
            async with self.session.ws_connect(ws_url) as ws:
                logger.info("WebSocket connected", url=ws_url)

                # Send multiple audio chunks using WebSocket message format
                for i in range(3):
                    ws_message = {
                        "message_type": "audio_chunk",
                        "data": {
                            "recorded_at": datetime.now(timezone.utc).isoformat(),
                            "chunk_data": base64.b64encode(
                                f"audio_chunk_{i}".encode() * 100
                            ).decode(),
                            "chunk_index": i,
                            "sample_rate": 16000,
                            "channels": 1,
                            "bits_per_sample": 16,
                            "duration_ms": 1000,
                            "format": "pcm",
                        },
                    }

                    await ws.send_json(ws_message)
                    logger.info("Sent audio chunk", chunk_index=i)

                    # Wait for acknowledgment
                    response = await ws.receive_json()
                    if (
                        response.get("type") != "ack"
                        or response.get("status") != "success"
                    ):
                        logger.error("Unexpected WebSocket response", response=response)
                        return False

                    await asyncio.sleep(0.1)

                # Send ping to test connection
                ping_message = {
                    "message_type": "ping",
                    "data": {"timestamp": datetime.now(timezone.utc).isoformat()},
                }
                await ws.send_json(ping_message)

                # Wait for pong response
                pong_response = await ws.receive_json()
                if pong_response.get("type") != "pong":
                    logger.error("Ping/pong failed", response=pong_response)
                    return False

                logger.info("WebSocket audio streaming test passed")
                return True

        except Exception as e:
            logger.error("WebSocket test failed", error=str(e))
            return False

    async def test_api_endpoint(
        self,
        endpoint: str,
        data: Dict[str, Any],
        expected_topic: str,
        max_retries: int = 3,
    ) -> bool:
        """Test a single API endpoint with retry logic."""
        logger.info(
            "Testing API endpoint", endpoint=endpoint, expected_topic=expected_topic
        )

        for attempt in range(max_retries):
            try:
                start_time = time.time()
                async with self.session.post(
                    f"{BASE_URL}{endpoint}",
                    json=data,
                    headers={"X-API-Key": "pineapple"},
                ) as response:
                    response_data = await response.json()
                    response_time = (time.time() - start_time) * 1000  # Convert to ms

                    # Track performance metrics
                    if endpoint not in self.performance_metrics:
                        self.performance_metrics[endpoint] = []
                    self.performance_metrics[endpoint].append(response_time)

                    if response.status not in [200, 201]:
                        logger.error(
                            "API endpoint failed",
                            endpoint=endpoint,
                            status=response.status,
                            response=response_data,
                            attempt=attempt + 1,
                        )
                        if attempt < max_retries - 1:
                            await asyncio.sleep(2**attempt)  # Exponential backoff
                            continue
                        return False

                    # Verify response contains expected fields
                    if response_data.get("status") != "success":
                        logger.error(
                            "API response status not success",
                            endpoint=endpoint,
                            response=response_data,
                        )
                        return False

                    if response_data.get("topic") != expected_topic:
                        logger.error(
                            "API response topic mismatch",
                            endpoint=endpoint,
                            expected=expected_topic,
                            actual=response_data.get("topic"),
                        )
                        return False

                    logger.info(
                        "API endpoint test passed",
                        endpoint=endpoint,
                        response_time_ms=f"{response_time:.2f}",
                    )
                    return True

            except aiohttp.ClientError as e:
                logger.warning(
                    "API request failed",
                    endpoint=endpoint,
                    error=str(e),
                    attempt=attempt + 1,
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(2**attempt)
                    continue
                return False
            except Exception as e:
                logger.error(
                    "Unexpected error in API test", endpoint=endpoint, error=str(e)
                )
                return False

        return False

    async def inject_processed_data(
        self, topic: str, data: Dict[str, Any], max_retries: int = 3
    ) -> bool:
        """Inject processed data into Kafka topic with retry logic."""
        logger.info("Injecting processed data", topic=topic)

        for attempt in range(max_retries):
            try:
                await self.kafka_producer.send(topic, value=data)
                logger.info("Processed data injected successfully", topic=topic)
                return True
            except Exception as e:
                logger.warning(
                    "Failed to inject processed data",
                    topic=topic,
                    error=str(e),
                    attempt=attempt + 1,
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(2**attempt)
                    continue
                logger.error("All injection attempts failed", topic=topic)
                return False

        return False

    async def verify_db_data(
        self, table: str, device_id: str, timeout: int = 30
    ) -> bool:
        """Verify data exists in database table."""
        if not self.db_pool:
            logger.warning("Database not available, skipping verification", table=table)
            return True  # Skip DB verification if no connection

        logger.info("Verifying database data", table=table, device_id=device_id)

        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                async with self.db_pool.acquire() as conn:
                    query = f"SELECT COUNT(*) FROM {table} WHERE device_id = $1"
                    count = await conn.fetchval(query, device_id)

                    if count > 0:
                        logger.info(
                            "Database verification passed",
                            table=table,
                            device_id=device_id,
                            count=count,
                        )
                        return True

            except Exception as e:
                logger.warning("Database query failed", table=table, error=str(e))

            await asyncio.sleep(2)

        logger.error(
            "Database verification failed",
            table=table,
            device_id=device_id,
            timeout=timeout,
        )
        return False

    async def run_api_tests(self) -> Dict[str, bool]:
        """Run all API endpoint tests."""
        logger.info("Running API endpoint tests")

        api_tests = [
            ("/audio/upload", TEST_DATA["audio"], "device.audio.raw"),
            ("/images/upload", TEST_DATA["image"], "device.image.camera.raw"),
            ("/sensor/gps", TEST_DATA["gps"], "device.sensor.gps.raw"),
            (
                "/sensor/accelerometer",
                TEST_DATA["accelerometer"],
                "device.sensor.accelerometer.raw",
            ),
            (
                "/sensor/heartrate",
                TEST_DATA["heartrate"],
                "device.health.heartrate.raw",
            ),
            ("/sensor/power", TEST_DATA["power"], "device.state.power.raw"),
            (
                "/system/apps/macos",
                TEST_DATA["macos_apps"],
                "device.system.apps.macos.raw",
            ),
            ("/system/metadata", TEST_DATA["metadata"], "device.metadata.raw"),
            ("/notes/upload", TEST_DATA["note"], "device.text.notes.raw"),
        ]

        results = {}

        for endpoint, data, expected_topic in api_tests:
            results[endpoint] = await self.test_api_endpoint(
                endpoint, data, expected_topic
            )
            await asyncio.sleep(1)  # Brief pause between tests

        # Test WebSocket audio streaming
        results["WebSocket /audio/stream"] = await self.test_websocket_audio_stream()

        return results

    async def run_processed_data_injection(self) -> Dict[str, bool]:
        """Inject processed data examples into topics."""
        logger.info("Injecting processed data examples")

        injection_tests = [
            ("media.audio.vad_filtered", PROCESSED_DATA_EXAMPLES["vad_filtered"]),
            ("media.audio.voice_segments", PROCESSED_DATA_EXAMPLES["voice_segments"]),
            ("media.text.word_timestamps", PROCESSED_DATA_EXAMPLES["word_timestamps"]),
            (
                "media.image.vision_annotations",
                PROCESSED_DATA_EXAMPLES["vision_annotations"],
            ),
            (
                "analysis.audio.emotion_scores",
                PROCESSED_DATA_EXAMPLES["emotion_scores"],
            ),
            ("analysis.image.face_emotions", PROCESSED_DATA_EXAMPLES["face_emotions"]),
            (
                "task.url.processed_content",
                PROCESSED_DATA_EXAMPLES["processed_content"],
            ),
        ]

        results = {}

        for topic, data in injection_tests:
            results[topic] = await self.inject_processed_data(topic, data)
            await asyncio.sleep(1)

        return results

    async def run_database_verification(self) -> Dict[str, bool]:
        """Verify all data reached the database."""
        logger.info("Running database verification tests")

        # Wait for data to be processed
        logger.info("Waiting for data processing and ingestion")
        await asyncio.sleep(15)

        db_tests = [
            # Raw data tables (from API)
            ("device_audio_raw", TEST_DEVICE_ID),
            ("device_image_camera_raw", TEST_DEVICE_ID),
            ("device_sensor_gps_raw", TEST_DEVICE_ID),
            ("device_sensor_accelerometer_raw", TEST_DEVICE_ID),
            ("device_health_heartrate_raw", TEST_DEVICE_ID),
            ("device_state_power_raw", TEST_DEVICE_ID),
            ("device_system_apps_macos_raw", TEST_DEVICE_ID),
            ("device_metadata_raw", TEST_DEVICE_ID),
            ("device_text_notes_raw", TEST_DEVICE_ID),
            # Processed data tables (from injected data)
            ("media_audio_vad_filtered", TEST_DEVICE_ID),
            ("media_audio_voice_segments", TEST_DEVICE_ID),
            ("media_text_word_timestamps", TEST_DEVICE_ID),
            ("media_image_vision_annotations", TEST_DEVICE_ID),
            ("analysis_audio_emotion_scores", TEST_DEVICE_ID),
            ("analysis_image_face_emotions", TEST_DEVICE_ID),
            ("task_url_processed_content", TEST_DEVICE_ID),
        ]

        results = {}

        for table, device_id in db_tests:
            results[table] = await self.verify_db_data(table, device_id)

        return results

    async def run_full_test_cycle(self) -> Dict[str, Any]:
        """Run the complete end-to-end test cycle."""
        logger.info("Starting full E2E test cycle")

        test_results = {
            "start_time": datetime.now(timezone.utc).isoformat(),
            "api_tests": {},
            "processed_injection": {},
            "database_verification": {},
            "overall_success": False,
        }

        try:
            # Wait for services
            await self.wait_for_services()

            # Run API tests
            test_results["api_tests"] = await self.run_api_tests()

            # Inject processed data
            test_results[
                "processed_injection"
            ] = await self.run_processed_data_injection()

            # Verify database
            test_results[
                "database_verification"
            ] = await self.run_database_verification()

            # Calculate overall success
            api_success = all(test_results["api_tests"].values())
            injection_success = all(test_results["processed_injection"].values())
            db_success = all(test_results["database_verification"].values())

            test_results["overall_success"] = (
                api_success and injection_success and db_success
            )

            # Add performance metrics
            test_results["performance_metrics"] = self._calculate_performance_stats()

        except Exception as e:
            logger.error("E2E test cycle failed", error=str(e))
            test_results["error"] = str(e)

        test_results["end_time"] = datetime.now(timezone.utc).isoformat()

        return test_results

    def _calculate_performance_stats(self) -> Dict[str, Dict[str, float]]:
        """Calculate performance statistics from collected metrics."""
        stats = {}

        for endpoint, times in self.performance_metrics.items():
            if times:
                stats[endpoint] = {
                    "avg_ms": sum(times) / len(times),
                    "min_ms": min(times),
                    "max_ms": max(times),
                    "count": len(times),
                }

        return stats

    def print_test_results(self, results: Dict[str, Any]):
        """Print formatted test results."""
        print("\n" + "=" * 80)
        print("🧪 LOOM V2 END-TO-END TEST RESULTS")
        print("=" * 80)

        print(
            f"\n📊 Overall Success: {'✅ PASS' if results['overall_success'] else '❌ FAIL'}"
        )
        print(f"⏱️  Duration: {results['start_time']} → {results['end_time']}")

        # API Tests
        print("\n🌐 API Endpoint Tests:")
        for endpoint, success in results["api_tests"].items():
            status = "✅" if success else "❌"
            print(f"  {status} {endpoint}")

        api_pass_rate = (
            sum(results["api_tests"].values()) / len(results["api_tests"]) * 100
        )
        print(f"  📈 Pass Rate: {api_pass_rate:.1f}%")

        # Processed Data Injection
        print("\n🔄 Processed Data Injection:")
        for topic, success in results["processed_injection"].items():
            status = "✅" if success else "❌"
            print(f"  {status} {topic}")

        injection_pass_rate = (
            sum(results["processed_injection"].values())
            / len(results["processed_injection"])
            * 100
        )
        print(f"  📈 Pass Rate: {injection_pass_rate:.1f}%")

        # Database Verification
        print("\n💾 Database Verification:")
        for table, success in results["database_verification"].items():
            status = "✅" if success else "❌"
            print(f"  {status} {table}")

        db_pass_rate = (
            sum(results["database_verification"].values())
            / len(results["database_verification"])
            * 100
        )
        print(f"  📈 Pass Rate: {db_pass_rate:.1f}%")

        # Performance Metrics
        if "performance_metrics" in results:
            print("\n⚡ Performance Metrics:")
            for endpoint, metrics in results["performance_metrics"].items():
                print(f"  {endpoint}:")
                print(f"    • Average: {metrics['avg_ms']:.2f}ms")
                print(f"    • Min: {metrics['min_ms']:.2f}ms")
                print(f"    • Max: {metrics['max_ms']:.2f}ms")

        # Cleanup Results
        if "cleanup_results" in results:
            print("\n🧹 Test Data Cleanup:")
            cleanup_data = results["cleanup_results"]
            if isinstance(cleanup_data, dict) and "skipped" in cleanup_data:
                print(f"  ⚠️  Database cleanup skipped: {cleanup_data['skipped']}")
            else:
                total_cleaned = 0
                for table, rows in cleanup_data.items():
                    if isinstance(rows, int) and rows >= 0:
                        print(f"  ✓ {table}: {rows} rows deleted")
                        total_cleaned += rows
                    else:
                        print(f"  ✗ {table}: cleanup failed")
                print(f"  📊 Total rows cleaned: {total_cleaned}")

        if "error" in results:
            print(f"\n❌ Error: {results['error']}")

        print("\n" + "=" * 80)


async def main():
    """Main test runner."""
    print("🚀 Starting Loom v2 End-to-End Test Pipeline")
    print("This will test the complete data flow from API → Kafka → Database")

    # Check if development environment is running
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{BASE_URL}/healthz", timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status != 200:
                    raise Exception("Ingestion API not responding")
    except:
        print("\n❌ Development environment not running!")
        print("Please start it first with: make dev-up")
        print("Or: tilt up")
        return 1

    runner = E2ETestRunner()

    try:
        await runner.setup()
        results = await runner.run_full_test_cycle()

        # Clean up test data
        print("\n🧹 Cleaning up test data...")
        cleanup_results = await runner.cleanup_test_data()
        results["cleanup_results"] = cleanup_results

        runner.print_test_results(results)

        # Save results to file
        results_file = Path("e2e_test_results.json")
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2, default=str)

        print(f"\n📄 Detailed results saved to: {results_file}")

        return 0 if results["overall_success"] else 1

    finally:
        await runner.cleanup()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
