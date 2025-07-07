# Kafka Single Partition Debug Mode

This guide explains how to switch Kafka topics to single partition mode for debugging consumer issues.

## Why Single Partition Mode?

When Kafka topics have multiple partitions, messages are distributed across partitions and assigned to different consumer instances. This can make debugging difficult because:
- A consumer might be assigned partitions that aren't receiving data
- Messages might be going to different consumer instances
- It's harder to track message flow

Single partition mode ensures all messages go through one partition, making it easier to debug.

## Switching to Single Partition Mode

### 1. Set Environment Variable

The system now uses `LOOM_KAFKA_DEFAULT_PARTITIONS` environment variable. It's already set in `.env.docker-compose`:

```bash
LOOM_KAFKA_DEFAULT_PARTITIONS=1
```

### 2. Stop All Services

```bash
docker-compose -f docker-compose.local.yml down
```

### 3. Reset Kafka Topics

Run the script to delete and recreate all topics with 1 partition:

```bash
./scripts/reset_kafka_topics_single_partition.sh
```

This script will:
- Delete all existing Kafka topics
- Recreate them with 1 partition each
- Maintain the same retention periods

### 4. Update Database Configuration

Update the database to reflect the new partition configuration:

```bash
docker exec loomv2-postgres-1 psql -U loom -d loom -f /scripts/update_kafka_partitions_db.sql
```

Or if running from outside the container:

```bash
psql -h localhost -U loom -d loom -f scripts/update_kafka_partitions_db.sql
```

### 5. Restart Services

```bash
docker-compose -f docker-compose.local.yml up -d
```

## Verifying the Configuration

### Check Kafka Topics

```bash
docker exec loomv2-kafka-1 kafka-topics --bootstrap-server localhost:9092 --describe --topic device.audio.raw
```

You should see `PartitionCount: 1`

### Check Database

```bash
docker exec loomv2-postgres-1 psql -U loom -d loom -c "SELECT topic_name, partitions FROM kafka_topics WHERE is_active = true LIMIT 5;"
```

All topics should show `partitions: 1`

## Switching Back to Multi-Partition Mode

### 1. Update Environment Variable

Edit `.env.docker-compose`:

```bash
LOOM_KAFKA_DEFAULT_PARTITIONS=3  # Or your desired default
```

### 2. Update Database

First, revert the partition counts in the database by running the partition optimization migration:

```bash
docker exec loomv2-postgres-1 psql -U loom -d loom -c "
UPDATE kafka_topics kt
SET partitions = CASE
    WHEN topic_name = 'device.sensor.accelerometer.raw' THEN 10
    WHEN topic_name = 'device.audio.raw' THEN 6
    WHEN topic_name IN ('os.events.app_lifecycle.raw', 'os.events.system.raw') THEN 4
    ELSE 3
END
WHERE is_active = true;"
```

### 3. Recreate Topics

You'll need to delete and recreate topics with the new partition counts. The system will use the partition counts from the database when auto-creating topics.

### 4. Restart Services

```bash
docker-compose -f docker-compose.local.yml down
docker-compose -f docker-compose.local.yml up -d
```

## Troubleshooting

### Consumer Not Receiving Messages

With single partition mode, if consumers still aren't receiving messages:

1. Check consumer group offset:
```bash
docker exec loomv2-kafka-1 kafka-consumer-groups --bootstrap-server localhost:9092 --describe --group kyutai-stt-consumer
```

2. Reset consumer offset if needed:
```bash
docker exec loomv2-kafka-1 kafka-consumer-groups --bootstrap-server localhost:9092 --group kyutai-stt-consumer --reset-offsets --to-earliest --all-topics --execute
```

3. Check topic has messages:
```bash
docker exec loomv2-kafka-1 kafka-console-consumer --bootstrap-server localhost:9092 --topic device.audio.raw --from-beginning --max-messages 5
```

### Partition Mismatch

If you see errors about partition counts not matching:

1. Ensure both Kafka and database have the same partition configuration
2. Restart all services to pick up the new configuration
3. Check logs for any topic auto-creation with wrong partition counts
