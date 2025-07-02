"""Motion detection algorithm for accelerometer data."""

import numpy as np
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
import logging
from collections import deque

from .models import (
    AccelerometerReading, 
    SignificantMotionEvent, 
    MotionType, 
    ActivityType
)
from .config import settings

logger = logging.getLogger(__name__)


class MotionDetector:
    """Detects significant motion events from accelerometer data."""
    
    def __init__(self):
        self.window_size = int(settings.motion_window_seconds * 100)  # Assuming ~100Hz sampling
        self.motion_buffer = deque(maxlen=self.window_size)
        self.last_event_time = None
        self.event_counter = 0
        
    def add_reading(self, reading: AccelerometerReading) -> Optional[SignificantMotionEvent]:
        """Add a new accelerometer reading and check for significant motion."""
        self.motion_buffer.append(reading)
        
        # Need enough samples for analysis
        if len(self.motion_buffer) < self.window_size // 2:
            return None
            
        # Check cooldown period
        if self.last_event_time:
            cooldown_end = self.last_event_time + timedelta(seconds=settings.motion_cooldown_seconds)
            if datetime.utcnow() < cooldown_end:
                return None
        
        # Analyze motion in current window
        event = self._analyze_window()
        if event:
            self.last_event_time = datetime.utcnow()
            self.event_counter += 1
            
        return event
    
    def _analyze_window(self) -> Optional[SignificantMotionEvent]:
        """Analyze current window for significant motion."""
        if len(self.motion_buffer) < 10:  # Need minimum samples
            return None
            
        readings = list(self.motion_buffer)
        
        # Calculate acceleration magnitudes
        magnitudes = np.array([
            np.sqrt(r.x**2 + r.y**2 + r.z**2) for r in readings
        ])
        
        # Remove gravity component (approximately 9.8 m/s²)
        magnitudes_no_gravity = np.abs(magnitudes - 9.8)
        
        # Calculate statistics
        max_accel = np.max(magnitudes_no_gravity)
        avg_accel = np.mean(magnitudes_no_gravity)
        std_accel = np.std(magnitudes_no_gravity)
        
        # Check if motion is significant
        if max_accel < settings.motion_threshold_ms2:
            return None
            
        # Detect motion type
        motion_type, confidence = self._classify_motion(readings, magnitudes_no_gravity)
        
        # Detect activity type
        activity_type, activity_confidence = self._classify_activity(
            avg_accel, std_accel, magnitudes_no_gravity
        )
        
        # Calculate dominant axis
        x_var = np.var([r.x for r in readings])
        y_var = np.var([r.y for r in readings])
        z_var = np.var([r.z for r in readings])
        
        dominant_axis = "x" if x_var > y_var and x_var > z_var else (
            "y" if y_var > z_var else "z"
        )
        
        # Create event
        event = SignificantMotionEvent(
            event_id=f"{readings[0].device_id}_{self.event_counter}_{int(datetime.utcnow().timestamp())}",
            device_id=readings[0].device_id,
            start_time=readings[0].timestamp,
            end_time=readings[-1].timestamp,
            duration_seconds=(readings[-1].timestamp - readings[0].timestamp).total_seconds(),
            motion_type=motion_type,
            confidence=confidence,
            max_acceleration=float(max_accel),
            avg_acceleration=float(avg_accel),
            dominant_axis=dominant_axis,
            activity_type=activity_type,
            activity_confidence=activity_confidence,
            sample_count=len(readings),
            raw_data_summary={
                "std_acceleration": float(std_accel),
                "min_acceleration": float(np.min(magnitudes_no_gravity)),
                "percentile_25": float(np.percentile(magnitudes_no_gravity, 25)),
                "percentile_75": float(np.percentile(magnitudes_no_gravity, 75)),
                "x_variance": float(x_var),
                "y_variance": float(y_var),
                "z_variance": float(z_var)
            }
        )
        
        logger.info(
            f"Detected significant motion: {motion_type} "
            f"(confidence: {confidence:.2f}, max_accel: {max_accel:.2f} m/s²)"
        )
        
        return event
    
    def _classify_motion(
        self, 
        readings: List[AccelerometerReading], 
        magnitudes: np.ndarray
    ) -> Tuple[MotionType, float]:
        """Classify the type of motion detected."""
        # Calculate features
        max_mag = np.max(magnitudes)
        avg_mag = np.mean(magnitudes)
        std_mag = np.std(magnitudes)
        
        # Check for sudden changes
        if len(magnitudes) > 10:
            first_quarter = magnitudes[:len(magnitudes)//4]
            last_quarter = magnitudes[-len(magnitudes)//4:]
            
            start_avg = np.mean(first_quarter)
            end_avg = np.mean(last_quarter)
            
            if end_avg - start_avg > 3.0:  # Sudden acceleration
                return MotionType.SUDDEN_START, 0.8
            elif start_avg - end_avg > 3.0:  # Sudden deceleration
                return MotionType.SUDDEN_STOP, 0.8
        
        # Check for fall (high acceleration followed by low)
        if max_mag > 8.0 and len(magnitudes) > 20:
            peak_idx = np.argmax(magnitudes)
            if peak_idx < len(magnitudes) - 10:
                post_peak = magnitudes[peak_idx+5:]
                if np.mean(post_peak) < 1.0:
                    return MotionType.FALL, 0.9
        
        # Check for shake (high frequency oscillation)
        if std_mag > 2.0 and self._count_zero_crossings(magnitudes) > 10:
            return MotionType.SHAKE, 0.7
        
        # Check for walking/running patterns
        zero_crossings = self._count_zero_crossings(magnitudes - avg_mag)
        if 5 < zero_crossings < 15 and 1.0 < avg_mag < 3.0:
            return MotionType.WALKING, 0.7
        elif zero_crossings > 15 and avg_mag > 3.0:
            return MotionType.RUNNING, 0.7
        
        # Vehicle motion (low frequency, moderate magnitude)
        if zero_crossings < 5 and 0.5 < avg_mag < 2.0:
            return MotionType.VEHICLE, 0.6
        
        return MotionType.UNKNOWN, 0.5
    
    def _classify_activity(
        self, 
        avg_accel: float, 
        std_accel: float,
        magnitudes: np.ndarray
    ) -> Tuple[Optional[ActivityType], Optional[float]]:
        """Classify the activity type based on motion patterns."""
        # Stationary
        if avg_accel < settings.activity_stationary_threshold:
            return ActivityType.STATIONARY, 0.9
        
        # Walking
        elif avg_accel < settings.activity_walking_threshold and std_accel > 0.5:
            return ActivityType.WALKING, 0.7
        
        # Running
        elif avg_accel < settings.activity_running_threshold and std_accel > 1.0:
            return ActivityType.RUNNING, 0.7
        
        # Vehicle (smooth motion)
        elif avg_accel < settings.activity_vehicle_threshold and std_accel < 0.5:
            return ActivityType.VEHICLE, 0.6
        
        # Unknown
        return ActivityType.UNKNOWN, 0.5
    
    def _count_zero_crossings(self, signal: np.ndarray) -> int:
        """Count the number of zero crossings in a signal."""
        if len(signal) < 2:
            return 0
        
        # Remove mean to center around zero
        centered = signal - np.mean(signal)
        
        # Count sign changes
        signs = np.sign(centered)
        diff = np.diff(signs)
        crossings = np.sum(np.abs(diff) > 1)
        
        return int(crossings)