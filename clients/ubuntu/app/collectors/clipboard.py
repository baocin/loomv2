"""Clipboard monitoring collector for Ubuntu/Linux."""

import hashlib
import subprocess
from datetime import datetime
from typing import Any

import structlog

from app.collectors import BaseCollector

logger = structlog.get_logger(__name__)


class ClipboardCollector(BaseCollector):
    """Monitors clipboard changes for Ubuntu/Linux."""

    def __init__(
        self,
        api_client,
        poll_interval: float,
        send_interval: float,
        max_content_length: int = 10000,
    ):
        super().__init__(api_client, poll_interval, send_interval)
        self.max_content_length = max_content_length
        self._clipboard_tools = []
        self._last_clipboard_hash = None
        self._x11_available = False
        self._wayland_available = False

    async def initialize(self) -> None:
        """Initialize the clipboard collector."""
        try:
            # Check for available clipboard tools
            await self._check_clipboard_tools()

            logger.info(
                "Clipboard collector initialized",
                available_tools=self._clipboard_tools,
                x11_available=self._x11_available,
                wayland_available=self._wayland_available,
                max_content_length=self.max_content_length,
            )

            self._initialized = True

        except Exception as e:
            logger.error("Failed to initialize clipboard collector", error=str(e))
            raise

    async def _check_clipboard_tools(self) -> None:
        """Check for available clipboard tools."""
        import os

        # Check display server type
        if os.environ.get("DISPLAY"):
            self._x11_available = True
        if os.environ.get("WAYLAND_DISPLAY"):
            self._wayland_available = True

        # Test clipboard tools
        clipboard_tools = [
            "xclip",  # X11 clipboard tool
            "xsel",  # Alternative X11 clipboard tool
            "wl-paste",  # Wayland clipboard tool
            "pbpaste",  # macOS (if running on Mac)
        ]

        for tool in clipboard_tools:
            try:
                result = subprocess.run(["which", tool], capture_output=True, timeout=5)

                if result.returncode == 0:
                    self._clipboard_tools.append(tool)
                    logger.info(f"Found clipboard tool: {tool}")

            except Exception:
                continue

        if not self._clipboard_tools:
            logger.warning("No clipboard tools found")

    async def poll_data(self) -> dict[str, Any] | None:
        """Poll clipboard for changes."""
        if not self._clipboard_tools:
            logger.debug("No clipboard tools available, skipping poll")
            return None

        try:
            # Get current clipboard content
            clipboard_data = await self._get_clipboard_content()

            if not clipboard_data:
                return None

            # Check if clipboard has changed
            current_hash = self._calculate_content_hash(
                clipboard_data.get("content", "")
            )

            if current_hash == self._last_clipboard_hash:
                # No change, don't return data
                return None

            # Update hash for next comparison
            self._last_clipboard_hash = current_hash

            return {
                "clipboard_data": clipboard_data,
                "content_hash": current_hash,
                "change_detected": True,
            }

        except Exception as e:
            logger.error("Error polling clipboard data", error=str(e))
            return None

    async def _get_clipboard_content(self) -> dict[str, Any] | None:
        """Get current clipboard content using available tools."""

        # Try different clipboard tools based on availability and display server
        if self._x11_available:
            for tool in ["xclip", "xsel"]:
                if tool in self._clipboard_tools:
                    content = await self._get_clipboard_with_tool(tool)
                    if content is not None:
                        return content

        if self._wayland_available:
            if "wl-paste" in self._clipboard_tools:
                content = await self._get_clipboard_with_tool("wl-paste")
                if content is not None:
                    return content

        # Try any available tool as fallback
        for tool in self._clipboard_tools:
            content = await self._get_clipboard_with_tool(tool)
            if content is not None:
                return content

        return None

    async def _get_clipboard_with_tool(self, tool: str) -> dict[str, Any] | None:
        """Get clipboard content using a specific tool."""
        try:
            if tool == "xclip":
                # Try different clipboard selections
                for selection in ["clipboard", "primary", "secondary"]:
                    try:
                        result = subprocess.run(
                            ["xclip", "-selection", selection, "-o"],
                            capture_output=True,
                            text=True,
                            timeout=5,
                        )

                        if result.returncode == 0 and result.stdout:
                            return self._process_clipboard_content(
                                result.stdout, tool, selection
                            )
                    except Exception:
                        continue

            elif tool == "xsel":
                # Try different clipboard buffers
                for clipboard_type in ["--clipboard", "--primary", "--secondary"]:
                    try:
                        result = subprocess.run(
                            ["xsel", clipboard_type, "--output"],
                            capture_output=True,
                            text=True,
                            timeout=5,
                        )

                        if result.returncode == 0 and result.stdout:
                            return self._process_clipboard_content(
                                result.stdout, tool, clipboard_type
                            )
                    except Exception:
                        continue

            elif tool == "wl-paste":
                try:
                    # Get text content
                    result = subprocess.run(
                        ["wl-paste", "--no-newline"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )

                    if result.returncode == 0 and result.stdout:
                        return self._process_clipboard_content(
                            result.stdout, tool, "clipboard"
                        )
                except Exception:
                    pass

            elif tool == "pbpaste":  # macOS
                try:
                    result = subprocess.run(
                        ["pbpaste"], capture_output=True, text=True, timeout=5
                    )

                    if result.returncode == 0 and result.stdout:
                        return self._process_clipboard_content(
                            result.stdout, tool, "general"
                        )
                except Exception:
                    pass

            return None

        except Exception as e:
            logger.error(f"Error getting clipboard with {tool}", error=str(e))
            return None

    def _process_clipboard_content(
        self, content: str, tool: str, selection: str
    ) -> dict[str, Any]:
        """Process and format clipboard content."""
        # Truncate content if too long
        original_length = len(content)
        if len(content) > self.max_content_length:
            content = content[: self.max_content_length]
            truncated = True
        else:
            truncated = False

        # Analyze content type
        content_type = self._analyze_content_type(content)

        # Check for sensitive content patterns
        is_sensitive = self._check_sensitive_content(content)

        return {
            "content": content if not is_sensitive else "[SENSITIVE CONTENT DETECTED]",
            "original_length": original_length,
            "truncated": truncated,
            "content_type": content_type,
            "tool_used": tool,
            "selection": selection,
            "is_sensitive": is_sensitive,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _analyze_content_type(self, content: str) -> str:
        """Analyze the type of clipboard content."""
        content_lower = content.lower().strip()

        # URL patterns
        if content.startswith(("http://", "https://", "ftp://")) or "www." in content:
            return "url"

        # Email patterns
        if "@" in content and "." in content and len(content.split()) == 1:
            return "email"

        # File path patterns
        if content.startswith("/") or content.startswith("~/") or "\\" in content:
            return "file_path"

        # Code patterns
        if any(
            lang in content_lower
            for lang in [
                "def ",
                "function ",
                "import ",
                "from ",
                "class ",
                "var ",
                "let ",
                "const ",
            ]
        ):
            return "code"

        # JSON/XML patterns
        if (content.strip().startswith("{") and content.strip().endswith("}")) or (
            content.strip().startswith("[") and content.strip().endswith("]")
        ):
            return "json"

        if content.strip().startswith("<") and content.strip().endswith(">"):
            return "xml_html"

        # Number patterns
        try:
            float(content.strip())
            return "number"
        except ValueError:
            pass

        # Multi-line text
        if "\n" in content:
            return "multiline_text"

        # Default
        return "text"

    def _check_sensitive_content(self, content: str) -> bool:
        """Check if content contains potentially sensitive information."""
        content_lower = content.lower()

        # Common sensitive patterns
        sensitive_patterns = [
            "password",
            "passwd",
            "pwd",
            "secret",
            "key",
            "token",
            "credit card",
            "ssn",
            "social security",
            "api_key",
            "api-key",
            "apikey",
            "private key",
            "private_key",
            "oauth",
            "bearer",
            "username:",
            "password:",
            "login:",
            "auth:",
        ]

        for pattern in sensitive_patterns:
            if pattern in content_lower:
                return True

        # Credit card number pattern (simple check)
        import re

        if re.search(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b", content):
            return True

        # Email + password pattern
        if "@" in content and any(
            p in content_lower for p in ["password", "pass", "pwd"]
        ):
            return True

        return False

    def _calculate_content_hash(self, content: str) -> str:
        """Calculate hash of content for change detection."""
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    async def send_data_batch(self, data_batch: list[dict[str, Any]]) -> bool:
        """Send a batch of clipboard data."""
        try:
            success_count = 0

            for clipboard_data in data_batch:
                success = await self.api_client.send_clipboard_data(
                    clipboard_data["clipboard_data"],
                    {
                        "content_hash": clipboard_data["content_hash"],
                        "change_detected": clipboard_data["change_detected"],
                    },
                )

                if success:
                    success_count += 1

            # Consider successful if at least 80% of clipboard data was sent
            return success_count >= len(data_batch) * 0.8

        except Exception as e:
            logger.error("Error sending clipboard data batch", error=str(e))
            return False

    async def cleanup(self) -> None:
        """Cleanup clipboard collector resources."""
        logger.info("Clipboard collector cleaned up")

    async def get_status(self) -> dict[str, Any]:
        """Get clipboard collector status."""
        base_status = await super().get_status()
        base_status.update(
            {
                "available_tools": self._clipboard_tools,
                "x11_available": self._x11_available,
                "wayland_available": self._wayland_available,
                "max_content_length": self.max_content_length,
                "last_hash": self._last_clipboard_hash,
            }
        )
        return base_status
