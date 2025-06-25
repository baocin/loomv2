"""Screen capture collector for Ubuntu/Linux."""

import asyncio
import io
import os
import subprocess
import tempfile
from typing import Any

import structlog

from app.collectors import BaseCollector

logger = structlog.get_logger(__name__)


class ScreenCollector(BaseCollector):
    """Collects screen capture data for Ubuntu."""

    def __init__(
        self,
        api_client,
        poll_interval: float,
        send_interval: float,
        quality: int = 80,
        max_width: int = 1920,
        max_height: int = 1080,
    ):
        super().__init__(api_client, poll_interval, send_interval)
        self.quality = quality
        self.max_width = max_width
        self.max_height = max_height
        self._display_available = False
        self._capture_method = None

    async def initialize(self) -> None:
        """Initialize the screen collector."""
        try:
            # Check for available display and capture methods
            await self._check_display_environment()

            logger.info(
                "Screen collector initialized",
                quality=self.quality,
                max_resolution=f"{self.max_width}x{self.max_height}",
                display_available=self._display_available,
                capture_method=self._capture_method,
            )

            self._initialized = True

        except Exception as e:
            logger.error("Failed to initialize screen collector", error=str(e))
            raise

    async def _check_display_environment(self) -> None:
        """Check for available display and screen capture tools."""
        # Check if DISPLAY is set
        display = os.environ.get("DISPLAY")
        if not display:
            logger.warning("No DISPLAY environment variable set")
            self._display_available = False
            return

        # Try different capture methods in order of preference
        capture_tools = [
            ("scrot", ["scrot", "--version"]),
            ("gnome-screenshot", ["gnome-screenshot", "--version"]),
            ("import", ["import", "-version"]),  # ImageMagick
            ("xwd", ["which", "xwd"]),
        ]

        for tool_name, test_cmd in capture_tools:
            try:
                result = subprocess.run(test_cmd, capture_output=True, timeout=5)

                if result.returncode == 0:
                    self._capture_method = tool_name
                    self._display_available = True
                    logger.info(f"Using {tool_name} for screen capture")
                    return

            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue

        logger.warning("No screen capture tools found")
        self._display_available = False
        self._capture_method = None

    async def poll_data(self) -> dict[str, Any] | None:
        """Poll screen capture data."""
        if not self._display_available:
            logger.debug("Display not available, skipping screen capture")
            return None

        try:
            # Capture screen
            image_data = await self._capture_screen()

            if not image_data:
                return None

            metadata = {
                "format": "png",
                "quality": self.quality,
                "max_width": self.max_width,
                "max_height": self.max_height,
                "capture_method": self._capture_method,
                "size_bytes": len(image_data),
            }

            return {
                "image_data": image_data.hex(),  # Convert to hex for JSON serialization
                "metadata": metadata,
            }

        except Exception as e:
            logger.error("Error polling screen capture", error=str(e))
            return None

    async def _capture_screen(self) -> bytes | None:
        """Capture the screen using available tools."""
        if not self._capture_method:
            return None

        try:
            if self._capture_method == "scrot":
                return await self._capture_with_scrot()
            elif self._capture_method == "gnome-screenshot":
                return await self._capture_with_gnome_screenshot()
            elif self._capture_method == "import":
                return await self._capture_with_imagemagick()
            elif self._capture_method == "xwd":
                return await self._capture_with_xwd()
            else:
                logger.warning(f"Unknown capture method: {self._capture_method}")
                return None

        except Exception as e:
            logger.error(
                f"Error capturing screen with {self._capture_method}", error=str(e)
            )
            return None

    async def _capture_with_scrot(self) -> bytes | None:
        """Capture screen using scrot."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
            try:
                cmd = [
                    "scrot",
                    "--quality",
                    str(self.quality),
                    "--silent",
                    tmp_file.name,
                ]

                process = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )

                await process.communicate()

                if process.returncode == 0 and os.path.exists(tmp_file.name):
                    with open(tmp_file.name, "rb") as f:
                        image_data = f.read()
                    return await self._resize_if_needed(image_data)
                else:
                    logger.warning(
                        "scrot capture failed", returncode=process.returncode
                    )
                    return None

            finally:
                # Clean up temporary file
                if os.path.exists(tmp_file.name):
                    os.unlink(tmp_file.name)

    async def _capture_with_gnome_screenshot(self) -> bytes | None:
        """Capture screen using gnome-screenshot."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
            try:
                cmd = ["gnome-screenshot", "--file", tmp_file.name]

                process = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )

                await process.communicate()

                if process.returncode == 0 and os.path.exists(tmp_file.name):
                    with open(tmp_file.name, "rb") as f:
                        image_data = f.read()
                    return await self._resize_if_needed(image_data)
                else:
                    logger.warning(
                        "gnome-screenshot capture failed", returncode=process.returncode
                    )
                    return None

            finally:
                if os.path.exists(tmp_file.name):
                    os.unlink(tmp_file.name)

    async def _capture_with_imagemagick(self) -> bytes | None:
        """Capture screen using ImageMagick's import command."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
            try:
                cmd = [
                    "import",
                    "-window",
                    "root",
                    "-quality",
                    str(self.quality),
                    tmp_file.name,
                ]

                process = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )

                await process.communicate()

                if process.returncode == 0 and os.path.exists(tmp_file.name):
                    with open(tmp_file.name, "rb") as f:
                        image_data = f.read()
                    return await self._resize_if_needed(image_data)
                else:
                    logger.warning(
                        "ImageMagick import capture failed",
                        returncode=process.returncode,
                    )
                    return None

            finally:
                if os.path.exists(tmp_file.name):
                    os.unlink(tmp_file.name)

    async def _capture_with_xwd(self) -> bytes | None:
        """Capture screen using xwd and convert to PNG."""
        with tempfile.NamedTemporaryFile(suffix=".xwd", delete=False) as xwd_file:
            try:
                # Capture with xwd
                cmd = ["xwd", "-root", "-out", xwd_file.name]

                process = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )

                await process.communicate()

                if process.returncode != 0:
                    logger.warning("xwd capture failed", returncode=process.returncode)
                    return None

                # Convert to PNG using convert (ImageMagick)
                with tempfile.NamedTemporaryFile(
                    suffix=".png", delete=False
                ) as png_file:
                    try:
                        convert_cmd = ["convert", xwd_file.name, png_file.name]

                        convert_process = await asyncio.create_subprocess_exec(
                            *convert_cmd,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                        )

                        await convert_process.communicate()

                        if convert_process.returncode == 0 and os.path.exists(
                            png_file.name
                        ):
                            with open(png_file.name, "rb") as f:
                                image_data = f.read()
                            return await self._resize_if_needed(image_data)
                        else:
                            logger.warning(
                                "xwd to PNG conversion failed",
                                returncode=convert_process.returncode,
                            )
                            return None

                    finally:
                        if os.path.exists(png_file.name):
                            os.unlink(png_file.name)

            finally:
                if os.path.exists(xwd_file.name):
                    os.unlink(xwd_file.name)

    async def _resize_if_needed(self, image_data: bytes) -> bytes:
        """Resize image if it exceeds maximum dimensions."""
        try:
            from PIL import Image

            # Load image
            img = Image.open(io.BytesIO(image_data))
            original_size = img.size

            # Check if resize is needed
            if img.width <= self.max_width and img.height <= self.max_height:
                return image_data

            # Calculate new size maintaining aspect ratio
            ratio = min(self.max_width / img.width, self.max_height / img.height)
            new_size = (int(img.width * ratio), int(img.height * ratio))

            # Resize image
            resized_img = img.resize(new_size, Image.Resampling.LANCZOS)

            # Convert back to bytes
            buffer = io.BytesIO()
            resized_img.save(buffer, format="PNG", quality=self.quality)

            logger.debug(
                "Image resized", original_size=original_size, new_size=new_size
            )

            return buffer.getvalue()

        except ImportError:
            logger.warning("PIL not available, cannot resize image")
            return image_data
        except Exception as e:
            logger.error("Error resizing image", error=str(e))
            return image_data

    async def send_data_batch(self, data_batch: list[dict[str, Any]]) -> bool:
        """Send a batch of screen capture data."""
        try:
            success_count = 0

            for capture_data in data_batch:
                # Convert hex back to bytes
                image_bytes = bytes.fromhex(capture_data["image_data"])

                success = await self.api_client.send_screen_capture(
                    image_bytes, capture_data["metadata"]
                )

                if success:
                    success_count += 1

            # Consider successful if at least 70% of captures were sent
            return success_count >= len(data_batch) * 0.7

        except Exception as e:
            logger.error("Error sending screen capture batch", error=str(e))
            return False

    async def cleanup(self) -> None:
        """Cleanup screen collector resources."""
        logger.info("Screen collector cleaned up")

    async def get_status(self) -> dict[str, Any]:
        """Get screen collector status."""
        base_status = await super().get_status()
        base_status.update(
            {
                "display_available": self._display_available,
                "capture_method": self._capture_method,
                "quality": self.quality,
                "max_width": self.max_width,
                "max_height": self.max_height,
            }
        )
        return base_status
