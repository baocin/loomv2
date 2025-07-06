"""Activity classification logic."""

import numpy as np
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
import logging
from collections import defaultdict
from geopy.distance import distance
import uuid

from .models import ActivityType, LocationContext, ActivityClassification
from .config import settings

logger = logging.getLogger(__name__)


class ActivityClassifier:
    """Classifies user activities based on motion, location, and step data."""

    def __init__(self):
        self.event_buffer = defaultdict(list)  # Per-device event buffers
        self.last_classification = {}  # Last classification time per device

    def add_event(
        self, device_id: str, event_type: str, event_data: dict
    ) -> Optional[ActivityClassification]:
        """Add an event and check if we should classify."""
        # Store event
        self.event_buffer[device_id].append(
            {
                "type": event_type,
                "data": event_data,
                "timestamp": self._parse_timestamp(event_data.get("timestamp")),
            }
        )

        # Clean old events
        self._clean_old_events(device_id)

        # Check if we should classify
        last_time = self.last_classification.get(device_id)
        now = datetime.now(timezone.utc)

        if (
            last_time
            and (now - last_time).total_seconds()
            < settings.classification_window_seconds
        ):
            return None

        # Classify if we have enough data
        classification = self._classify_activity(device_id)
        if classification:
            self.last_classification[device_id] = now

        return classification

    def _parse_timestamp(self, ts) -> datetime:
        """Parse timestamp from various formats."""
        if isinstance(ts, datetime):
            # Ensure datetime is timezone-aware
            if ts.tzinfo is None:
                return ts.replace(tzinfo=timezone.utc)
            return ts
        elif isinstance(ts, str):
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        else:
            return datetime.now(timezone.utc)

    def _clean_old_events(self, device_id: str):
        """Remove events older than classification window."""
        cutoff = datetime.now(timezone.utc) - timedelta(
            seconds=settings.classification_window_seconds * 2
        )
        self.event_buffer[device_id] = [
            e for e in self.event_buffer[device_id] if e["timestamp"] > cutoff
        ]

    def _classify_activity(self, device_id: str) -> Optional[ActivityClassification]:
        """Classify activity based on accumulated events."""
        events = self.event_buffer[device_id]
        if not events:
            return None

        # Separate events by type
        motion_events = [e for e in events if e["type"] == "motion"]
        gps_events = [e for e in events if e["type"] == "gps"]
        step_events = [e for e in events if e["type"] == "steps"]

        # Calculate time window
        timestamps = [e["timestamp"] for e in events]
        start_time = min(timestamps)
        end_time = max(timestamps)
        duration_seconds = (end_time - start_time).total_seconds()

        if duration_seconds < 10:  # Need at least 10 seconds of data
            return None

        # Analyze motion events
        motion_analysis = self._analyze_motion_events(motion_events)

        # Analyze GPS data
        gps_analysis = self._analyze_gps_events(gps_events)

        # Analyze step data
        step_analysis = self._analyze_step_events(step_events)

        # Combine analyses to determine activity
        activity_type, confidence = self._determine_activity(
            motion_analysis, gps_analysis, step_analysis
        )

        # Determine location context
        location_context = self._determine_location_context(gps_events)

        # Collect source event IDs
        source_events = []
        for event in events:
            if "data" in event and "trace_id" in event["data"]:
                source_events.append(event["data"]["trace_id"])
            elif "data" in event and "message_id" in event["data"]:
                source_events.append(event["data"]["message_id"])

        # Create classification
        classification = ActivityClassification(
            timestamp=datetime.now(timezone.utc),
            device_id=device_id,
            message_id=str(uuid.uuid4()),
            activity_type=activity_type,
            confidence=confidence,
            location_context=location_context,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration_seconds,
            motion_events_count=len(motion_events),
            step_count=step_analysis.get("total_steps", 0),
            distance_meters=step_analysis.get("total_distance", 0.0),
            avg_speed_ms=gps_analysis.get("avg_speed", 0.0),
            max_speed_ms=gps_analysis.get("max_speed", 0.0),
            start_location=gps_analysis.get("start_location"),
            end_location=gps_analysis.get("end_location"),
            metrics={
                "motion": motion_analysis,
                "gps": gps_analysis,
                "steps": step_analysis,
            },
            source_events=source_events[:100],  # Limit to 100 source events
        )

        logger.info(
            f"Classified activity for device {device_id}: "
            f"{activity_type} (confidence: {confidence:.2f})"
        )

        return classification

    def _analyze_motion_events(self, events: List[dict]) -> dict:
        """Analyze motion events."""
        if not events:
            return {}

        motion_types = defaultdict(int)
        avg_accelerations = []

        for event in events:
            data = event["data"]
            if "motion_type" in data:
                motion_types[data["motion_type"]] += 1
            if "avg_acceleration" in data:
                avg_accelerations.append(data["avg_acceleration"])

        return {
            "motion_types": dict(motion_types),
            "dominant_motion": (
                max(motion_types.items(), key=lambda x: x[1])[0]
                if motion_types
                else None
            ),
            "avg_acceleration": (
                np.mean(avg_accelerations) if avg_accelerations else 0.0
            ),
        }

    def _analyze_gps_events(self, events: List[dict]) -> dict:
        """Analyze GPS events for speed and distance."""
        if not events:
            return {}

        # Sort by timestamp
        events = sorted(events, key=lambda e: e["timestamp"])

        speeds = []
        total_distance = 0.0

        for i in range(1, len(events)):
            prev = events[i - 1]["data"]
            curr = events[i]["data"]

            if (
                "latitude" in prev
                and "longitude" in prev
                and "latitude" in curr
                and "longitude" in curr
            ):
                # Calculate distance
                prev_pos = (prev["latitude"], prev["longitude"])
                curr_pos = (curr["latitude"], curr["longitude"])
                dist = distance(prev_pos, curr_pos).meters

                # Calculate time difference
                time_diff = (
                    events[i]["timestamp"] - events[i - 1]["timestamp"]
                ).total_seconds()

                if time_diff > 0:
                    speed = dist / time_diff
                    speeds.append(speed)
                    total_distance += dist

        # Get start and end locations
        start_location = None
        end_location = None

        if events:
            first = events[0]["data"]
            if "latitude" in first and "longitude" in first:
                start_location = {"lat": first["latitude"], "lon": first["longitude"]}

            last = events[-1]["data"]
            if "latitude" in last and "longitude" in last:
                end_location = {"lat": last["latitude"], "lon": last["longitude"]}

        return {
            "avg_speed": np.mean(speeds) if speeds else 0.0,
            "max_speed": max(speeds) if speeds else 0.0,
            "total_distance": total_distance,
            "start_location": start_location,
            "end_location": end_location,
        }

    def _analyze_step_events(self, events: List[dict]) -> dict:
        """Analyze step events."""
        if not events:
            return {}

        total_steps = 0
        total_distance = 0.0
        total_calories = 0.0
        activity_types = defaultdict(int)

        for event in events:
            data = event["data"]
            total_steps += data.get("step_count", 0)
            total_distance += data.get("distance_meters", 0.0)
            total_calories += data.get("calories_burned", 0.0)

            if "activity_type" in data:
                activity_types[data["activity_type"]] += 1

        # Calculate steps per minute
        duration_minutes = (
            sum(e["data"].get("duration_seconds", 0) for e in events) / 60.0
        )

        steps_per_minute = total_steps / duration_minutes if duration_minutes > 0 else 0

        return {
            "total_steps": total_steps,
            "total_distance": total_distance,
            "total_calories": total_calories,
            "steps_per_minute": steps_per_minute,
            "activity_types": dict(activity_types),
        }

    def _determine_activity(
        self, motion_analysis: dict, gps_analysis: dict, step_analysis: dict
    ) -> Tuple[ActivityType, float]:
        """Determine activity type based on all analyses."""
        # Priority: GPS speed > Steps > Motion

        avg_speed = gps_analysis.get("avg_speed", 0.0)
        steps_per_minute = step_analysis.get("steps_per_minute", 0)
        dominant_motion = motion_analysis.get("dominant_motion")

        # Vehicle detection (high speed, low steps)
        if avg_speed > settings.activity_vehicle_speed_ms:
            if steps_per_minute < 10:
                return ActivityType.VEHICLE, 0.9
            else:
                # Could be cycling
                return ActivityType.CYCLING, 0.7

        # Running (high steps per minute)
        if steps_per_minute > settings.activity_running_steps_per_minute:
            return ActivityType.RUNNING, 0.8

        # Walking (moderate steps)
        if steps_per_minute > settings.activity_min_steps_per_minute:
            return ActivityType.WALKING, 0.9

        # Stationary (low speed, low steps)
        if avg_speed < settings.activity_stationary_speed_ms and steps_per_minute < 5:
            return ActivityType.STATIONARY, 0.8

        # Check motion type as fallback
        if dominant_motion:
            if dominant_motion == "walking":
                return ActivityType.WALKING, 0.6
            elif dominant_motion == "running":
                return ActivityType.RUNNING, 0.6
            elif dominant_motion == "vehicle":
                return ActivityType.VEHICLE, 0.6

        # Unknown
        return ActivityType.UNKNOWN, 0.5

    def _determine_location_context(
        self, gps_events: List[dict]
    ) -> Optional[LocationContext]:
        """Determine location context from GPS data."""
        # This is a simplified implementation
        # In a real system, you would check against known locations (home, work, etc.)

        if not gps_events:
            return None

        # For now, just return unknown
        # Could be enhanced with geofencing, POI lookup, etc.
        return LocationContext.UNKNOWN
