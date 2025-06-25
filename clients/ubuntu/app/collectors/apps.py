"""Application monitoring collector for Ubuntu/Linux."""

import json
import subprocess
from typing import Any

import structlog

from app.collectors import BaseCollector

logger = structlog.get_logger(__name__)


class AppsCollector(BaseCollector):
    """Collects active application and window information for Ubuntu."""

    def __init__(self, api_client, poll_interval: float, send_interval: float):
        super().__init__(api_client, poll_interval, send_interval)
        self._x11_available = False
        self._wayland_available = False
        self._display_server = None

    async def initialize(self) -> None:
        """Initialize the apps collector."""
        try:
            # Check for available display servers
            await self._check_display_server()

            logger.info(
                "Apps collector initialized",
                display_server=self._display_server,
                x11_available=self._x11_available,
                wayland_available=self._wayland_available,
            )

            self._initialized = True

        except Exception as e:
            logger.error("Failed to initialize apps collector", error=str(e))
            raise

    async def _check_display_server(self) -> None:
        """Check for available display servers and tools."""
        import os

        # Check for X11
        if os.environ.get("DISPLAY"):
            try:
                # Test if xdotool or wmctrl is available
                for tool in ["xdotool", "wmctrl"]:
                    result = subprocess.run(
                        ["which", tool], capture_output=True, timeout=5
                    )
                    if result.returncode == 0:
                        self._x11_available = True
                        self._display_server = "x11"
                        logger.info(f"Found X11 tool: {tool}")
                        break
            except Exception:
                pass

        # Check for Wayland
        if os.environ.get("WAYLAND_DISPLAY"):
            try:
                # Test if swaymsg is available (for Sway compositor)
                result = subprocess.run(
                    ["which", "swaymsg"], capture_output=True, timeout=5
                )
                if result.returncode == 0:
                    self._wayland_available = True
                    if not self._display_server:
                        self._display_server = "wayland"
                    logger.info("Found Wayland tool: swaymsg")
            except Exception:
                pass

        if not self._x11_available and not self._wayland_available:
            logger.warning("No supported display server tools found")

    async def poll_data(self) -> dict[str, Any] | None:
        """Poll current application and window data."""
        try:
            apps_data = {}

            # Get active processes
            processes = await self._get_running_processes()
            apps_data["processes"] = processes

            # Get window information based on display server
            if self._x11_available:
                windows = await self._get_x11_windows()
                apps_data["windows"] = windows
                active_window = await self._get_active_x11_window()
                apps_data["active_window"] = active_window

            elif self._wayland_available:
                windows = await self._get_wayland_windows()
                apps_data["windows"] = windows

            # Get desktop environment info
            desktop_info = await self._get_desktop_environment()
            apps_data["desktop_environment"] = desktop_info

            return {"display_server": self._display_server, "apps_data": apps_data}

        except Exception as e:
            logger.error("Error polling apps data", error=str(e))
            return None

    async def _get_running_processes(self) -> list[dict[str, Any]]:
        """Get list of running GUI applications."""
        try:
            # Use ps to get processes with command lines
            result = subprocess.run(
                ["ps", "axo", "pid,ppid,pcpu,pmem,etime,comm,cmd"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return []

            processes = []
            lines = result.stdout.strip().split("\n")[1:]  # Skip header

            for line in lines:
                parts = line.strip().split(None, 6)
                if len(parts) >= 6:
                    try:
                        process_info = {
                            "pid": int(parts[0]),
                            "ppid": int(parts[1]),
                            "cpu_percent": float(parts[2]),
                            "memory_percent": float(parts[3]),
                            "elapsed_time": parts[4],
                            "command": parts[5],
                            "full_command": parts[6] if len(parts) > 6 else parts[5],
                        }

                        # Filter for likely GUI applications
                        if self._is_gui_process(process_info):
                            processes.append(process_info)

                    except (ValueError, IndexError):
                        continue

            return processes

        except Exception as e:
            logger.error("Error getting running processes", error=str(e))
            return []

    def _is_gui_process(self, process_info: dict[str, Any]) -> bool:
        """Determine if a process is likely a GUI application."""
        command = process_info.get("command", "").lower()
        full_command = process_info.get("full_command", "").lower()

        # Common GUI application patterns
        gui_patterns = [
            "firefox",
            "chrome",
            "chromium",
            "opera",
            "brave",
            "code",
            "atom",
            "sublime",
            "gedit",
            "vim",
            "emacs",
            "libreoffice",
            "gimp",
            "inkscape",
            "blender",
            "nautilus",
            "dolphin",
            "thunar",
            "nemo",
            "terminal",
            "gnome-terminal",
            "konsole",
            "xterm",
            "discord",
            "slack",
            "teams",
            "zoom",
            "skype",
            "spotify",
            "vlc",
            "mpv",
            "rhythmbox",
            "calculator",
            "gnome-calculator",
        ]

        # System processes to exclude
        exclude_patterns = [
            "kernel",
            "kthread",
            "[",
            "systemd",
            "dbus",
            "pulseaudio",
            "NetworkManager",
            "wpa_supplicant",
        ]

        # Check exclusions first
        for pattern in exclude_patterns:
            if pattern in command or pattern in full_command:
                return False

        # Check for GUI patterns
        for pattern in gui_patterns:
            if pattern in command or pattern in full_command:
                return True

        # Additional heuristics
        if any(term in full_command for term in ["--display", "DISPLAY=", "gtk", "qt"]):
            return True

        return False

    async def _get_x11_windows(self) -> list[dict[str, Any]]:
        """Get window information using X11 tools."""
        try:
            # Try wmctrl first
            result = subprocess.run(
                ["wmctrl", "-lp"], capture_output=True, text=True, timeout=5
            )

            if result.returncode == 0:
                return self._parse_wmctrl_output(result.stdout)

            # Fallback to xdotool
            result = subprocess.run(
                ["xdotool", "search", "--onlyvisible", "--name", ".*"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                return await self._parse_xdotool_output(result.stdout)

        except Exception as e:
            logger.error("Error getting X11 windows", error=str(e))

        return []

    def _parse_wmctrl_output(self, output: str) -> list[dict[str, Any]]:
        """Parse wmctrl -lp output."""
        windows = []

        for line in output.strip().split("\n"):
            if not line.strip():
                continue

            parts = line.split(None, 4)
            if len(parts) >= 5:
                try:
                    window_info = {
                        "window_id": parts[0],
                        "desktop": int(parts[1]),
                        "pid": int(parts[2]),
                        "hostname": parts[3],
                        "title": parts[4],
                    }
                    windows.append(window_info)
                except (ValueError, IndexError):
                    continue

        return windows

    async def _parse_xdotool_output(self, output: str) -> list[dict[str, Any]]:
        """Parse xdotool search output and get window details."""
        windows = []

        for window_id in output.strip().split("\n"):
            if not window_id.strip():
                continue

            try:
                # Get window name
                name_result = subprocess.run(
                    ["xdotool", "getwindowname", window_id],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )

                # Get window PID
                pid_result = subprocess.run(
                    ["xdotool", "getwindowpid", window_id],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )

                window_info = {
                    "window_id": window_id,
                    "title": (
                        name_result.stdout.strip()
                        if name_result.returncode == 0
                        else "Unknown"
                    ),
                    "pid": (
                        int(pid_result.stdout.strip())
                        if pid_result.returncode == 0
                        else None
                    ),
                }

                windows.append(window_info)

            except Exception:
                continue

        return windows

    async def _get_active_x11_window(self) -> dict[str, Any] | None:
        """Get currently active window information."""
        try:
            # Get active window ID
            result = subprocess.run(
                ["xdotool", "getactivewindow"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode != 0:
                return None

            window_id = result.stdout.strip()

            # Get window details
            name_result = subprocess.run(
                ["xdotool", "getwindowname", window_id],
                capture_output=True,
                text=True,
                timeout=2,
            )

            pid_result = subprocess.run(
                ["xdotool", "getwindowpid", window_id],
                capture_output=True,
                text=True,
                timeout=2,
            )

            return {
                "window_id": window_id,
                "title": (
                    name_result.stdout.strip()
                    if name_result.returncode == 0
                    else "Unknown"
                ),
                "pid": (
                    int(pid_result.stdout.strip())
                    if pid_result.returncode == 0
                    else None
                ),
            }

        except Exception as e:
            logger.error("Error getting active X11 window", error=str(e))
            return None

    async def _get_wayland_windows(self) -> list[dict[str, Any]]:
        """Get window information for Wayland (Sway compositor)."""
        try:
            result = subprocess.run(
                ["swaymsg", "-t", "get_tree"], capture_output=True, text=True, timeout=5
            )

            if result.returncode != 0:
                return []

            tree = json.loads(result.stdout)
            windows = []

            def extract_windows(node):
                if node.get("type") == "con" and node.get("name"):
                    windows.append(
                        {
                            "id": node.get("id"),
                            "name": node.get("name"),
                            "app_id": node.get("app_id"),
                            "pid": node.get("pid"),
                            "focused": node.get("focused", False),
                        }
                    )

                for child in node.get("nodes", []):
                    extract_windows(child)
                for child in node.get("floating_nodes", []):
                    extract_windows(child)

            extract_windows(tree)
            return windows

        except Exception as e:
            logger.error("Error getting Wayland windows", error=str(e))
            return []

    async def _get_desktop_environment(self) -> dict[str, Any]:
        """Get desktop environment information."""
        import os

        desktop_info = {
            "session_type": os.environ.get("XDG_SESSION_TYPE"),
            "current_desktop": os.environ.get("XDG_CURRENT_DESKTOP"),
            "session_desktop": os.environ.get("XDG_SESSION_DESKTOP"),
            "desktop_session": os.environ.get("DESKTOP_SESSION"),
            "gdmsession": os.environ.get("GDMSESSION"),
        }

        return {k: v for k, v in desktop_info.items() if v is not None}

    async def send_data_batch(self, data_batch: list[dict[str, Any]]) -> bool:
        """Send a batch of apps data."""
        try:
            success_count = 0

            for apps_data in data_batch:
                success = await self.api_client.send_app_monitoring(
                    apps_data["apps_data"],
                    {"display_server": apps_data["display_server"]},
                )

                if success:
                    success_count += 1

            # Consider successful if at least 60% of batches were sent
            return success_count >= len(data_batch) * 0.6

        except Exception as e:
            logger.error("Error sending apps data batch", error=str(e))
            return False

    async def cleanup(self) -> None:
        """Cleanup apps collector resources."""
        logger.info("Apps collector cleaned up")

    async def get_status(self) -> dict[str, Any]:
        """Get apps collector status."""
        base_status = await super().get_status()
        base_status.update(
            {
                "display_server": self._display_server,
                "x11_available": self._x11_available,
                "wayland_available": self._wayland_available,
            }
        )
        return base_status
