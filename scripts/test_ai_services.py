#!/usr/bin/env python3
"""
AI Service Testing Script

Comprehensive testing script for all AI microservices in the Loom v2 pipeline.
Tests functionality, performance, and error handling for each service.

Usage:
    python scripts/test_ai_services.py                    # Test all services
    python scripts/test_ai_services.py --service nomic-embed   # Test specific service
    python scripts/test_ai_services.py --performance     # Performance testing
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
        "requires_auth": True,
    },
    "onefilellm": {
        "url": "http://localhost:8080",
        "health_endpoint": "/health",
        "requires_auth": False,
    },
    "silero-vad": {
        "url": "http://localhost:8001",
        "health_endpoint": "/healthz",
        "requires_auth": False,
    },
    "parakeet-tdt": {
        "url": "http://localhost:8002",
        "health_endpoint": "/healthz",
        "requires_auth": False,
    },
    "minicpm-vision": {
        "url": "http://localhost:8003",
        "health_endpoint": "/healthz",
        "requires_auth": False,
    },
    "nomic-embed": {
        "url": "http://localhost:8004",
        "health_endpoint": "/healthz",
        "requires_auth": False,
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
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))

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
                    logger.info(f"✅ {service_name} is healthy", health=health_data)
                    return True
                else:
                    logger.error(
                        f"❌ {service_name} health check failed: {response.status}"
                    )
                    return False
        except Exception as e:
            logger.error(f"❌ {service_name} health check error: {e}")
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

    async def test_onefilellm(self) -> Dict[str, Any]:
        """Test OneFileLLM service."""
        logger.info("Testing OneFileLLM")
        results = {}

        # Test text processing
        process_data = {
            "content": "This is a test document for OneFileLLM processing.",
            "content_type": "text/plain",
            "options": {"extract_metadata": True},
        }

        results["text_process"] = await self._test_endpoint(
            "POST", f"{SERVICES['onefilellm']['url']}/process", data=process_data
        )

        return results

    async def test_silero_vad(self) -> Dict[str, Any]:
        """Test Silero VAD service."""
        logger.info("Testing Silero VAD")
        results = {}

        # Test voice activity detection
        vad_data = {
            "audio_data": self.data_generator.generate_test_audio(),
            "sample_rate": 16000,
            "threshold": 0.5,
        }

        results["vad_detect"] = await self._test_endpoint(
            "POST", f"{SERVICES['silero-vad']['url']}/detect", data=vad_data
        )

        # Test batch processing
        batch_data = {
            "audio_chunks": [
                {
                    "audio_data": self.data_generator.generate_test_audio(1000),
                    "sample_rate": 16000,
                    "chunk_id": "chunk_001",
                },
                {
                    "audio_data": self.data_generator.generate_test_audio(1500),
                    "sample_rate": 16000,
                    "chunk_id": "chunk_002",
                },
            ],
            "threshold": 0.5,
        }

        results["vad_batch"] = await self._test_endpoint(
            "POST", f"{SERVICES['silero-vad']['url']}/detect-batch", data=batch_data
        )

        return results

    async def test_parakeet_tdt(self) -> Dict[str, Any]:
        """Test Parakeet TDT ASR service."""
        logger.info("Testing Parakeet TDT")
        results = {}

        # Test transcription
        transcribe_data = {
            "audio_data": self.data_generator.generate_test_audio(3000),
            "sample_rate": 16000,
            "language": "en",
            "return_word_timestamps": True,
            "return_confidence": True,
        }

        results["transcribe"] = await self._test_endpoint(
            "POST",
            f"{SERVICES['parakeet-tdt']['url']}/transcribe",
            data=transcribe_data,
        )

        return results

    async def test_minicpm_vision(self) -> Dict[str, Any]:
        """Test MiniCPM Vision service."""
        logger.info("Testing MiniCPM Vision")
        results = {}

        # Test image analysis
        analysis_data = {
            "image_data": self.data_generator.generate_test_image(),
            "prompt": "Describe what you see in this image",
            "max_tokens": 100,
        }

        results["image_analysis"] = await self._test_endpoint(
            "POST", f"{SERVICES['minicpm-vision']['url']}/analyze", data=analysis_data
        )

        # Test OCR
        ocr_data = {
            "image_data": self.data_generator.generate_test_image(),
            "extract_text_only": True,
        }

        results["ocr"] = await self._test_endpoint(
            "POST", f"{SERVICES['minicpm-vision']['url']}/ocr", data=ocr_data
        )

        # Test VQA (Visual Question Answering)
        vqa_data = {
            "image_data": self.data_generator.generate_test_image(),
            "question": "What colors are present in this image?",
            "max_tokens": 50,
        }

        results["vqa"] = await self._test_endpoint(
            "POST", f"{SERVICES['minicpm-vision']['url']}/vqa", data=vqa_data
        )

        return results

    async def test_nomic_embed(self) -> Dict[str, Any]:
        """Test Nomic Embed Vision service."""
        logger.info("Testing Nomic Embed Vision")
        results = {}

        # Test text embedding
        text_embed_data = {
            "text": "This is a test text for embedding generation.",
            "metadata": {"test_type": "ai_service_test"},
        }

        results["text_embed"] = await self._test_endpoint(
            "POST", f"{SERVICES['nomic-embed']['url']}/embed", data=text_embed_data
        )

        # Test image embedding
        image_embed_data = {
            "image_data": self.data_generator.generate_test_image(),
            "include_description": True,
            "metadata": {"test_type": "ai_service_test"},
        }

        results["image_embed"] = await self._test_endpoint(
            "POST", f"{SERVICES['nomic-embed']['url']}/embed", data=image_embed_data
        )

        # Test combined embedding
        combined_data = {
            "text": "This image shows a test visualization",
            "image_data": self.data_generator.generate_test_image(),
            "include_description": True,
        }

        results["combined_embed"] = await self._test_endpoint(
            "POST", f"{SERVICES['nomic-embed']['url']}/embed", data=combined_data
        )

        # Test batch embeddings
        batch_data = {
            "texts": self.data_generator.generate_test_texts()[:3],
            "images": [
                self.data_generator.generate_test_image(320, 240),
                self.data_generator.generate_test_image(640, 480),
            ],
            "include_descriptions": True,
        }

        results["batch_embed"] = await self._test_endpoint(
            "POST", f"{SERVICES['nomic-embed']['url']}/embed/batch", data=batch_data
        )

        # Test model info
        results["model_info"] = await self._test_endpoint(
            "GET", f"{SERVICES['nomic-embed']['url']}/model/info"
        )

        # Test stats
        results["stats"] = await self._test_endpoint(
            "GET", f"{SERVICES['nomic-embed']['url']}/stats"
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

            service_results = {
                "health_check": health_ok,
                "endpoints": {},
                "errors": [],
            }

            if not health_ok:
                service_results["errors"].append("Health check failed")
                self.results["services"][service_name] = service_results
                continue

            # Test service-specific endpoints
            try:
                if service_name == "ingestion-api":
                    service_results["endpoints"] = await self.test_ingestion_api()
                elif service_name == "onefilellm":
                    service_results["endpoints"] = await self.test_onefilellm()
                elif service_name == "silero-vad":
                    service_results["endpoints"] = await self.test_silero_vad()
                elif service_name == "parakeet-tdt":
                    service_results["endpoints"] = await self.test_parakeet_tdt()
                elif service_name == "minicpm-vision":
                    service_results["endpoints"] = await self.test_minicpm_vision()
                elif service_name == "nomic-embed":
                    service_results["endpoints"] = await self.test_nomic_embed()

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

        total_endpoints = 0
        successful_endpoints = 0

        for service_results in self.results["services"].values():
            for endpoint_result in service_results["endpoints"].values():
                total_endpoints += 1
                if endpoint_result.get("success", False):
                    successful_endpoints += 1

        self.results["summary"] = {
            "total_services": total_services,
            "healthy_services": healthy_services,
            "total_endpoints": total_endpoints,
            "successful_endpoints": successful_endpoints,
            "success_rate": (
                (successful_endpoints / total_endpoints * 100)
                if total_endpoints > 0
                else 0
            ),
            "overall_success": healthy_services == total_services
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
            f"🎯 Endpoints: {summary['successful_endpoints']}/{summary['total_endpoints']} ({summary['success_rate']:.1f}%)"
        )
        print(f"🆔 Test Device ID: {TEST_DEVICE_ID}")

        # Service details
        for service_name, service_results in self.results["services"].items():
            health_status = "✅" if service_results["health_check"] else "❌"
            print(f"\n{health_status} {service_name.upper()}")

            if service_results["errors"]:
                for error in service_results["errors"]:
                    print(f"  ❌ Error: {error}")

            for endpoint_name, endpoint_result in service_results["endpoints"].items():
                status = "✅" if endpoint_result.get("success", False) else "❌"
                time_ms = endpoint_result.get("processing_time_ms", 0)
                print(f"  {status} {endpoint_name} ({time_ms:.1f}ms)")

                if not endpoint_result.get("success", False):
                    error = endpoint_result.get("error", "Unknown error")
                    status_code = endpoint_result.get("status_code", "N/A")
                    print(f"    Error: {error} (HTTP {status_code})")

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
    parser.add_argument(
        "--performance", action="store_true", help="Run performance tests"
    )
    parser.add_argument("--output", type=str, help="Output JSON report file")
    parser.add_argument(
        "--iterations", type=int, default=1, help="Number of test iterations"
    )

    args = parser.parse_args()

    tester = AIServiceTester(args)

    try:
        await tester.setup()

        for i in range(args.iterations):
            if args.iterations > 1:
                logger.info(f"Running iteration {i+1}/{args.iterations}")

            await tester.run_tests()

            if args.iterations > 1 and i < args.iterations - 1:
                await asyncio.sleep(1)  # Brief pause between iterations

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
