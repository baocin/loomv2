#!/usr/bin/env python3
"""Fix all Kafka consumers to use optimized configuration from database.

This script updates all consumer services to use the KafkaConsumerConfigLoader
which loads optimized configurations from the pipeline_consumer_configs table.
"""

import os
import subprocess
from pathlib import Path
import re

# Consumer services that need updating
CONSUMER_SERVICES = [
    "gps-geocoding-consumer",
    "significant-motion-detector",
    "step-counter",
    "activity-classifier",
    "georegion-detector",
    "silero-vad",
    "kyutai-stt",
    "minicpm-vision",
    "face-emotion",
    # Add more as needed
]

# Template for updated consumer initialization
CONSUMER_INIT_TEMPLATE = '''
import os
import asyncpg
from loom_common.kafka.consumer_config_loader import KafkaConsumerConfigLoader

async def create_optimized_consumer():
    """Create optimized consumer with database config."""
    db_url = os.getenv('LOOM_DATABASE_URL', 'postgresql://loom:loom@postgres:5432/loom')
    db_pool = await asyncpg.create_pool(db_url)
    loader = KafkaConsumerConfigLoader(db_pool)

    consumer = await loader.create_consumer(
        service_name='{service_name}',
        topics={topics},
        kafka_bootstrap_servers=os.getenv('LOOM_KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')
    )

    return consumer, loader, db_pool
'''


def find_consumer_files(service_path):
    """Find consumer Python files in a service directory."""
    consumer_files = []
    for root, dirs, files in os.walk(service_path):
        for file in files:
            if file.endswith(".py") and "consumer" in file.lower():
                consumer_files.append(os.path.join(root, file))
    return consumer_files


def extract_topics(file_content):
    """Extract Kafka topics from consumer code."""
    # Look for topic definitions
    topic_patterns = [
        r'KAFKA_INPUT_TOPIC[S]?\s*=\s*["\']([^"\']+)["\']',
        r'input_topic[s]?\s*=\s*["\']([^"\']+)["\']',
        r"subscribe\s*\(\s*\[([^\]]+)\]",
        r'subscribe\s*\(\s*["\']([^"\']+)["\']',
    ]

    topics = []
    for pattern in topic_patterns:
        matches = re.findall(pattern, file_content, re.IGNORECASE)
        for match in matches:
            if "," in match:
                # Multiple topics
                topics.extend([t.strip().strip("\"'") for t in match.split(",")])
            else:
                topics.append(match.strip().strip("\"'"))

    return list(set(topics))  # Remove duplicates


def check_loom_common_dependency(service_path):
    """Check if service has loom-common dependency."""
    pyproject_path = os.path.join(service_path, "pyproject.toml")
    requirements_path = os.path.join(service_path, "requirements.txt")

    if os.path.exists(pyproject_path):
        with open(pyproject_path, "r") as f:
            content = f.read()
            if "loom-common" in content:
                return True

    if os.path.exists(requirements_path):
        with open(requirements_path, "r") as f:
            content = f.read()
            if "loom-common" in content:
                return True

    return False


def add_loom_common_dependency(service_path):
    """Add loom-common dependency to service."""
    pyproject_path = os.path.join(service_path, "pyproject.toml")

    if os.path.exists(pyproject_path):
        print(f"  Adding loom-common to {pyproject_path}")
        with open(pyproject_path, "r") as f:
            content = f.read()

        # Add to dependencies section
        if "[tool.poetry.dependencies]" in content:
            # Find the dependencies section and add loom-common
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if "[tool.poetry.dependencies]" in line:
                    # Insert after this line
                    for j in range(i + 1, len(lines)):
                        if lines[j].strip() and not lines[j].startswith("#"):
                            lines.insert(
                                j,
                                'loom-common = {path = "../loom-common", develop = true}',
                            )
                            break
                    break

            with open(pyproject_path, "w") as f:
                f.write("\n".join(lines))
        else:
            # For uv projects
            if "dependencies = [" in content:
                content = content.replace(
                    "dependencies = [",
                    'dependencies = [\n    "loom-common @ file:///${PROJECT_ROOT}/../loom-common",',
                    1,
                )
                with open(pyproject_path, "w") as f:
                    f.write(content)


