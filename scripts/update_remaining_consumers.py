#!/usr/bin/env python3
"""
Update remaining Kafka consumers to use the optimization loader.
This script focuses on actual service consumers, not library code.
"""

import re
from pathlib import Path

# Services that actually need updating based on pipeline definitions
SERVICES_TO_UPDATE = [
    # Simple processors
    ("georegion-detector", "device.sensor.gps.raw"),
    ("activity-classifier", "device.sensor.accelerometer.windowed"),
    ("step-counter", "device.sensor.accelerometer.raw"),
    # AI processors
    ("face-emotion", "media.image.analysis.minicpm_results"),
    ("gemma3n-processor", "media.text.transcribed.words"),
    # I/O processors
    ("gps-geocoding-consumer", "device.sensor.gps.raw"),
    # Scheduled tasks
    ("scheduled-consumers", "various"),
]


def update_python_consumer(service_path: Path, service_name: str, topics: str):
    """Update a Python consumer to use optimization loader."""

    # Find the main consumer file
    consumer_files = list(service_path.rglob("*consumer*.py"))
    if not consumer_files:
        consumer_files = list(service_path.rglob("main.py"))

    if not consumer_files:
        print(f"  ⚠️  No consumer file found for {service_name}")
        return False

    # Update the first consumer file found
    consumer_file = consumer_files[0]

    # Skip if already optimized
    content = consumer_file.read_text()
    if "KafkaConsumerConfigLoader" in content:
        print(f"  ✓ Already optimized: {consumer_file}")
        return True

    print(f"  📝 Updating: {consumer_file}")

    # Check if it uses regular KafkaConsumer or AIOKafkaConsumer
    is_async = "AIOKafkaConsumer" in content or "aiokafka" in content

    # Add imports
    import_section = """
# Kafka consumer optimization
from loom_common.kafka_utils.consumer_config_loader import KafkaConsumerConfigLoader
import asyncpg
import psutil
"""

    # Find where to insert imports (after existing imports)
    import_match = re.search(
        r"(from kafka import.*\n|import kafka.*\n|from aiokafka import.*\n)", content
    )
    if import_match:
        insert_pos = import_match.end()
        content = content[:insert_pos] + import_section + content[insert_pos:]

    # Replace consumer creation
    if is_async:
        # Async consumer pattern
        old_pattern = r"consumer = AIOKafkaConsumer\((.*?)\)"
        new_code = f"""
# Create optimized consumer with database config
async def create_optimized_consumer():
    db_url = os.getenv('DATABASE_URL', 'postgresql://loom:loom@postgres:5432/loom')
    db_pool = await asyncpg.create_pool(db_url)
    loader = KafkaConsumerConfigLoader(db_pool)

    consumer = await loader.create_consumer(
        service_name='{service_name}',
        topics=['{topics}'],  # Update with actual topics
        bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
    )

    return consumer, loader, db_pool

# Use it in your main function:
# consumer, loader, db_pool = await create_optimized_consumer()
"""
    else:
        # Sync consumer pattern
        old_pattern = r"consumer = KafkaConsumer\((.*?)\)"
        new_code = f"""
# Create optimized consumer with database config
def create_optimized_consumer():
    # Note: For sync consumers, you may need to refactor to async
    # or use the BaseKafkaConsumer from loom_common
    from loom_common.kafka.consumer import BaseKafkaConsumer

    consumer = BaseKafkaConsumer(
        service_name='{service_name}',
        topics=['{topics}'],  # Update with actual topics
        bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092'),
        db_pool=None  # Pass asyncpg pool if available
    )

    return consumer

# Use it in your main function:
# consumer = create_optimized_consumer()
"""

    # Add the creation function after imports
    content = re.sub(r"(import.*\n)(\n+)", r"\1" + new_code + r"\2", content, count=1)

    # Save the updated file
    consumer_file.write_text(content)

    # Update requirements.txt
    req_file = service_path / "requirements.txt"
    if req_file.exists():
        req_content = req_file.read_text()
        if "loom-common" not in req_content:
            req_content += "\n# Kafka optimization dependencies\nloom-common>=0.1.0\nasyncpg>=0.27.0\npsutil>=5.9.0\n"
            req_file.write_text(req_content)
            print("  ✓ Updated requirements.txt")

    return True


def main():
    """Update remaining consumers."""
    print("# Updating Remaining Kafka Consumers")
    print("=" * 60)

    services_dir = Path("services")

    for service_name, topics in SERVICES_TO_UPDATE:
        service_path = services_dir / service_name

        if not service_path.exists():
            print(f"\n❌ Service not found: {service_name}")
            continue

        print(f"\n## Updating {service_name}")

        # Update Python consumers
        success = update_python_consumer(service_path, service_name, topics)

        if success:
            print(f"  ✅ Successfully updated {service_name}")
        else:
            print(f"  ❌ Failed to update {service_name}")

    print("\n## Next Steps")
    print(
        """
1. Review the updated consumer files to ensure correct topic names
2. Test each service individually:
   ```bash
   cd services/<service-name>
   docker build -t <service-name> .
   docker run --env-file .env <service-name>
   ```
3. Apply database migrations:
   ```bash
   make db-migrate
   ```
4. Monitor performance:
   ```sql
   SELECT * FROM v_consumer_performance_monitor;
   ```
"""
    )


if __name__ == "__main__":
    main()
