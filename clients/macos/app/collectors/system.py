"""System metrics collector for macOS."""

import platform
from datetime import datetime
from typing import Any

import psutil
import structlog

from app.collectors import BaseCollector

logger = structlog.get_logger(__name__)


class SystemCollector(BaseCollector):
    """Collects system metrics and performance data."""

    def __init__(self, api_client, interval: int):
        super().__init__(api_client, interval)
        self._system_info = None

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
            }

            logger.info(
                "System collector initialized",
                hostname=self._system_info["hostname"],
                cpu_count=self._system_info["cpu_count"],
            )

            self._initialized = True

        except Exception as e:
            logger.error("Failed to initialize system collector", error=str(e))
            raise

    async def collect(self) -> bool:
        """Collect system metrics."""
        if not self._initialized:
            logger.warning("System collector not initialized")
            return False

        try:
            logger.debug("Collecting system metrics")

            # Collect dynamic system metrics
            metrics = await self._collect_system_metrics()

            # Send to API
            success = await self.api_client.send_system_metrics(metrics)

            if success:
                self._collection_count += 1
                self._last_collection = datetime.utcnow().isoformat()
                logger.debug("System metrics collected and sent")
            else:
                self._error_count += 1
                logger.error("Failed to send system metrics")

            return success

        except Exception as e:
            self._error_count += 1
            logger.error("Error collecting system metrics", error=str(e))
            return False

    async def _collect_system_metrics(self) -> dict[str, Any]:
        """Collect current system metrics."""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_times = psutil.cpu_times()
            cpu_freq = psutil.cpu_freq()

            # Memory metrics
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()

            # Disk metrics
            disk_usage = psutil.disk_usage("/")
            disk_io = psutil.disk_io_counters()

            # Network metrics
            network_io = psutil.net_io_counters()
            network_connections = len(psutil.net_connections())

            # Process metrics
            processes = list(
                psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"])
            )
            process_count = len(processes)

            # Battery metrics (if available)
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
            except:
                pass

            # Temperature sensors (if available)
            temperatures = {}
            try:
                temps = psutil.sensors_temperatures()
                for name, entries in temps.items():
                    temperatures[name] = [
                        {"label": entry.label, "current": entry.current}
                        for entry in entries
                    ]
            except:
                pass

            # Load average (Unix-like systems)
            load_avg = None
            try:
                load_avg = psutil.getloadavg()
            except:
                pass

            metrics = {
                "timestamp": datetime.utcnow().isoformat(),
                "static_info": self._system_info,
                "cpu": {
                    "percent": cpu_percent,
                    "times": {
                        "user": cpu_times.user,
                        "system": cpu_times.system,
                        "idle": cpu_times.idle,
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
                    "load_average": load_avg,
                },
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used,
                    "free": memory.free,
                    "active": getattr(memory, "active", None),
                    "inactive": getattr(memory, "inactive", None),
                    "wired": getattr(memory, "wired", None),  # macOS specific
                },
                "swap": {
                    "total": swap.total,
                    "used": swap.used,
                    "free": swap.free,
                    "percent": swap.percent,
                },
                "disk": {
                    "usage": {
                        "total": disk_usage.total,
                        "used": disk_usage.used,
                        "free": disk_usage.free,
                        "percent": (disk_usage.used / disk_usage.total) * 100,
                    },
                    "io": (
                        {
                            "read_count": disk_io.read_count if disk_io else None,
                            "write_count": disk_io.write_count if disk_io else None,
                            "read_bytes": disk_io.read_bytes if disk_io else None,
                            "write_bytes": disk_io.write_bytes if disk_io else None,
                        }
                        if disk_io
                        else None
                    ),
                },
                "network": {
                    "io": {
                        "bytes_sent": network_io.bytes_sent,
                        "bytes_recv": network_io.bytes_recv,
                        "packets_sent": network_io.packets_sent,
                        "packets_recv": network_io.packets_recv,
                    },
                    "connections_count": network_connections,
                },
                "processes": {
                    "count": process_count,
                    "top_cpu": sorted(
                        [p.info for p in processes if p.info["cpu_percent"] > 0],
                        key=lambda x: x["cpu_percent"],
                        reverse=True,
                    )[:10],  # Top 10 CPU consumers
                    "top_memory": sorted(
                        [p.info for p in processes if p.info["memory_percent"] > 0],
                        key=lambda x: x["memory_percent"],
                        reverse=True,
                    )[:10],  # Top 10 memory consumers
                },
                "battery": battery,
                "temperatures": temperatures,
            }

            return metrics

        except Exception as e:
            logger.error("Error collecting system metrics", error=str(e))
            return {}

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
                }
            )
        return base_status
