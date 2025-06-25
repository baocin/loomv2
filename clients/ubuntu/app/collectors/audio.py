"""Audio data collector for Ubuntu/Linux."""

import asyncio
import io
import subprocess
import wave
from typing import Any

import structlog

from app.collectors import BaseCollector

logger = structlog.get_logger(__name__)


class AudioCollector(BaseCollector):
    """Collects audio data from microphone on Ubuntu."""

    def __init__(
        self,
        api_client,
        poll_interval: float,
        send_interval: float,
        sample_rate: int = 44100,
        channels: int = 1,
        audio_format: str = "wav",
    ):
        super().__init__(api_client, poll_interval, send_interval)
        self.sample_rate = sample_rate
        self.channels = channels
        self.audio_format = audio_format
        self._recording = False
        self._audio_available = False

    async def initialize(self) -> None:
        """Initialize the audio collector."""
        try:
            # Check if audio devices are available
            await self._check_audio_devices()

            logger.info(
                "Audio collector initialized",
                sample_rate=self.sample_rate,
                channels=self.channels,
                format=self.audio_format,
                audio_available=self._audio_available,
            )

            self._initialized = True

        except Exception as e:
            logger.error("Failed to initialize audio collector", error=str(e))
            raise

    async def _check_audio_devices(self) -> None:
        """Check for available audio input devices."""
        try:
            # Try to list audio devices using arecord
            result = subprocess.run(
                ["arecord", "-l"], capture_output=True, text=True, timeout=5
            )

            if result.returncode == 0 and result.stdout:
                logger.info("Audio devices found", devices=result.stdout.strip())
                self._audio_available = True
            else:
                logger.warning("No audio input devices found")
                self._audio_available = False

        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning("Could not check audio devices", error=str(e))
            self._audio_available = False

    async def poll_data(self) -> dict[str, Any] | None:
        """Poll audio data."""
        if not self._audio_available:
            logger.debug("Audio not available, skipping poll")
            return None

        try:
            # Record audio for the poll interval duration
            audio_data = await self._record_audio_chunk(self.poll_interval)

            if not audio_data:
                return None

            metadata = {
                "sample_rate": self.sample_rate,
                "channels": self.channels,
                "duration_ms": int(self.poll_interval * 1000),
                "format": self.audio_format,
                "source": "microphone",
                "size_bytes": len(audio_data),
            }

            return {
                "audio_data": audio_data.hex(),  # Convert to hex for JSON serialization
                "metadata": metadata,
            }

        except Exception as e:
            logger.error("Error polling audio data", error=str(e))
            return None

    async def _record_audio_chunk(self, duration: float) -> bytes | None:
        """Record audio chunk using arecord."""
        try:
            # Use arecord to capture audio
            cmd = [
                "arecord",
                "-f",
                "S16_LE",  # 16-bit little endian
                "-c",
                str(self.channels),  # Number of channels
                "-r",
                str(self.sample_rate),  # Sample rate
                "-d",
                str(duration),  # Duration in seconds
                "-q",  # Quiet mode
                "-",  # Output to stdout
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0 and stdout:
                # Convert raw audio to WAV format
                wav_data = self._raw_to_wav(stdout)
                return wav_data
            else:
                logger.warning(
                    "Audio recording failed",
                    returncode=process.returncode,
                    stderr=stderr.decode() if stderr else None,
                )
                return None

        except Exception as e:
            logger.error("Error recording audio chunk", error=str(e))
            return None

    def _raw_to_wav(self, raw_audio: bytes) -> bytes:
        """Convert raw audio data to WAV format."""
        try:
            buffer = io.BytesIO()

            with wave.open(buffer, "wb") as wav_file:
                wav_file.setnchannels(self.channels)
                wav_file.setsampwidth(2)  # 16-bit = 2 bytes
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(raw_audio)

            return buffer.getvalue()

        except Exception as e:
            logger.error("Error converting raw audio to WAV", error=str(e))
            return raw_audio  # Return raw data as fallback

    async def _generate_mock_audio_data(self) -> bytes:
        """Generate mock audio data for testing when no real audio is available."""
        import math

        # Generate a simple sine wave
        duration = self.poll_interval
        num_samples = int(self.sample_rate * duration)

        # Generate sine wave samples
        frequency = 440  # A4 note
        amplitude = 0.3
        samples = []

        for i in range(num_samples):
            t = i / self.sample_rate
            sample = amplitude * math.sin(2 * math.pi * frequency * t)
            # Convert to 16-bit integer
            sample_int = int(sample * 32767)
            samples.append(sample_int)

        # Create WAV data in memory
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(self.sample_rate)

            # Convert samples to bytes
            for sample in samples:
                wav_file.writeframes(
                    sample.to_bytes(2, byteorder="little", signed=True)
                )

        return buffer.getvalue()

    async def send_data_batch(self, data_batch: list[dict[str, Any]]) -> bool:
        """Send a batch of audio data."""
        try:
            success_count = 0

            for audio_data in data_batch:
                # Convert hex back to bytes
                audio_bytes = bytes.fromhex(audio_data["audio_data"])

                success = await self.api_client.send_audio(
                    audio_bytes, audio_data["metadata"]
                )

                if success:
                    success_count += 1

            # Consider successful if at least 80% of audio chunks were sent
            return success_count >= len(data_batch) * 0.8

        except Exception as e:
            logger.error("Error sending audio data batch", error=str(e))
            return False

    async def cleanup(self) -> None:
        """Cleanup audio resources."""
        try:
            self._recording = False
            logger.info("Audio collector cleaned up")

        except Exception as e:
            logger.error("Error cleaning up audio collector", error=str(e))

    async def get_status(self) -> dict[str, Any]:
        """Get audio collector status."""
        base_status = await super().get_status()
        base_status.update(
            {
                "recording": self._recording,
                "audio_available": self._audio_available,
                "sample_rate": self.sample_rate,
                "channels": self.channels,
                "format": self.audio_format,
            }
        )
        return base_status
