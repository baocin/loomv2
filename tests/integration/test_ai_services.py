#!/usr/bin/env python3
"""
AI Service Testing Script

Tests health, readiness, and basic functionality of AI microservices in the Loom v2 pipeline.
Most AI services are Kafka consumers without REST inference endpoints.

Usage:
    python scripts/test_ai_services.py                    # Test all services
    python scripts/test_ai_services.py --service silero-vad   # Test specific service
    python scripts/test_ai_services.py --output report.json    # Generate JSON report
"""

import asyncio
import base64
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import argparse
import sys

import aiohttp
import structlog
from PIL import Image
import io

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

logger = structlog.get_logger(__name__)

# Test configuration
TEST_DEVICE_ID = str(uuid.uuid4())  # Generate unique device ID for this test run
TEST_RECORDED_AT = datetime.now(timezone.utc).isoformat()

# Service configurations
SERVICES = {
    "ingestion-api": {
        "url": "http://localhost:8000",
        "health_endpoint": "/healthz",
        "ready_endpoint": "/readyz",
        "requires_auth": True,
        "type": "rest_api",
    },
    "silero-vad": {
        "url": "http://localhost:8001",
        "health_endpoint": "/healthz",
        "ready_endpoint": "/readyz",
        "requires_auth": False,
        "type": "kafka_consumer",
        "kafka_topics": {
            "input": "device.audio.raw",
            "output": "media.audio.vad_filtered"
        }
    },
    "kyutai-stt": {
        "url": "http://localhost:8002",
        "health_endpoint": "/healthz",
        "ready_endpoint": "/readyz",
        "requires_auth": False,
        "type": "kafka_consumer",
        "kafka_topics": {
            "input": "media.audio.vad_filtered",
            "output": "media.text.transcribed.words"
        }
    },
    "minicpm-vision": {
        "url": "http://localhost:8003",
        "health_endpoint": "/healthz",
        "ready_endpoint": "/readyz",
        "requires_auth": False,
        "type": "kafka_consumer",
        "kafka_topics": {
            "input": ["device.image.camera.raw", "device.video.screen.raw"],
            "output": "media.image.analysis.minicpm_results"
        }
    },
    "moondream-ocr": {
        "url": "http://localhost:8007",
        "health_endpoint": "/healthz",
        "ready_endpoint": "/readyz",
        "requires_auth": False,
        "type": "hybrid",  # Both REST API and Kafka consumer
        "kafka_topics": {
            "input": "external.twitter.images.raw",
            "output": "media.text.extracted.twitter"
        }
    },
}


class TestDataGenerator:
    """Generate realistic test data for AI services."""

    @staticmethod
    def generate_test_image(
        width: int = 640, height: int = 480, format: str = "JPEG"
    ) -> str:
        """Generate a test image and return as base64."""
        # Create a simple test image
        img = Image.new("RGB", (width, height), color=(73, 109, 137))

        # Add some text
        try:
            from PIL import ImageDraw

            draw = ImageDraw.Draw(img)
            draw.text((10, 10), "Test Image for AI Processing", fill=(255, 255, 255))
        except ImportError:
            pass  # PIL might not have font support

        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format=format)
        return base64.b64encode(buffer.getvalue()).decode()

    @staticmethod
    def generate_test_audio(duration_ms: int = 3000, sample_rate: int = 16000) -> str:
        """Generate test audio data and return as base64."""
        # Generate simple sine wave audio data
        import math

        samples = int(sample_rate * duration_ms / 1000)
        audio_data = bytearray()

        for i in range(samples):
            # Simple sine wave at 440Hz
            sample = int(32767 * math.sin(2 * math.pi * 440 * i / sample_rate))
            audio_data.extend(sample.to_bytes(2, byteorder="little", signed=True))

        return base64.b64encode(audio_data).decode()

    @staticmethod
    def generate_test_texts() -> List[str]:
        """Generate various test texts for embedding and processing."""
        return [
            "This is a short test text.",
            "This is a medium-length test text that contains multiple sentences. It should provide enough content for meaningful embedding generation and analysis.",
            """This is a longer test document that contains multiple paragraphs and various types of content.

            It includes different sentence structures, punctuation marks, and even some technical terms like "AI", "machine learning", and "natural language processing".

            This type of content is typical of what the Loom v2 system would process in real-world scenarios, including notes, transcripts, and document content.""",
            "Technical content: PostgreSQL, TimescaleDB, Kafka, Docker, Kubernetes, FastAPI, Python",
            "Question: What is the meaning of life? Answer: 42.",
            "Code snippet: def hello_world(): print('Hello, World!')",
        ]


