#!/usr/bin/env python
"""create_kafka_topics.py

Utility script to create Kafka topics required by Loom pipelines.

Usage:
    python scripts/create_kafka_topics.py --bootstrap-servers localhost:9092

This script is idempotent: existing topics are skipped.

Requirements:
    pip install confluent-kafka==2.3.0
"""
from __future__ import annotations

import argparse
import logging
from typing import List

from confluent_kafka.admin import AdminClient, NewTopic

# Topic definitions grouped by category
RAW_TOPICS: List[str] = [
    "device.audio.raw",
    "device.video.screen.raw",
    "device.image.camera.raw",
    "device.sensor.accelerometer.raw",
    "device.sensor.gps.raw",
    "device.sensor.barometer.raw",
    "device.sensor.temperature.raw",
    "device.health.heartrate.raw",
    "device.health.steps.raw",
    "device.state.power.raw",
    "device.network.wifi.raw",
    "device.network.bluetooth.raw",
    "os.events.app_lifecycle.raw",
    "os.events.notifications.raw",
    "digital.clipboard.raw",
    "digital.web_analytics.raw",
    "external.twitter.liked.raw",
    "external.calendar.events.raw",
    "external.email.events.raw",
    "task.url.ingest",
]

PROCESSED_TOPICS: List[str] = [
    "media.audio.vad_filtered",
    "media.text.transcribed.words",
    "media.image.analysis.moondream_results",
    "media.video.analysis.yolo_results",
    "analysis.3d_reconstruction.dustr_results",
    "analysis.inferred_context.qwen_results",
    "task.url.processed.twitter_archived",
    "task.url.processed.pdf_extracted",
]

DEFAULT_PARTITIONS = 3
DEFAULT_REPLICATION_FACTOR = 3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create Kafka topics for Loom")
    parser.add_argument(
        "--bootstrap-servers",
        required=True,
        help="Comma separated list of Kafka bootstrap servers (e.g., localhost:9092)",
    )
    parser.add_argument(
        "--create-processed",
        action="store_true",
        help="Also create processed topics in addition to raw topics",
    )
    return parser.parse_args()


def maybe_create_topics(admin: AdminClient, topics: List[str]):
    existing_topics = set(admin.list_topics(timeout=10).topics.keys())
    to_create = [
        NewTopic(t, num_partitions=DEFAULT_PARTITIONS, replication_factor=DEFAULT_REPLICATION_FACTOR)
        for t in topics
        if t not in existing_topics
    ]

    if not to_create:
        logging.info("All topics already exist. Nothing to do.")
        return

    # Create and wait for completion
    fs = admin.create_topics(to_create)
    for topic, f in fs.items():
        try:
            f.result()  # raises exception on failure
            logging.info("Created topic %s", topic)
        except Exception as exc:
            logging.error("Failed to create topic %s: %s", topic, exc)


def main():
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    admin = AdminClient({"bootstrap.servers": args.bootstrap_servers})

    topics = RAW_TOPICS.copy()
    if args.create_processed:
        topics += PROCESSED_TOPICS

    maybe_create_topics(admin, topics)


if __name__ == "__main__":
    main() 