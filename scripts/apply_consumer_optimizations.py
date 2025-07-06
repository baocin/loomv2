#!/usr/bin/env python3
"""
Script to apply consumer optimizations to all Kafka consumer services.
This script helps identify and update services that need optimization.
"""

from pathlib import Path
from typing import List, Tuple


def find_kafka_consumers(services_dir: Path) -> List[Tuple[Path, str]]:
    """Find all services that use Kafka consumers."""
    consumers = []

    for service_dir in services_dir.iterdir():
        if not service_dir.is_dir():
            continue

        # Check Python files
        for py_file in service_dir.rglob("*.py"):
            content = py_file.read_text()
            if any(
                pattern in content
                for pattern in [
                    "from kafka import KafkaConsumer",
                    "import kafka",
                    "KafkaConsumer(",
                    "from aiokafka import",
                    "AIOKafkaConsumer",
                ]
            ):
                consumers.append((py_file, "python"))

        # Check TypeScript/JavaScript files
        for ext in ["*.ts", "*.js"]:
            for ts_file in service_dir.rglob(ext):
                # Skip node_modules and directories
                if "node_modules" in str(ts_file) or ts_file.is_dir():
                    continue
                try:
                    content = ts_file.read_text()
                    if any(
                        pattern in content
                        for pattern in ["kafkajs", "new Kafka", "kafka.consumer"]
                    ):
                        consumers.append((ts_file, "typescript"))
                except Exception:
                    continue

    return consumers


def check_optimization_status(file_path: Path, language: str) -> bool:
    """Check if a file already uses the optimization loader."""
    content = file_path.read_text()

    if language == "python":
        return (
            "KafkaConsumerConfigLoader" in content
            or "consumer_config_loader" in content
        )
    else:  # typescript
        return "consumerConfigLoader" in content or "createOptimizedConsumer" in content


def generate_update_instructions(consumers: List[Tuple[Path, str]]) -> None:
    """Generate instructions for updating each consumer."""

    print("# Kafka Consumer Optimization Status Report")
    print("=" * 60)

    optimized = []
    needs_update = []

    for file_path, language in consumers:
        if check_optimization_status(file_path, language):
            optimized.append((file_path, language))
        else:
            needs_update.append((file_path, language))

    print(f"\n## Already Optimized ({len(optimized)} services)")
    for file_path, lang in optimized:
        try:
            rel_path = file_path.relative_to(Path.cwd())
        except ValueError:
            rel_path = file_path
        print(f"✓ {rel_path} ({lang})")

    print(f"\n## Needs Optimization ({len(needs_update)} services)")
    for file_path, lang in needs_update:
        service_name = file_path.parts[-3] if len(file_path.parts) > 3 else "unknown"
        try:
            rel_path = file_path.relative_to(Path.cwd())
        except ValueError:
            rel_path = file_path
        print(f"\n### {service_name} - {rel_path}")

        if lang == "python":
            print(
                """
1. Add to requirements.txt:
   ```
   loom-common>=0.1.0
   asyncpg>=0.27.0
   psutil>=5.9.0
   ```

2. Add imports:
   ```python
   from loom_common.kafka_utils.consumer_config_loader import KafkaConsumerConfigLoader
   import asyncpg
   import os
   ```

3. Replace consumer creation:
   ```python
   # Before:
   consumer = KafkaConsumer(
       'topic_name',
       bootstrap_servers=['kafka:9092'],
       # ... manual settings
   )

   # After:
   async def create_consumer():
       db_pool = await asyncpg.create_pool(os.getenv('DATABASE_URL'))
       loader = KafkaConsumerConfigLoader(db_pool)

       consumer = await loader.create_consumer(
           service_name='"""
                + service_name
                + """',
           topics=['topic_name'],
           bootstrap_servers='kafka:9092'
       )
       return consumer, loader
   ```

4. Add metrics recording:
   ```python
   # In your processing loop:
   await loader.record_processing_metrics(
       service_name='"""
                + service_name
                + """',
       messages_processed=len(messages),
       processing_time_ms=elapsed_ms,
       memory_usage_mb=psutil.Process().memory_info().rss / 1024 / 1024
   )
   ```
"""
            )
        else:  # typescript
            print(
                """
1. Install dependencies:
   ```bash
   npm install pg kafkajs
   ```

2. Import the loader:
   ```typescript
   import { createOptimizedConsumer } from '../shared/consumerConfigLoader';
   import { Pool } from 'pg';
   ```

3. Replace consumer creation:
   ```typescript
   // Before:
   const consumer = kafka.consumer({ groupId: 'my-group' });

   // After:
   const pool = new Pool({ connectionString: process.env.DATABASE_URL });
   const consumer = await createOptimizedConsumer(
       pool,
       { brokers: ['kafka:9092'] },
       '"""
                + service_name
                + """',
       ['topic_name']
   );
   ```
"""
            )


def check_database_configs() -> None:
    """Check which services have database configurations."""
    print("\n## Database Configuration Status")
    print("Run this SQL to see which services have configs:")
    print(
        """
```sql
-- Show all configured services
SELECT service_name, max_poll_records, session_timeout_ms, description
FROM pipeline_consumer_configs
ORDER BY service_name;

-- Show services from pipeline_services not yet configured
SELECT ps.name
FROM pipeline_services ps
LEFT JOIN pipeline_consumer_configs pcc ON ps.name = pcc.service_name
WHERE pcc.service_name IS NULL
ORDER BY ps.name;
```
"""
    )


def generate_monitoring_queries() -> None:
    """Generate useful monitoring queries."""
    print("\n## Monitoring Queries")
    print(
        """
```sql
-- Check consumer lag
SELECT * FROM v_consumer_performance_monitor
WHERE avg_lag > 100
ORDER BY avg_lag DESC;

-- Get optimization recommendations
SELECT service_name, recommendation, priority
FROM v_consumer_alerts
WHERE priority IN ('high', 'critical');

-- Monitor a specific service
SELECT * FROM v_consumer_performance_history
WHERE service_name = 'your-service-name'
AND timestamp > NOW() - INTERVAL '1 hour'
ORDER BY timestamp DESC;
```
"""
    )


def main():
    """Main execution function."""
    services_dir = Path("services")

    if not services_dir.exists():
        print("Error: services directory not found. Run from project root.")
        return

    # Find all Kafka consumers
    consumers = find_kafka_consumers(services_dir)

    # Generate update instructions
    generate_update_instructions(consumers)

    # Check database configs
    check_database_configs()

    # Generate monitoring queries
    generate_monitoring_queries()

    print("\n## Next Steps")
    print(
        """
1. Update services that need optimization using the instructions above
2. Run database migrations if not already applied:
   ```bash
   make db-migrate
   ```
3. Populate initial consumer configs:
   ```bash
   python scripts/populate_consumer_configs.py
   ```
4. Monitor performance and adjust configs as needed
"""
    )


if __name__ == "__main__":
    main()
