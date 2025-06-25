"""Location data collector for Ubuntu/Linux."""

import json
import re
import subprocess
from typing import Any

import structlog

from app.collectors import BaseCollector

logger = structlog.get_logger(__name__)


class LocationCollector(BaseCollector):
    """Collects location data for Ubuntu using various methods."""

    def __init__(self, api_client, poll_interval: float, send_interval: float):
        super().__init__(api_client, poll_interval, send_interval)
        self._geoclue_available = False
        self._networkmanager_available = False
        self._location_methods = []

    async def initialize(self) -> None:
        """Initialize the location collector."""
        try:
            # Check for available location services
            await self._check_location_services()

            logger.info(
                "Location collector initialized",
                geoclue_available=self._geoclue_available,
                networkmanager_available=self._networkmanager_available,
                available_methods=self._location_methods,
            )

            self._initialized = True

        except Exception as e:
            logger.error("Failed to initialize location collector", error=str(e))
            raise

    async def _check_location_services(self) -> None:
        """Check for available location services."""
        # Check for GeoClue2 (GNOME location service)
        try:
            result = subprocess.run(
                ["busctl", "list", "--user"], capture_output=True, text=True, timeout=5
            )

            if result.returncode == 0 and "org.freedesktop.GeoClue2" in result.stdout:
                self._geoclue_available = True
                self._location_methods.append("geoclue2")
                logger.info("GeoClue2 location service available")
        except Exception:
            pass

        # Check for NetworkManager (can provide approximate location via WiFi)
        try:
            result = subprocess.run(["which", "nmcli"], capture_output=True, timeout=5)

            if result.returncode == 0:
                self._networkmanager_available = True
                self._location_methods.append("networkmanager")
                logger.info("NetworkManager available for WiFi-based location")
        except Exception:
            pass

        # Check for GPS utilities
        for gps_tool in ["gpsd", "gpsctl"]:
            try:
                result = subprocess.run(
                    ["which", gps_tool], capture_output=True, timeout=5
                )

                if result.returncode == 0:
                    self._location_methods.append(f"gps_{gps_tool}")
                    logger.info(f"GPS tool available: {gps_tool}")
            except Exception:
                pass

        if not self._location_methods:
            logger.warning("No location services found")

    async def poll_data(self) -> dict[str, Any] | None:
        """Poll location data."""
        if not self._location_methods:
            logger.debug("No location methods available, skipping poll")
            return None

        try:
            location_data = {}

            # Try GeoClue2 first (most accurate)
            if self._geoclue_available:
                geoclue_location = await self._get_geoclue_location()
                if geoclue_location:
                    location_data["geoclue"] = geoclue_location

            # Get WiFi-based location approximation
            if self._networkmanager_available:
                wifi_location = await self._get_wifi_location()
                if wifi_location:
                    location_data["wifi"] = wifi_location

            # Get network interface information
            network_info = await self._get_network_info()
            if network_info:
                location_data["network"] = network_info

            # Get timezone information (can help with location context)
            timezone_info = await self._get_timezone_info()
            if timezone_info:
                location_data["timezone"] = timezone_info

            if location_data:
                return {
                    "location_data": location_data,
                    "methods_used": list(location_data.keys()),
                }

            return None

        except Exception as e:
            logger.error("Error polling location data", error=str(e))
            return None

    async def _get_geoclue_location(self) -> dict[str, Any] | None:
        """Get location from GeoClue2 service."""
        try:
            # Use busctl to query GeoClue2
            result = subprocess.run(
                [
                    "busctl",
                    "call",
                    "--user",
                    "org.freedesktop.GeoClue2",
                    "/org/freedesktop/GeoClue2/Manager",
                    "org.freedesktop.GeoClue2.Manager",
                    "GetClient",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return None

            # Parse the client path from the output
            client_path_match = re.search(
                r'"/org/freedesktop/GeoClue2/Client/\d+"', result.stdout
            )
            if not client_path_match:
                return None

            client_path = client_path_match.group(0).strip('"')

            # Start the client
            subprocess.run(
                [
                    "busctl",
                    "call",
                    "--user",
                    "org.freedesktop.GeoClue2",
                    client_path,
                    "org.freedesktop.GeoClue2.Client",
                    "Start",
                ],
                capture_output=True,
                timeout=5,
            )

            # Get location
            location_result = subprocess.run(
                [
                    "busctl",
                    "get-property",
                    "--user",
                    "org.freedesktop.GeoClue2",
                    client_path,
                    "org.freedesktop.GeoClue2.Client",
                    "Location",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if location_result.returncode == 0 and location_result.stdout.strip():
                # Parse location object path
                location_path_match = re.search(
                    r'"/org/freedesktop/GeoClue2/Location/\d+"', location_result.stdout
                )
                if location_path_match:
                    location_path = location_path_match.group(0).strip('"')

                    # Get latitude
                    lat_result = subprocess.run(
                        [
                            "busctl",
                            "get-property",
                            "--user",
                            "org.freedesktop.GeoClue2",
                            location_path,
                            "org.freedesktop.GeoClue2.Location",
                            "Latitude",
                        ],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )

                    # Get longitude
                    lon_result = subprocess.run(
                        [
                            "busctl",
                            "get-property",
                            "--user",
                            "org.freedesktop.GeoClue2",
                            location_path,
                            "org.freedesktop.GeoClue2.Location",
                            "Longitude",
                        ],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )

                    # Get accuracy
                    acc_result = subprocess.run(
                        [
                            "busctl",
                            "get-property",
                            "--user",
                            "org.freedesktop.GeoClue2",
                            location_path,
                            "org.freedesktop.GeoClue2.Location",
                            "Accuracy",
                        ],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )

                    if lat_result.returncode == 0 and lon_result.returncode == 0:
                        try:
                            # Parse coordinates
                            latitude = float(
                                re.search(r"[-+]?\d*\.?\d+", lat_result.stdout).group()
                            )
                            longitude = float(
                                re.search(r"[-+]?\d*\.?\d+", lon_result.stdout).group()
                            )
                            accuracy = (
                                float(
                                    re.search(r"\d+\.?\d*", acc_result.stdout).group()
                                )
                                if acc_result.returncode == 0
                                else None
                            )

                            return {
                                "latitude": latitude,
                                "longitude": longitude,
                                "accuracy": accuracy,
                                "source": "geoclue2",
                            }
                        except (ValueError, AttributeError):
                            pass

            return None

        except Exception as e:
            logger.error("Error getting GeoClue location", error=str(e))
            return None

    async def _get_wifi_location(self) -> dict[str, Any] | None:
        """Get approximate location based on WiFi networks."""
        try:
            # Get nearby WiFi networks
            result = subprocess.run(
                ["nmcli", "-t", "-f", "SSID,BSSID,SIGNAL", "dev", "wifi"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return None

            networks = []
            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue

                parts = line.split(":")
                if len(parts) >= 3:
                    try:
                        networks.append(
                            {
                                "ssid": parts[0],
                                "bssid": parts[1],
                                "signal_strength": int(parts[2]),
                            }
                        )
                    except (ValueError, IndexError):
                        continue

            if networks:
                # Get current connection info
                connection_result = subprocess.run(
                    [
                        "nmcli",
                        "-t",
                        "-f",
                        "NAME,TYPE,DEVICE",
                        "connection",
                        "show",
                        "--active",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                active_connections = []
                if connection_result.returncode == 0:
                    for line in connection_result.stdout.strip().split("\n"):
                        if line.strip():
                            parts = line.split(":")
                            if len(parts) >= 3:
                                active_connections.append(
                                    {
                                        "name": parts[0],
                                        "type": parts[1],
                                        "device": parts[2],
                                    }
                                )

                return {
                    "nearby_networks": networks[:10],  # Limit to top 10
                    "active_connections": active_connections,
                    "source": "wifi_scan",
                }

            return None

        except Exception as e:
            logger.error("Error getting WiFi location", error=str(e))
            return None

    async def _get_network_info(self) -> dict[str, Any] | None:
        """Get network interface and IP information."""
        try:
            # Get network interfaces
            ip_result = subprocess.run(
                ["ip", "-j", "addr", "show"], capture_output=True, text=True, timeout=5
            )

            network_info = {}

            if ip_result.returncode == 0:
                try:
                    interfaces = json.loads(ip_result.stdout)
                    network_info["interfaces"] = []

                    for iface in interfaces:
                        if iface.get("operstate") == "UP":
                            iface_info = {
                                "name": iface.get("ifname"),
                                "state": iface.get("operstate"),
                                "addresses": [],
                            }

                            for addr in iface.get("addr_info", []):
                                if addr.get("family") in ["inet", "inet6"]:
                                    iface_info["addresses"].append(
                                        {
                                            "family": addr.get("family"),
                                            "local": addr.get("local"),
                                            "prefixlen": addr.get("prefixlen"),
                                        }
                                    )

                            if iface_info["addresses"]:
                                network_info["interfaces"].append(iface_info)

                except json.JSONDecodeError:
                    pass

            # Get default route
            route_result = subprocess.run(
                ["ip", "route", "show", "default"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if route_result.returncode == 0 and route_result.stdout.strip():
                network_info["default_route"] = route_result.stdout.strip()

            return network_info if network_info else None

        except Exception as e:
            logger.error("Error getting network info", error=str(e))
            return None

    async def _get_timezone_info(self) -> dict[str, Any] | None:
        """Get timezone and locale information."""
        try:
            timezone_info = {}

            # Get timezone
            tz_result = subprocess.run(
                ["timedatectl", "show", "--property=Timezone", "--value"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if tz_result.returncode == 0:
                timezone_info["timezone"] = tz_result.stdout.strip()

            # Get locale
            locale_result = subprocess.run(
                ["locale"], capture_output=True, text=True, timeout=5
            )

            if locale_result.returncode == 0:
                locale_data = {}
                for line in locale_result.stdout.strip().split("\n"):
                    if "=" in line:
                        key, value = line.split("=", 1)
                        locale_data[key] = value.strip('"')
                timezone_info["locale"] = locale_data

            return timezone_info if timezone_info else None

        except Exception as e:
            logger.error("Error getting timezone info", error=str(e))
            return None

    async def send_data_batch(self, data_batch: list[dict[str, Any]]) -> bool:
        """Send a batch of location data."""
        try:
            success_count = 0

            for location_data in data_batch:
                # Extract GPS coordinates if available
                coordinates = None
                accuracy = None

                location_info = location_data.get("location_data", {})

                # Prefer GeoClue data
                if "geoclue" in location_info:
                    geoclue_data = location_info["geoclue"]
                    coordinates = {
                        "latitude": geoclue_data.get("latitude"),
                        "longitude": geoclue_data.get("longitude"),
                    }
                    accuracy = geoclue_data.get("accuracy")

                # Send as GPS data if coordinates available
                if (
                    coordinates
                    and coordinates["latitude"] is not None
                    and coordinates["longitude"] is not None
                ):
                    success = await self.api_client.send_sensor_data(
                        "gps",
                        {
                            "latitude": coordinates["latitude"],
                            "longitude": coordinates["longitude"],
                            "accuracy": accuracy,
                            "source": "system_location",
                            "additional_data": location_info,
                        },
                    )
                else:
                    # Send as generic sensor data
                    success = await self.api_client.send_sensor_data(
                        "generic",
                        {
                            "sensor_type": "location_context",
                            "value": len(location_data.get("methods_used", [])),
                            "unit": "methods",
                            "readings": location_info,
                        },
                    )

                if success:
                    success_count += 1

            # Consider successful if at least 50% of data was sent
            return success_count >= len(data_batch) * 0.5

        except Exception as e:
            logger.error("Error sending location data batch", error=str(e))
            return False

    async def cleanup(self) -> None:
        """Cleanup location collector resources."""
        logger.info("Location collector cleaned up")

    async def get_status(self) -> dict[str, Any]:
        """Get location collector status."""
        base_status = await super().get_status()
        base_status.update(
            {
                "geoclue_available": self._geoclue_available,
                "networkmanager_available": self._networkmanager_available,
                "available_methods": self._location_methods,
            }
        )
        return base_status
