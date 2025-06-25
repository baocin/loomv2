"""System metrics collector for Ubuntu/Linux."""

import os
import platform
from datetime import datetime
from typing import Any

import psutil
import structlog

from app.collectors import BaseCollector

logger = structlog.get_logger(__name__)


class SystemCollector(BaseCollector):
    """Collects system metrics and performance data for Ubuntu."""

    def __init__(self, api_client, poll_interval: float, send_interval: float):
        super().__init__(api_client, poll_interval, send_interval)
        self._system_info = None
        self._last_network_io = None
        self._last_disk_io = None

    async def initialize(self) -> None:
        """Initialize the system collector."""
        try:
            # Gather static system information
            self._system_info = {
                "platform": platform.platform(),
                "processor": platform.processor(),
                "architecture": platform.architecture(),
                "hostname": platform.node(),
                "python_version": platform.python_version(),
                "cpu_count": psutil.cpu_count(),
                "cpu_count_logical": psutil.cpu_count(logical=True),
                "memory_total": psutil.virtual_memory().total,
                "boot_time": psutil.boot_time(),
                "linux_distribution": self._get_linux_distribution(),
            }

            # Initialize baseline readings for delta calculations
            self._last_network_io = psutil.net_io_counters()
            self._last_disk_io = psutil.disk_io_counters()

            logger.info(
                "System collector initialized",
                hostname=self._system_info["hostname"],
                cpu_count=self._system_info["cpu_count"],
                distribution=self._system_info["linux_distribution"],
            )

            self._initialized = True

        except Exception as e:
            logger.error("Failed to initialize system collector", error=str(e))
            raise

    def _get_linux_distribution(self) -> dict[str, str]:
        """Get Linux distribution information."""
        try:
            # Try to read /etc/os-release
            os_info = {}
            if os.path.exists("/etc/os-release"):
                with open("/etc/os-release") as f:
                    for line in f:
                        if "=" in line:
                            key, value = line.strip().split("=", 1)
                            os_info[key] = value.strip('"')

            return {
                "name": os_info.get("NAME", "Unknown"),
                "version": os_info.get("VERSION", "Unknown"),
                "id": os_info.get("ID", "Unknown"),
                "version_id": os_info.get("VERSION_ID", "Unknown"),
            }
        except Exception as e:
            logger.warning("Could not determine Linux distribution", error=str(e))
            return {
                "name": "Unknown",
                "version": "Unknown",
                "id": "unknown",
                "version_id": "unknown",
            }

    async def poll_data(self) -> dict[str, Any] | None:
        """Poll current system metrics."""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=None)  # Non-blocking
            cpu_times = psutil.cpu_times()
            cpu_freq = psutil.cpu_freq()

            # Memory metrics
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()

            # Disk metrics
            disk_usage = psutil.disk_usage("/")
            current_disk_io = psutil.disk_io_counters()

            # Calculate disk I/O deltas
            disk_io_delta = {}
            if self._last_disk_io and current_disk_io:
                disk_io_delta = {
                    "read_bytes_delta": current_disk_io.read_bytes
                    - self._last_disk_io.read_bytes,
                    "write_bytes_delta": current_disk_io.write_bytes
                    - self._last_disk_io.write_bytes,
                    "read_count_delta": current_disk_io.read_count
                    - self._last_disk_io.read_count,
                    "write_count_delta": current_disk_io.write_count
                    - self._last_disk_io.write_count,
                }
                self._last_disk_io = current_disk_io

            # Network metrics
            current_network_io = psutil.net_io_counters()
            network_connections = len(psutil.net_connections())

            # Calculate network I/O deltas
            network_io_delta = {}
            if self._last_network_io and current_network_io:
                network_io_delta = {
                    "bytes_sent_delta": current_network_io.bytes_sent
                    - self._last_network_io.bytes_sent,
                    "bytes_recv_delta": current_network_io.bytes_recv
                    - self._last_network_io.bytes_recv,
                    "packets_sent_delta": current_network_io.packets_sent
                    - self._last_network_io.packets_sent,
                    "packets_recv_delta": current_network_io.packets_recv
                    - self._last_network_io.packets_recv,
                }
                self._last_network_io = current_network_io

            # Load average (Linux specific)
            load_avg = os.getloadavg()

            # Temperature sensors (if available)
            temperatures = {}
            try:
                temps = psutil.sensors_temperatures()
                for name, entries in temps.items():
                    temperatures[name] = [
                        {
                            "label": entry.label,
                            "current": entry.current,
                            "high": entry.high,
                            "critical": entry.critical,
                        }
                        for entry in entries
                    ]
            except Exception:
                pass

            # Battery information (for laptops)
            battery = None
            try:
                battery_info = psutil.sensors_battery()
                if battery_info:
                    battery = {
                        "percent": battery_info.percent,
                        "power_plugged": battery_info.power_plugged,
                        "seconds_left": (
                            battery_info.secsleft
                            if battery_info.secsleft != psutil.POWER_TIME_UNLIMITED
                            else None
                        ),
                    }
            except Exception:
                pass

            # Process information (top processes)
            processes = list(
                psutil.process_iter(
                    ["pid", "name", "cpu_percent", "memory_percent", "status"]
                )
            )

            # User and session information
            users = psutil.users()

            metrics = {
                "timestamp": datetime.utcnow().isoformat(),
                "cpu": {
                    "percent": cpu_percent,
                    "times": {
                        "user": cpu_times.user,
                        "system": cpu_times.system,
                        "idle": cpu_times.idle,
                        "iowait": getattr(cpu_times, "iowait", None),
                        "irq": getattr(cpu_times, "irq", None),
                        "softirq": getattr(cpu_times, "softirq", None),
                        "steal": getattr(cpu_times, "steal", None),
                        "guest": getattr(cpu_times, "guest", None),
                    },
                    "frequency": (
                        {
                            "current": cpu_freq.current if cpu_freq else None,
                            "min": cpu_freq.min if cpu_freq else None,
                            "max": cpu_freq.max if cpu_freq else None,
                        }
                        if cpu_freq
                        else None
                    ),
                    "load_average": {
                        "1min": load_avg[0],
                        "5min": load_avg[1],
                        "15min": load_avg[2],
                    },
                },
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used,
                    "free": memory.free,
                    "active": getattr(memory, "active", None),
                    "inactive": getattr(memory, "inactive", None),
                    "buffers": getattr(memory, "buffers", None),
                    "cached": getattr(memory, "cached", None),
                    "shared": getattr(memory, "shared", None),
                },
                "swap": {
                    "total": swap.total,
                    "used": swap.used,
                    "free": swap.free,
                    "percent": swap.percent,
                    "sin": getattr(swap, "sin", None),
                    "sout": getattr(swap, "sout", None),
                },
                "disk": {
                    "usage": {
                        "total": disk_usage.total,
                        "used": disk_usage.used,
                        "free": disk_usage.free,
                        "percent": (disk_usage.used / disk_usage.total) * 100,
                    },
                    "io": {
                        "read_count": (
                            current_disk_io.read_count if current_disk_io else None
                        ),
                        "write_count": (
                            current_disk_io.write_count if current_disk_io else None
                        ),
                        "read_bytes": (
                            current_disk_io.read_bytes if current_disk_io else None
                        ),
                        "write_bytes": (
                            current_disk_io.write_bytes if current_disk_io else None
                        ),
                        **disk_io_delta,
                    },
                },
                "network": {
                    "io": {
                        "bytes_sent": current_network_io.bytes_sent,
                        "bytes_recv": current_network_io.bytes_recv,
                        "packets_sent": current_network_io.packets_sent,
                        "packets_recv": current_network_io.packets_recv,
                        **network_io_delta,
                    },
                    "connections_count": network_connections,
                },
                "processes": {
                    "count": len(processes),
                    "top_cpu": sorted(
                        [
                            p.info
                            for p in processes
                            if p.info["cpu_percent"] and p.info["cpu_percent"] > 0
                        ],
                        key=lambda x: x["cpu_percent"],
                        reverse=True,
                    )[:10],
                    "top_memory": sorted(
                        [
                            p.info
                            for p in processes
                            if p.info["memory_percent"] and p.info["memory_percent"] > 0
                        ],
                        key=lambda x: x["memory_percent"],
                        reverse=True,
                    )[:10],
                },
                "users": [
                    {
                        "name": user.name,
                        "terminal": user.terminal,
                        "host": user.host,
                        "started": user.started,
                    }
                    for user in users
                ],
                "battery": battery,
                "temperatures": temperatures,
            }

            return metrics

        except Exception as e:
            logger.error("Error polling system metrics", error=str(e))
            return None

    async def send_data_batch(self, data_batch: list[dict[str, Any]]) -> bool:
        """Send a batch of system metrics."""
        try:
            # Send each metric as a generic sensor reading
            success_count = 0

            for metrics in data_batch:
                success = await self.api_client.send_sensor_data(
                    "generic",
                    {
                        "sensor_type": "system_metrics",
                        "value": metrics["cpu"][
                            "percent"
                        ],  # Use CPU percentage as primary value
                        "unit": "percent",
                        "readings": {"static_info": self._system_info, **metrics},
                    },
                )

                if success:
                    success_count += 1

            # Consider successful if at least 50% of readings were sent
            return success_count >= len(data_batch) * 0.5

        except Exception as e:
            logger.error("Error sending system metrics batch", error=str(e))
            return False

    async def cleanup(self) -> None:
        """Cleanup system collector resources."""
        logger.info("System collector cleaned up")

    async def get_status(self) -> dict[str, Any]:
        """Get system collector status."""
        base_status = await super().get_status()
        if self._system_info:
            base_status.update(
                {
                    "hostname": self._system_info.get("hostname"),
                    "cpu_count": self._system_info.get("cpu_count"),
                    "memory_total_gb": round(
                        self._system_info.get("memory_total", 0) / (1024**3), 2
                    ),
                    "distribution": self._system_info.get("linux_distribution"),
                }
            )
        return base_status
