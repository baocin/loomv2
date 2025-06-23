#!/usr/bin/env python3
"""End-to-end pipeline testing for Loom v2."""

import asyncio
import base64
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Dict, Any

import aiohttp
import aiokafka
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
INGESTION_API_URL = os.getenv("LOOM_INGESTION_API_URL", "http://localhost:8000")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("LOOM_KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

# Test data
SAMPLE_AUDIO_BASE64 = base64.b64encode(b"fake_audio_data" * 100).decode()
SAMPLE_IMAGE_BASE64 = base64.b64encode(b"fake_image_data" * 100).decode()

SAMPLE_PAYLOADS = {
    "audio": {
        "device_id": "test-device-001",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "chunk_number": 1,
        "audio_data": SAMPLE_AUDIO_BASE64,
        "format": "wav",
        "sample_rate": 16000,
        "channels": 1,
        "duration_ms": 1000,
        "metadata": {"test": True}
    },
    "gps": {
        "device_id": "test-device-001",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "latitude": 37.7749,
        "longitude": -122.4194,
        "altitude": 10.0,
        "accuracy": 5.0,
        "metadata": {"test": True}
    },
    "image": {
        "device_id": "test-device-001",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "image_data": SAMPLE_IMAGE_BASE64,
        "format": "png",
        "width": 640,
        "height": 480,
        "metadata": {"test": True}
    },
    "note": {
        "device_id": "test-device-001",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "content": "This is a test note for end-to-end pipeline testing.",
        "metadata": {"test": True}
    }
}


class PipelineTester:
    """End-to-end pipeline tester."""
    
    def __init__(self):
        self.session = None
        self.producer = None
        self.consumer = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        self.producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode()
        )
        await self.producer.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.consumer:
            await self.consumer.stop()
        if self.producer:
            await self.producer.stop()
        if self.session:
            await self.session.close()
    
    async def test_api_health(self) -> bool:
        """Test if the ingestion API is healthy."""
        try:
            async with self.session.get(f"{INGESTION_API_URL}/healthz") as resp:
                if resp.status == 200:
                    logger.info("✅ Ingestion API health check passed")
                    return True
                else:
                    logger.error(f"❌ Ingestion API health check failed: {resp.status}")
                    return False
        except Exception as e:
            logger.error(f"❌ Failed to connect to ingestion API: {e}")
            return False
    
    async def test_kafka_connectivity(self) -> bool:
        """Test Kafka connectivity."""
        try:
            # Test producer
            await self.producer.send_and_wait(
                "test.connectivity",
                {"timestamp": datetime.now(timezone.utc).isoformat(), "test": True}
            )
            logger.info("✅ Kafka connectivity test passed")
            return True
        except Exception as e:
            logger.error(f"❌ Kafka connectivity test failed: {e}")
            return False
    
    async def test_audio_ingestion(self) -> bool:
        """Test audio data ingestion."""
        try:
            async with self.session.post(
                f"{INGESTION_API_URL}/audio/upload",
                json=SAMPLE_PAYLOADS["audio"]
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    logger.info(f"✅ Audio ingestion successful: {result['message']}")
                    return True
                else:
                    error = await resp.text()
                    logger.error(f"❌ Audio ingestion failed: {resp.status} - {error}")
                    return False
        except Exception as e:
            logger.error(f"❌ Audio ingestion test failed: {e}")
            return False
    
    async def test_sensor_ingestion(self) -> bool:
        """Test sensor data ingestion."""
        try:
            async with self.session.post(
                f"{INGESTION_API_URL}/sensor/gps",
                json=SAMPLE_PAYLOADS["gps"]
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    logger.info(f"✅ GPS sensor ingestion successful: {result['message']}")
                    return True
                else:
                    error = await resp.text()
                    logger.error(f"❌ GPS sensor ingestion failed: {resp.status} - {error}")
                    return False
        except Exception as e:
            logger.error(f"❌ Sensor ingestion test failed: {e}")
            return False
    
    async def test_image_ingestion(self) -> bool:
        """Test image data ingestion."""
        try:
            async with self.session.post(
                f"{INGESTION_API_URL}/images/upload",
                json=SAMPLE_PAYLOADS["image"]
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    logger.info(f"✅ Image ingestion successful: {result['message']}")
                    return True
                else:
                    error = await resp.text()
                    logger.error(f"❌ Image ingestion failed: {resp.status} - {error}")
                    return False
        except Exception as e:
            logger.error(f"❌ Image ingestion test failed: {e}")
            return False
    
    async def test_note_ingestion(self) -> bool:
        """Test note data ingestion."""
        try:
            async with self.session.post(
                f"{INGESTION_API_URL}/notes/upload",
                json=SAMPLE_PAYLOADS["note"]
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    logger.info(f"✅ Note ingestion successful: {result['message']}")
                    return True
                else:
                    error = await resp.text()
                    logger.error(f"❌ Note ingestion failed: {resp.status} - {error}")
                    return False
        except Exception as e:
            logger.error(f"❌ Note ingestion test failed: {e}")
            return False
    
    async def test_kafka_topic_existence(self) -> bool:
        """Test that required Kafka topics exist."""
        expected_topics = [
            "device.audio.raw",
            "device.sensor.gps.raw",
            "device.image.camera.raw",
            "device.text.notes.raw",
            "media.audio.vad_filtered",
            "media.text.transcribed.words",
            "media.image.analysis.minicpm_results"
        ]
        
        try:
            # Use admin client to list topics
            from aiokafka.admin import AIOKafkaAdminClient
            admin = AIOKafkaAdminClient(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
            await admin.start()
            
            metadata = await admin.list_topics()
            existing_topics = set(metadata.topics.keys())
            
            await admin.close()
            
            missing_topics = set(expected_topics) - existing_topics
            
            if not missing_topics:
                logger.info(f"✅ All required Kafka topics exist ({len(expected_topics)} topics)")
                return True
            else:
                logger.warning(f"⚠️  Missing Kafka topics: {missing_topics}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to check Kafka topics: {e}")
            return False
    
    async def monitor_kafka_messages(self, topics: list, duration: int = 30) -> Dict[str, int]:
        """Monitor Kafka messages for a specified duration."""
        message_counts = {topic: 0 for topic in topics}
        
        try:
            consumer = AIOKafkaConsumer(
                *topics,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                auto_offset_reset='latest',
                group_id='pipeline-test-monitor'
            )
            await consumer.start()
            
            logger.info(f"🔍 Monitoring Kafka messages for {duration} seconds...")
            
            start_time = time.time()
            while time.time() - start_time < duration:
                try:
                    # Wait for messages with timeout
                    msg_pack = await asyncio.wait_for(consumer.getmany(timeout_ms=1000), timeout=2.0)
                    
                    for topic_partition, messages in msg_pack.items():
                        topic = topic_partition.topic
                        message_counts[topic] += len(messages)
                        
                        for message in messages:
                            logger.debug(f"📨 Message on {topic}: {message.value[:100]}...")
                            
                except asyncio.TimeoutError:
                    continue
            
            await consumer.stop()
            
            # Report results
            for topic, count in message_counts.items():
                if count > 0:
                    logger.info(f"✅ {topic}: {count} messages")
                else:
                    logger.warning(f"⚠️  {topic}: No messages")
            
            return message_counts
            
        except Exception as e:
            logger.error(f"❌ Failed to monitor Kafka messages: {e}")
            return message_counts


async def run_pipeline_test():
    """Run the complete end-to-end pipeline test."""
    logger.info("🚀 Starting Loom v2 End-to-End Pipeline Test")
    logger.info("=" * 50)
    
    results = {}
    
    async with PipelineTester() as tester:
        # Test 1: API Health
        logger.info("1️⃣  Testing API Health...")
        results["api_health"] = await tester.test_api_health()
        
        # Test 2: Kafka Connectivity
        logger.info("\n2️⃣  Testing Kafka Connectivity...")
        results["kafka_connectivity"] = await tester.test_kafka_connectivity()
        
        # Test 3: Kafka Topics
        logger.info("\n3️⃣  Testing Kafka Topics...")
        results["kafka_topics"] = await tester.test_kafka_topic_existence()
        
        # Test 4: Data Ingestion
        logger.info("\n4️⃣  Testing Data Ingestion...")
        results["audio_ingestion"] = await tester.test_audio_ingestion()
        results["sensor_ingestion"] = await tester.test_sensor_ingestion()
        results["image_ingestion"] = await tester.test_image_ingestion()
        results["note_ingestion"] = await tester.test_note_ingestion()
        
        # Test 5: Message Monitoring
        logger.info("\n5️⃣  Monitoring Kafka Message Flow...")
        monitoring_topics = [
            "device.audio.raw",
            "device.sensor.gps.raw", 
            "device.image.camera.raw",
            "device.text.notes.raw"
        ]
        
        # Send some test data and monitor
        await asyncio.gather(
            tester.test_audio_ingestion(),
            tester.test_sensor_ingestion(),
            tester.monitor_kafka_messages(monitoring_topics, duration=10)
        )
    
    # Report final results
    logger.info("\n" + "=" * 50)
    logger.info("📊 PIPELINE TEST RESULTS")
    logger.info("=" * 50)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} - {test_name.replace('_', ' ').title()}")
    
    logger.info(f"\n📈 Overall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        logger.info("🎉 All pipeline tests PASSED! The system is ready.")
    else:
        logger.warning(f"⚠️  {total-passed} tests FAILED. Check logs above for details.")
    
    return passed == total


if __name__ == "__main__":
    # Run the test
    success = asyncio.run(run_pipeline_test())
    exit(0 if success else 1)