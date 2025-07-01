"""Georegion detection logic"""
import math
from typing import List, Optional, Tuple
from datetime import datetime
import structlog

from .models import Georegion, GeocodedLocation, GeoregionDetection
from .config import settings

logger = structlog.get_logger()


class GeoregionDetector:
    """Detects when a device enters/exits defined georegions"""
    
    def __init__(self, georegions: Optional[List[Georegion]] = None):
        """Initialize with georegions from config or database"""
        if georegions:
            self.georegions = georegions
        else:
            # Load from default config
            self.georegions = [
                Georegion(**gr) for gr in settings.default_georegions
            ]
        logger.info("Initialized georegion detector", 
                   georegion_count=len(self.georegions))
    
    def calculate_distance(self, lat1: float, lon1: float, 
                          lat2: float, lon2: float) -> float:
        """Calculate distance between two points in meters using Haversine formula"""
        R = 6371000  # Earth's radius in meters
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        distance = R * c
        return distance
    
    def detect_georegions(self, location: GeocodedLocation) -> List[GeoregionDetection]:
        """Detect which georegions the location falls within"""
        detections = []
        
        # Extract coordinates from geocoded location
        lat = location.data.get("latitude")
        lon = location.data.get("longitude")
        
        if lat is None or lon is None:
            logger.warning("Missing coordinates in geocoded location",
                          trace_id=location.trace_id)
            return detections
        
        # Check each georegion
        for georegion in self.georegions:
            distance = self.calculate_distance(
                lat, lon, 
                georegion.latitude, georegion.longitude
            )
            
            if distance <= georegion.radius_meters:
                # Location is within this georegion
                confidence = 1.0 - (distance / georegion.radius_meters)
                
                detection = GeoregionDetection(
                    trace_id=f"{location.trace_id}_gr_{georegion.id}",
                    device_id=location.device_id,
                    timestamp=location.timestamp,
                    data={
                        "georegion_id": georegion.id,
                        "georegion_name": georegion.name,
                        "georegion_type": georegion.type,
                        "latitude": lat,
                        "longitude": lon,
                        "distance_to_center_meters": round(distance, 2),
                        "confidence_score": round(confidence, 3),
                        "entry_time": location.timestamp,  # Could track state
                        "exit_time": None,  # Would need state tracking
                    },
                    metadata={
                        "trigger_source": "geocoded_location",
                        "original_trace_id": location.trace_id,
                        "georegion_metadata": georegion.metadata
                    }
                )
                
                detections.append(detection)
                
                logger.info("Detected georegion presence",
                           device_id=location.device_id,
                           georegion=georegion.name,
                           distance=round(distance, 2),
                           confidence=round(confidence, 3))
        
        return detections
    
    def update_georegions(self, georegions: List[Georegion]):
        """Update the list of georegions (e.g., from database)"""
        self.georegions = georegions
        logger.info("Updated georegions", count=len(georegions))