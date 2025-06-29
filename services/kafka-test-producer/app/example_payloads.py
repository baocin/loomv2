"""Example payloads for all Kafka topics in the Loom v2 system."""

from datetime import datetime, timezone, timedelta
import base64
import random
import uuid
from typing import Dict, Any, List

from faker import Faker

fake = Faker()


def generate_trace_id() -> str:
    """Generate a unique trace ID."""
    return str(uuid.uuid4())


def generate_device_id() -> str:
    """Generate a device ID."""
    devices = ["phone-1", "laptop-1", "tablet-1", "watch-1", "desktop-1"]
    return random.choice(devices)


def generate_timestamp() -> str:
    """Generate an ISO format timestamp."""
    # Random time within last hour
    offset = random.randint(0, 3600)
    timestamp = datetime.now(timezone.utc) - timedelta(seconds=offset)
    return timestamp.isoformat()


class ExamplePayloads:
    """Generate example payloads for all Kafka topics."""

    @staticmethod
    def device_audio_raw() -> Dict[str, Any]:
        """Raw audio chunks from microphones."""
        # Generate fake base64 audio data (small chunk)
        fake_audio = base64.b64encode(b"FAKE_AUDIO_DATA" * 100).decode()

        return {
            "schema_version": "v1",
            "device_id": generate_device_id(),
            "timestamp": generate_timestamp(),
            "trace_id": generate_trace_id(),
            "data": {
                "audio_data": fake_audio,
                "format": "pcm",
                "sample_rate": 16000,
                "channels": 1,
                "bits_per_sample": 16,
                "duration_ms": 1000,
                "device_info": {"microphone": "Built-in Microphone", "gain": 0.8},
            },
            "metadata": {"app_version": "1.0.0", "os": "macOS", "environment": "quiet"},
        }

    @staticmethod
    def device_video_screen_raw() -> Dict[str, Any]:
        """Keyframes from screen recordings."""
        # Create a valid 1x1 pixel JPEG image
        valid_jpeg = base64.b64encode(
            bytes.fromhex(
                "ffd8ffe000104a46494600010101006000600000ffdb004300080606070605080707070909080a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c20242e2720222c231c1c2837292c30313434341f27393d38323c2e333432ffdb0043010909090c0b0c180d0d1832211c213232323232323232323232323232323232323232323232323232323232323232323232323232323232323232323232323232ffc00011080001000103012200021101031101ffc4001f0000010501010101010100000000000000000102030405060708090a0bffc400b5100002010303020403050504040000017d01020300041105122131410613516107227114328191a1082342b1c11552d1f02433627282090a161718191a25262728292a3435363738393a434445464748494a535455565758595a636465666768696a737475767778797a838485868788898a92939495969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae1e2e3e4e5e6e7e8e9eaf1f2f3f4f5f6f7f8f9faffc4001f0100030101010101010101010000000000000102030405060708090a0bffc400b51100020102040403040705040400010277000102031104052131061241510761711322328108144291a1b1c109233352f0156272d10a162434e125f11718191a262728292a35363738393a434445464748494a535455565758595a636465666768696a737475767778797a82838485868788898a92939495969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae2e3e4e5e6e7e8e9eaf2f3f4f5f6f7f8f9faffda000c03010002110311003f00ffd9"
            )
        ).decode()

        return {
            "schema_version": "v1",
            "device_id": generate_device_id(),
            "timestamp": generate_timestamp(),
            "trace_id": generate_trace_id(),
            "data": {
                "frame_data": valid_jpeg,
                "format": "jpeg",
                "width": 1920,
                "height": 1080,
                "frame_number": random.randint(1, 1000),
                "timestamp_ms": random.randint(0, 60000),
                "screen_info": {
                    "display": "Built-in Display",
                    "resolution": "1920x1080",
                    "scale_factor": 2.0,
                },
            },
            "metadata": {
                "recording_session": generate_trace_id(),
                "app_in_focus": "Chrome",
            },
        }

    @staticmethod
    def device_image_camera_raw() -> Dict[str, Any]:
        """Photos from cameras and screenshots."""
        # Create a valid 1x1 pixel JPEG image (smallest valid JPEG)
        valid_jpeg = base64.b64encode(
            bytes.fromhex(
                "ffd8ffe000104a46494600010101006000600000ffdb004300080606070605080707070909080a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c20242e2720222c231c1c2837292c30313434341f27393d38323c2e333432ffdb0043010909090c0b0c180d0d1832211c213232323232323232323232323232323232323232323232323232323232323232323232323232323232323232323232323232ffc00011080001000103012200021101031101ffc4001f0000010501010101010100000000000000000102030405060708090a0bffc400b5100002010303020403050504040000017d01020300041105122131410613516107227114328191a1082342b1c11552d1f02433627282090a161718191a25262728292a3435363738393a434445464748494a535455565758595a636465666768696a737475767778797a838485868788898a92939495969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae1e2e3e4e5e6e7e8e9eaf1f2f3f4f5f6f7f8f9faffc4001f0100030101010101010101010000000000000102030405060708090a0bffc400b51100020102040403040705040400010277000102031104052131061241510761711322328108144291a1b1c109233352f0156272d10a162434e125f11718191a262728292a35363738393a434445464748494a535455565758595a636465666768696a737475767778797a82838485868788898a92939495969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae2e3e4e5e6e7e8e9eaf2f3f4f5f6f7f8f9faffda000c03010002110311003f00ffd9"
            )
        ).decode()

        return {
            "schema_version": "v1",
            "device_id": generate_device_id(),
            "timestamp": generate_timestamp(),
            "trace_id": generate_trace_id(),
            "data": {
                "image_data": valid_jpeg,
                "format": "jpeg",
                "width": 4032,
                "height": 3024,
                "source": random.choice(["camera", "screenshot"]),
                "camera_info": {
                    "device": "iPhone 14 Pro",
                    "lens": "Wide",
                    "iso": 100,
                    "shutter_speed": "1/125",
                    "aperture": "f/1.8",
                },
            },
            "metadata": {
                "location": {
                    "latitude": float(fake.latitude()),
                    "longitude": float(fake.longitude()),
                },
                "tags": ["nature", "landscape"],
            },
        }

    @staticmethod
    def device_sensor_gps_raw() -> Dict[str, Any]:
        """GPS coordinates with accuracy."""
        return {
            "schema_version": "v1",
            "device_id": generate_device_id(),
            "timestamp": generate_timestamp(),
            "trace_id": generate_trace_id(),
            "data": {
                "latitude": float(fake.latitude()),
                "longitude": float(fake.longitude()),
                "altitude": round(random.uniform(0, 1000), 2),
                "accuracy": round(random.uniform(5, 50), 2),
                "speed": round(random.uniform(0, 30), 2),
                "heading": round(random.uniform(0, 360), 2),
                "provider": "gps",
            },
            "metadata": {
                "activity": random.choice(["walking", "driving", "stationary"]),
                "battery_level": random.randint(10, 100),
            },
        }

    @staticmethod
    def device_sensor_accelerometer_raw() -> Dict[str, Any]:
        """3-axis motion data."""
        return {
            "schema_version": "v1",
            "device_id": generate_device_id(),
            "timestamp": generate_timestamp(),
            "trace_id": generate_trace_id(),
            "data": {
                "x": round(random.uniform(-2, 2), 4),
                "y": round(random.uniform(-2, 2), 4),
                "z": round(random.uniform(8, 12), 4),  # Gravity
                "magnitude": round(random.uniform(9, 11), 4),
                "sample_rate": 100,
            },
            "metadata": {
                "activity": random.choice(["walking", "running", "stationary"]),
                "device_orientation": random.choice(["portrait", "landscape"]),
            },
        }

    @staticmethod
    def device_health_heartrate_raw() -> Dict[str, Any]:
        """Heart rate measurements."""
        return {
            "schema_version": "v1",
            "device_id": generate_device_id(),
            "timestamp": generate_timestamp(),
            "trace_id": generate_trace_id(),
            "data": {
                "heart_rate": random.randint(60, 100),
                "confidence": round(random.uniform(0.8, 1.0), 2),
                "measurement_type": "continuous",
                "variability": random.randint(20, 60),
            },
            "metadata": {
                "activity": random.choice(["resting", "walking", "exercise"]),
                "device_model": "Apple Watch Series 8",
            },
        }

    @staticmethod
    def device_state_power_raw() -> Dict[str, Any]:
        """Battery level and charging status."""
        return {
            "schema_version": "v1",
            "device_id": generate_device_id(),
            "timestamp": generate_timestamp(),
            "trace_id": generate_trace_id(),
            "data": {
                "battery_level": random.randint(1, 100),
                "is_charging": random.choice([True, False]),
                "power_source": random.choice(["battery", "ac", "usb"]),
                "battery_health": random.randint(80, 100),
                "temperature_celsius": round(random.uniform(20, 40), 1),
            },
            "metadata": {
                "cycles": random.randint(100, 500),
                "time_to_full": (
                    random.randint(0, 180) if random.choice([True, False]) else None
                ),
            },
        }

    @staticmethod
    def external_twitter_liked_raw() -> Dict[str, Any]:
        """Liked tweets from Twitter/X."""
        return {
            "schema_version": "v1",
            "trace_id": generate_trace_id(),
            "timestamp": generate_timestamp(),
            "data": {
                "tweet_id": str(
                    random.randint(1000000000000000000, 9999999999999999999)
                ),
                "tweet_url": f"https://x.com/{fake.user_name()}/status/{random.randint(1000000000000000000, 9999999999999999999)}",
                "tweet_text": fake.text(max_nb_chars=280),
                "author_username": fake.user_name(),
                "author_display_name": fake.name(),
                "created_at": fake.date_time_this_year().isoformat() + "Z",
                "like_count": random.randint(0, 10000),
                "retweet_count": random.randint(0, 5000),
                "reply_count": random.randint(0, 1000),
                "is_retweet": random.choice([True, False]),
                "has_media": random.choice([True, False]),
                "media_urls": (
                    [fake.image_url()] if random.choice([True, False]) else []
                ),
            },
            "metadata": {
                "fetched_at": generate_timestamp(),
                "user_agent": "Mozilla/5.0",
            },
        }

    @staticmethod
    def external_twitter_images_raw() -> Dict[str, Any]:
        """Twitter screenshot images for OCR."""
        # Create a valid 1x1 pixel PNG image (smallest valid PNG)
        # This is a real PNG file that won't cause image processing errors
        valid_png = base64.b64encode(
            bytes.fromhex(
                "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154785e6364000000030001869182e70000000049454e44ae426082"
            )
        ).decode()

        return {
            "schema_version": "v1",
            "trace_id": generate_trace_id(),
            "tweet_id": str(random.randint(1000000000000000000, 9999999999999999999)),
            "tweet_url": f"https://x.com/{fake.user_name()}/status/{random.randint(1000000000000000000, 9999999999999999999)}",
            "device_id": generate_device_id(),
            "recorded_at": generate_timestamp(),
            "data": {
                "image_data": valid_png,
                "format": "png",
                "width": 1200,
                "height": 800,
                "tweet_id": str(
                    random.randint(1000000000000000000, 9999999999999999999)
                ),
                "screenshot_timestamp": generate_timestamp(),
            },
            "metadata": {"processor_version": "1.0.0", "screenshot_tool": "playwright"},
        }

    @staticmethod
    def media_audio_vad_filtered() -> Dict[str, Any]:
        """Audio chunks identified as speech."""
        fake_audio = base64.b64encode(b"FAKE_SPEECH_AUDIO" * 150).decode()

        return {
            "schema_version": "v1",
            "device_id": generate_device_id(),
            "timestamp": generate_timestamp(),
            "trace_id": generate_trace_id(),
            "data": {
                "audio_data": fake_audio,
                "format": "pcm",
                "sample_rate": 16000,
                "channels": 1,
                "duration_ms": 3000,
                "speech_probability": round(random.uniform(0.85, 0.99), 3),
                "start_time": 0,
                "end_time": 3000,
            },
            "metadata": {
                "vad_model": "silero-vad",
                "processing_time_ms": random.randint(10, 50),
            },
        }

    @staticmethod
    def media_text_transcribed_words() -> Dict[str, Any]:
        """Word-by-word transcripts from speech."""
        words = fake.sentence().split()
        word_timestamps = []
        current_time = 0.0

        for word in words:
            start = current_time
            duration = random.uniform(0.2, 0.5)
            end = start + duration
            word_timestamps.append(
                {
                    "word": word,
                    "start": round(start, 3),
                    "end": round(end, 3),
                    "confidence": round(random.uniform(0.8, 1.0), 3),
                }
            )
            current_time = end + random.uniform(0.05, 0.2)  # pause between words

        return {
            "schema_version": "v1",
            "device_id": generate_device_id(),
            "timestamp": generate_timestamp(),
            "trace_id": generate_trace_id(),
            "data": {
                "transcript": " ".join(words),
                "words": word_timestamps,
                "language": "en",
                "duration_seconds": round(current_time, 3),
                "audio_trace_id": generate_trace_id(),
            },
            "metadata": {
                "asr_model": "parakeet-tdt",
                "processing_time_ms": random.randint(100, 500),
            },
        }

    @staticmethod
    def task_url_ingest() -> Dict[str, Any]:
        """URLs to be processed."""
        url_types = ["twitter", "hackernews", "pdf", "webpage"]
        url_type = random.choice(url_types)

        urls = {
            "twitter": f"https://x.com/{fake.user_name()}/status/{random.randint(1000000000000000000, 9999999999999999999)}",
            "hackernews": f"https://news.ycombinator.com/item?id={random.randint(30000000, 40000000)}",
            "pdf": f"https://example.com/papers/{fake.slug()}.pdf",
            "webpage": fake.url(),
        }

        return {
            "schema_version": "v1",
            "trace_id": generate_trace_id(),
            "timestamp": generate_timestamp(),
            "data": {
                "url": urls[url_type],
                "url_type": url_type,
                "priority": random.choice(["high", "medium", "low"]),
                "source": random.choice(["manual", "auto", "scheduled"]),
                "requested_by": generate_device_id(),
            },
            "metadata": {"retry_count": 0, "max_retries": 3},
        }

    @staticmethod
    def analysis_text_embedded_twitter() -> Dict[str, Any]:
        """Twitter content with embeddings."""
        text = fake.text(max_nb_chars=280)
        # Generate fake embedding (384 dimensions for all-MiniLM-L6-v2)
        embedding = [round(random.uniform(-1, 1), 6) for _ in range(384)]

        return {
            "schema_version": "v1",
            "trace_id": generate_trace_id(),
            "timestamp": generate_timestamp(),
            "data": {
                "tweet_id": str(
                    random.randint(1000000000000000000, 9999999999999999999)
                ),
                "tweet_text": text,
                "author_username": fake.user_name(),
                "embedding": embedding,
                "embedding_model": "all-MiniLM-L6-v2",
                "embedding_dimensions": 384,
            },
            "metadata": {
                "processing_time_ms": random.randint(50, 200),
                "char_count": len(text),
            },
        }

    @staticmethod
    def get_all_topics() -> Dict[str, Dict[str, Any]]:
        """Get example payloads for all topics."""
        return {
            # Raw Data Ingestion
            "device.audio.raw": ExamplePayloads.device_audio_raw(),
            "device.video.screen.raw": ExamplePayloads.device_video_screen_raw(),
            "device.image.camera.raw": ExamplePayloads.device_image_camera_raw(),
            "device.sensor.gps.raw": ExamplePayloads.device_sensor_gps_raw(),
            "device.sensor.accelerometer.raw": ExamplePayloads.device_sensor_accelerometer_raw(),
            "device.health.heartrate.raw": ExamplePayloads.device_health_heartrate_raw(),
            "device.state.power.raw": ExamplePayloads.device_state_power_raw(),
            # External Sources
            "external.twitter.liked.raw": ExamplePayloads.external_twitter_liked_raw(),
            "external.twitter.images.raw": ExamplePayloads.external_twitter_images_raw(),
            # Processed Data
            "media.audio.vad_filtered": ExamplePayloads.media_audio_vad_filtered(),
            "media.text.transcribed.words": ExamplePayloads.media_text_transcribed_words(),
            # Tasks
            "task.url.ingest": ExamplePayloads.task_url_ingest(),
            # Analysis
            "analysis.text.embedded.twitter": ExamplePayloads.analysis_text_embedded_twitter(),
        }

    @staticmethod
    def get_topic_list() -> List[str]:
        """Get list of all available topics."""
        return list(ExamplePayloads.get_all_topics().keys())