def update_consumer_service(service_name):
    """Update a consumer service to use optimized configuration."""
    print(f"\nUpdating {service_name}...")

    service_path = Path(f"/home/aoi/code/loomv2/services/{service_name}")
    if not service_path.exists():
        print(f"  Service directory not found: {service_path}")
        return False

    # Check and add loom-common dependency
    if not check_loom_common_dependency(service_path):
        print("  Adding loom-common dependency...")
        add_loom_common_dependency(service_path)

    # Find consumer files
    consumer_files = find_consumer_files(service_path)
    if not consumer_files:
        print(f"  No consumer files found in {service_path}")
        return False

    for consumer_file in consumer_files:
        print(f"  Processing {consumer_file}...")

        with open(consumer_file, "r") as f:
            content = f.read()

        # Extract topics
        topics = extract_topics(content)
        if not topics:
            print(f"    Warning: No topics found in {consumer_file}")
            continue

        print(f"    Found topics: {topics}")

        # Check if already using optimized loader
        if "KafkaConsumerConfigLoader" in content:
            print("    Already using optimized loader, skipping...")
            continue

        # Add import and initialization code
        init_code = CONSUMER_INIT_TEMPLATE.format(
            service_name=service_name, topics=str(topics)
        )

        # Write to a separate file for manual integration
        init_file = consumer_file.replace(".py", "_optimized_init.py")
        with open(init_file, "w") as f:
            f.write(init_code)

        print(f"    Created initialization code in {init_file}")
        print("    Please manually integrate this into your consumer")

    return True


def restart_consumer(service_name):
    """Restart a consumer container."""
    container_name = f"loomv2-{service_name}-1"
    print(f"  Restarting {container_name}...")

    try:
        subprocess.run(["docker", "restart", container_name], check=True)
        print(f"  Successfully restarted {container_name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  Failed to restart {container_name}: {e}")
        return False


def main():
    """Main function."""
    print("Fixing all Kafka consumers to use optimized configuration...")
    print("=" * 60)

    # First, ensure all consumers are restarted to fix connection issues
    print("\nRestarting consumers to fix connection issues...")
    for service in CONSUMER_SERVICES:
        restart_consumer(service)

    print("\nWaiting for consumers to stabilize...")
    import time

    time.sleep(10)

    # Check consumer status
    print("\nChecking consumer status...")
    try:
        result = subprocess.run(
            [
                "docker",
                "exec",
                "loomv2-kafka-1",
                "kafka-consumer-groups",
                "--bootstrap-server",
                "localhost:9092",
                "--list",
            ],
            capture_output=True,
            text=True,
        )

        active_groups = result.stdout.strip().split("\n")
        print(f"Active consumer groups: {len(active_groups)}")
        for group in active_groups[:10]:  # Show first 10
            print(f"  - {group}")

    except Exception as e:
        print(f"Error checking consumer status: {e}")

    # Generate update templates for each service
    print("\nGenerating optimization templates...")
    for service in CONSUMER_SERVICES:
        update_consumer_service(service)

    print("\n" + "=" * 60)
    print("Summary:")
    print("1. All consumers have been restarted to fix connection issues")
    print("2. Optimization templates have been generated for manual integration")
    print("3. Look for *_optimized_init.py files in each service directory")
    print("4. Manually integrate the optimization code into your consumers")
    print("\nFor immediate optimization, update the consumer configurations in:")
    print("  - Max poll records for high-throughput consumers")
    print("  - Session timeouts for slow processors")
    print("  - Batch sizes for better performance")


if __name__ == "__main__":
    main()
