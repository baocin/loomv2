"""Prometheus metrics for georegion detection"""
from prometheus_client import Counter, Gauge, Histogram

# Counters
messages_processed = Counter(
    'georegion_messages_processed_total', 
    'Total geocoded location messages processed'
)

detections_made = Counter(
    'georegion_detections_made_total',
    'Total georegion detections made'
)

processing_errors = Counter(
    'georegion_processing_errors_total',
    'Total processing errors'
)

# Histograms
processing_duration = Histogram(
    'georegion_processing_duration_seconds',
    'Time spent processing messages'
)

# Gauges
active_georegions = Gauge(
    'georegion_active_regions_count',
    'Number of active georegions being monitored'
)