class AIServiceTester:
    """Main testing class for AI services."""

    def __init__(self, args):
        self.args = args
        self.session: Optional[aiohttp.ClientSession] = None
        self.results: Dict[str, Any] = {
            "start_time": datetime.now(timezone.utc).isoformat(),
            "test_device_id": TEST_DEVICE_ID,
            "services": {},
            "summary": {},
        }
        self.data_generator = TestDataGenerator()

    async def setup(self):
        """Initialize the test session."""
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60))

    async def cleanup(self):
        """Clean up resources."""
        if self.session:
            await self.session.close()

    async def test_service_health(
        self, service_name: str, config: Dict[str, Any]
    ) -> bool:
        """Test service health endpoint."""
        try:
            url = f"{config['url']}{config['health_endpoint']}"
            async with self.session.get(url) as response:
                if response.status == 200:
                    health_data = await response.json()
                    logger.info(f"✅ {service_name} health check passed", health=health_data)
                    return True
                else:
                    logger.error(
                        f"❌ {service_name} health check failed: {response.status}"
                    )
                    return False
        except Exception as e:
            logger.error(f"❌ {service_name} health check error: {e}")
            return False

    async def test_service_readiness(
        self, service_name: str, config: Dict[str, Any], max_retries: int = 30, retry_delay: float = 2.0
    ) -> bool:
        """Test service readiness endpoint with retries."""
        if "ready_endpoint" not in config:
            return True  # Skip if no readiness endpoint
            
        url = f"{config['url']}{config['ready_endpoint']}"
        
        for attempt in range(max_retries):
            try:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        ready_data = await response.json()
                        logger.info(f"✅ {service_name} is ready", ready=ready_data)
                        return True
                    else:
                        ready_text = await response.text()
                        if attempt == 0:
                            logger.info(
                                f"⏳ {service_name} not ready yet, waiting for model to load...", 
                                status=response.status,
                                response=ready_text
                            )
                        elif attempt % 5 == 0:  # Log every 5 attempts
                            logger.info(
                                f"⏳ Still waiting for {service_name} to be ready...", 
                                attempt=attempt + 1,
                                max_retries=max_retries
                            )
                        
                        # If it's a model loading issue, continue retrying
                        if response.status == 503 and "model" in ready_text.lower():
                            await asyncio.sleep(retry_delay)
                            continue
                        # For other errors, fail fast after a few retries
                        elif attempt > 3:
                            logger.error(
                                f"❌ {service_name} readiness check failed: {response.status}", 
                                response=ready_text
                            )
                            return False
            except Exception as e:
                if attempt == 0:
                    logger.warning(f"⏳ {service_name} connection error, retrying...", error=str(e))
                await asyncio.sleep(retry_delay)
                continue
                
        logger.error(f"❌ {service_name} readiness check timed out after {max_retries * retry_delay}s")
        return False

    async def test_ingestion_api(self) -> Dict[str, Any]:
        """Test ingestion API endpoints with required parameters."""
        logger.info("Testing Ingestion API")
        results = {}

        # Test audio upload
        audio_data = {
            "device_id": TEST_DEVICE_ID,
            "recorded_at": TEST_RECORDED_AT,
            "chunk_data": self.data_generator.generate_test_audio(),
            "sample_rate": 16000,
            "channels": 1,
            "duration_ms": 3000,
            "format": "wav",
        }

        results["audio_upload"] = await self._test_endpoint(
            "POST",
            f"{SERVICES['ingestion-api']['url']}/audio/upload",
            data=audio_data,
            requires_auth=True,
        )

        # Test image upload
        image_data = {
            "device_id": TEST_DEVICE_ID,
            "recorded_at": TEST_RECORDED_AT,
            "image_data": self.data_generator.generate_test_image(),
            "width": 640,
            "height": 480,
            "format": "jpeg",
            "camera_type": "test",
            "file_size": 12345,
        }

        results["image_upload"] = await self._test_endpoint(
            "POST",
            f"{SERVICES['ingestion-api']['url']}/images/upload",
            data=image_data,
            requires_auth=True,
        )

        # Test note upload
        note_data = {
            "device_id": TEST_DEVICE_ID,
            "recorded_at": TEST_RECORDED_AT,
            "content": "This is a test note for AI processing",
            "title": "Test Note",
            "note_type": "text",
            "tags": ["test", "ai"],
        }

        results["note_upload"] = await self._test_endpoint(
            "POST",
            f"{SERVICES['ingestion-api']['url']}/notes/upload",
            data=note_data,
            requires_auth=True,
        )

        # Test GitHub ingestion
        github_data = {
            "device_id": TEST_DEVICE_ID,
            "recorded_at": TEST_RECORDED_AT,
            "url": "https://github.com/octocat/Hello-World",
            "repository_type": "repository",
            "priority": 5,
            "include_files": ["*.md", "*.py"],
            "max_file_size": 1048576,
        }

        results["github_ingest"] = await self._test_endpoint(
            "POST",
            f"{SERVICES['ingestion-api']['url']}/github/ingest",
            data=github_data,
            requires_auth=True,
        )

        # Test document upload
        test_content = "This is a test document for OneFileLLM processing."
        document_data = {
            "device_id": TEST_DEVICE_ID,
            "recorded_at": TEST_RECORDED_AT,
            "filename": "test.txt",
            "file_data": base64.b64encode(test_content.encode()).decode(),
            "content_type": "text/plain",
            "file_size": len(test_content.encode()),
            "document_type": "text",
            "priority": 5,
        }

        results["document_upload"] = await self._test_endpoint(
            "POST",
            f"{SERVICES['ingestion-api']['url']}/documents/upload",
            data=document_data,
            requires_auth=True,
        )

        return results

    async def test_kafka_consumer_service(self, service_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Test Kafka consumer services (VAD, TDT, Vision)."""
        logger.info(f"Testing {service_name} (Kafka Consumer)")
        results = {}

        # Test warmup endpoint if available
        warmup_result = await self._test_endpoint(
            "POST", f"{config['url']}/warmup"
        )
        results["warmup"] = warmup_result

        # Test metrics endpoint
        metrics_result = await self._test_endpoint(
            "GET", f"{config['url']}/metrics"
        )
        results["metrics"] = metrics_result

        # Test root endpoint for service info
        info_result = await self._test_endpoint(
            "GET", f"{config['url']}/"
        )
        results["service_info"] = info_result

        # For MiniCPM Vision, test the status endpoint
        if service_name == "minicpm-vision":
            status_result = await self._test_endpoint(
                "GET", f"{config['url']}/status"
            )
            results["status"] = status_result

        return results

    async def test_moondream_ocr(self) -> Dict[str, Any]:
        """Test Moondream OCR service."""
        logger.info("Testing Moondream OCR")
        results = {}

        # Test OCR endpoint
        ocr_data = {
            "image_data": self.data_generator.generate_test_image(),
            "prompt": "Extract all text from this image"
        }

        results["ocr"] = await self._test_endpoint(
            "POST", f"{SERVICES['moondream-ocr']['url']}/ocr", data=ocr_data
        )

        # Test service info
        results["service_info"] = await self._test_endpoint(
            "GET", f"{SERVICES['moondream-ocr']['url']}/"
        )

        return results




    async def _test_endpoint(
        self,
        method: str,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        requires_auth: bool = False,
    ) -> Dict[str, Any]:
        """Test a single endpoint and return results."""
        start_time = time.time()

        headers = {"Content-Type": "application/json"}
        if requires_auth:
            headers["X-API-Key"] = "apikeyhere"

        try:
            if method == "GET":
                async with self.session.get(url, headers=headers) as response:
                    result = await self._process_response(response, start_time)
            elif method == "POST":
                async with self.session.post(
                    url, json=data, headers=headers
                ) as response:
                    result = await self._process_response(response, start_time)
            else:
                raise ValueError(f"Unsupported method: {method}")

            return result

        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            return {
                "success": False,
                "error": str(e),
                "processing_time_ms": processing_time,
                "status_code": None,
            }

    async def _process_response(
        self, response: aiohttp.ClientResponse, start_time: float
    ) -> Dict[str, Any]:
        """Process HTTP response and return structured result."""
        processing_time = (time.time() - start_time) * 1000

        try:
            response_data = await response.json()
        except Exception:
            response_data = await response.text()

        return {
            "success": response.status in [200, 201],
            "status_code": response.status,
            "processing_time_ms": processing_time,
            "response_data": response_data,
        }

    async def run_tests(self) -> None:
        """Run all AI service tests."""
        logger.info("🚀 Starting AI Service Testing", device_id=TEST_DEVICE_ID)

        # Determine which services to test
        services_to_test = (
            [self.args.service] if self.args.service else list(SERVICES.keys())
        )

        for service_name in services_to_test:
            if service_name not in SERVICES:
                logger.error(f"Unknown service: {service_name}")
                continue

            logger.info(f"Testing service: {service_name}")
            service_config = SERVICES[service_name]

            # Test health first
            health_ok = await self.test_service_health(service_name, service_config)
            
            # Test readiness
            ready_ok = await self.test_service_readiness(service_name, service_config)

            service_results = {
                "health_check": health_ok,
                "readiness_check": ready_ok,
                "service_type": service_config.get("type", "unknown"),
                "endpoints": {},
                "errors": [],
            }

            if not health_ok:
                service_results["errors"].append("Health check failed")
                self.results["services"][service_name] = service_results
                continue

            # Test service-specific endpoints based on type
            try:
                if service_name == "ingestion-api":
                    service_results["endpoints"] = await self.test_ingestion_api()
                elif service_config.get("type") == "kafka_consumer":
                    service_results["endpoints"] = await self.test_kafka_consumer_service(
                        service_name, service_config
                    )
                elif service_name == "moondream-ocr":
                    service_results["endpoints"] = await self.test_moondream_ocr()
                else:
                    logger.warning(f"No specific tests for {service_name}")

            except Exception as e:
                logger.error(f"Error testing {service_name}: {e}")
                service_results["errors"].append(str(e))

            self.results["services"][service_name] = service_results

    def generate_summary(self) -> None:
        """Generate test summary."""
        total_services = len(self.results["services"])
        healthy_services = sum(
            1 for s in self.results["services"].values() if s["health_check"]
        )
        ready_services = sum(
            1 for s in self.results["services"].values() if s.get("readiness_check", True)
        )

        total_endpoints = 0
        successful_endpoints = 0

        for service_results in self.results["services"].values():
            for endpoint_result in service_results["endpoints"].values():
                total_endpoints += 1
                if endpoint_result.get("success", False):
                    successful_endpoints += 1

        # Count service types
        service_types = {}
        for service_results in self.results["services"].values():
            service_type = service_results.get("service_type", "unknown")
            service_types[service_type] = service_types.get(service_type, 0) + 1

        self.results["summary"] = {
            "total_services": total_services,
            "healthy_services": healthy_services,
            "ready_services": ready_services,
            "total_endpoints": total_endpoints,
            "successful_endpoints": successful_endpoints,
            "success_rate": (
                (successful_endpoints / total_endpoints * 100)
                if total_endpoints > 0
                else 0
            ),
            "service_types": service_types,
            "overall_success": healthy_services == total_services
            and ready_services == total_services
            and successful_endpoints == total_endpoints,
        }

    def print_results(self) -> None:
        """Print formatted test results."""
        print("\n" + "=" * 80)
        print("🤖 AI SERVICE TESTING RESULTS")
        print("=" * 80)

        summary = self.results["summary"]
        print(
            f"\n📊 Overall Status: {'✅ PASS' if summary['overall_success'] else '❌ FAIL'}"
        )
        print(
            f"🏥 Health Checks: {summary['healthy_services']}/{summary['total_services']}"
        )
        print(
            f"✅ Readiness Checks: {summary['ready_services']}/{summary['total_services']}"
        )
        print(
            f"🎯 Endpoints Tested: {summary['successful_endpoints']}/{summary['total_endpoints']} ({summary['success_rate']:.1f}%)"
        )
        print(f"🆔 Test Device ID: {TEST_DEVICE_ID}")
        
        # Service types breakdown
        print("\n📦 Service Types:")
        for stype, count in summary["service_types"].items():
            print(f"  - {stype}: {count}")

        # Service details
        print("\n📋 Service Details:")
        for service_name, service_results in self.results["services"].items():
            health_status = "✅" if service_results["health_check"] else "❌"
            ready_status = "✅" if service_results.get("readiness_check", True) else "❌"
            service_type = service_results.get("service_type", "unknown")
            
            print(f"\n{health_status} {service_name.upper()} ({service_type})")
            print(f"  Health: {health_status} | Ready: {ready_status}")

            if service_results["errors"]:
                for error in service_results["errors"]:
                    print(f"  ❌ Error: {error}")

            if service_results["endpoints"]:
                print("  Endpoints:")
                for endpoint_name, endpoint_result in service_results["endpoints"].items():
                    status = "✅" if endpoint_result.get("success", False) else "❌"
                    time_ms = endpoint_result.get("processing_time_ms", 0)
                    print(f"    {status} {endpoint_name} ({time_ms:.1f}ms)")

                    if not endpoint_result.get("success", False):
                        error = endpoint_result.get("error", "Unknown error")
                        status_code = endpoint_result.get("status_code", "N/A")
                        print(f"      Error: {error} (HTTP {status_code})")

    async def save_results(self, output_path: str) -> None:
        """Save results to JSON file."""
        self.results["end_time"] = datetime.now(timezone.utc).isoformat()

        with open(output_path, "w") as f:
            json.dump(self.results, f, indent=2, default=str)

        logger.info(f"Results saved to {output_path}")


async def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description="AI Service Testing Script")
    parser.add_argument(
        "--service", choices=list(SERVICES.keys()), help="Test specific service only"
    )
    parser.add_argument("--output", type=str, help="Output JSON report file")

    args = parser.parse_args()

    tester = AIServiceTester(args)

    try:
        await tester.setup()
        await tester.run_tests()
        tester.generate_summary()
        tester.print_results()

        if args.output:
            await tester.save_results(args.output)

        # Exit with appropriate code
        if tester.results["summary"]["overall_success"]:
            return 0
        else:
            return 1

    finally:
        await tester.cleanup()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
