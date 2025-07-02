"""Step detection algorithm for accelerometer data."""

import numpy as np
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
import logging
from collections import deque
from scipy import signal
import uuid

from .models import AccelerometerReading, StepCountEvent
from .config import settings

logger = logging.getLogger(__name__)


class StepDetector:
    """Detects steps from accelerometer data using frequency analysis."""
    
    def __init__(self, device_id: str):
        self.device_id = device_id
        self.window_size = int(settings.step_window_seconds * 50)  # Assuming ~50Hz sampling
        self.accel_buffer = deque(maxlen=self.window_size)
        self.last_event_time = None
        self.total_steps = 0
        self.daily_steps = 0
        self.last_reset_date = datetime.utcnow().date()
        
    def add_reading(self, reading: AccelerometerReading) -> Optional[StepCountEvent]:
        """Add a new accelerometer reading and check for steps."""
        self.accel_buffer.append(reading)
        
        # Reset daily counter if new day
        current_date = datetime.utcnow().date()
        if current_date > self.last_reset_date:
            self.daily_steps = 0
            self.last_reset_date = current_date
        
        # Need enough samples for analysis
        if len(self.accel_buffer) < self.window_size:
            return None
            
        # Check if enough time has passed since last event
        if self.last_event_time:
            if datetime.utcnow() - self.last_event_time < timedelta(seconds=settings.step_window_seconds):
                return None
        
        # Analyze window for steps
        event = self._analyze_window()
        if event:
            self.last_event_time = datetime.utcnow()
            
        return event
    
    def _analyze_window(self) -> Optional[StepCountEvent]:
        """Analyze current window for step counting."""
        if len(self.accel_buffer) < 20:  # Need minimum samples
            return None
            
        readings = list(self.accel_buffer)
        
        # Calculate acceleration magnitudes
        magnitudes = np.array([
            np.sqrt(r.x**2 + r.y**2 + r.z**2) for r in readings
        ])
        
        # Remove gravity component
        magnitudes_filtered = magnitudes - np.mean(magnitudes)
        
        # Apply bandpass filter for walking frequencies (0.5-3 Hz)
        sample_rate = len(readings) / settings.step_window_seconds
        nyquist = sample_rate / 2
        
        if nyquist > settings.step_frequency_max_hz:
            low_freq = settings.step_frequency_min_hz / nyquist
            high_freq = settings.step_frequency_max_hz / nyquist
            
            # Design butterworth bandpass filter
            b, a = signal.butter(2, [low_freq, high_freq], btype='band')
            filtered_signal = signal.filtfilt(b, a, magnitudes_filtered)
        else:
            filtered_signal = magnitudes_filtered
        
        # Find peaks (steps)
        peaks, properties = signal.find_peaks(
            filtered_signal,
            height=settings.step_threshold_ms2,
            distance=int(sample_rate / settings.step_frequency_max_hz)  # Min distance between steps
        )
        
        step_count = len(peaks)
        
        if step_count == 0:
            return None
        
        # Calculate metrics
        self.total_steps += step_count
        self.daily_steps += step_count
        
        distance_meters = step_count * settings.stride_length_meters
        calories_burned = distance_meters * settings.calories_per_meter
        
        # Calculate dominant frequency using FFT
        if len(filtered_signal) > 10:
            freqs, power = signal.periodogram(filtered_signal, sample_rate)
            peak_freq_idx = np.argmax(power[1:]) + 1  # Skip DC component
            peak_frequency = freqs[peak_freq_idx]
        else:
            peak_frequency = 0.0
        
        # Determine activity type and confidence
        activity_type, confidence = self._classify_activity(
            step_count, peak_frequency, np.mean(magnitudes_filtered)
        )
        
        # Calculate active minutes (any period with steps)
        active_minutes = int(settings.step_window_seconds / 60) if step_count > 0 else 0
        
        # Create event
        event = StepCountEvent(
            timestamp=datetime.utcnow(),
            device_id=self.device_id,
            message_id=str(uuid.uuid4()),
            step_count=step_count,
            distance_meters=round(distance_meters, 2),
            calories_burned=round(calories_burned, 2),
            active_minutes=active_minutes,
            start_time=readings[0].timestamp,
            end_time=readings[-1].timestamp,
            duration_seconds=settings.step_window_seconds,
            activity_type=activity_type,
            confidence=confidence,
            avg_acceleration=float(np.mean(np.abs(magnitudes_filtered))),
            peak_frequency_hz=float(peak_frequency)
        )
        
        logger.info(
            f"Detected {step_count} steps for device {self.device_id} "
            f"(total: {self.total_steps}, daily: {self.daily_steps})"
        )
        
        return event
    
    def _classify_activity(
        self, 
        step_count: int, 
        peak_frequency: float,
        avg_acceleration: float
    ) -> Tuple[str, float]:
        """Classify the type of activity based on step patterns."""
        steps_per_second = step_count / settings.step_window_seconds
        
        # Running: high frequency, high acceleration
        if steps_per_second > 2.5 and avg_acceleration > 2.0:
            return "running", 0.8
        
        # Walking: moderate frequency
        elif 0.8 < steps_per_second < 2.5:
            return "walking", 0.9
        
        # Slow walking
        elif 0.3 < steps_per_second <= 0.8:
            return "slow_walking", 0.7
        
        # Unknown/other activity
        else:
            return "unknown", 0.5