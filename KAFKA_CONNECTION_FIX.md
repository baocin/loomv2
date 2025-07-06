# Kafka Connection Fix Summary

## Issue
Multiple services including x-url-processor were failing to connect to Kafka with error:
```
Connect attempt to <BrokerConnection node_id=1 host=localhost:9092 <connecting> [IPv4 ('127.0.0.1', 9092)]> returned error 111. Disconnecting.
```

## Root Cause
The Kafka advertised listeners were configured incorrectly:
- PLAINTEXT_HOST was advertised as `localhost:9092`
- When services connected to `kafka:29092`, Kafka's metadata response directed them to `localhost:9092`
- Containers cannot reach `localhost:9092` as it refers to the container's own localhost, not the host

## Solution Applied

1. **Fixed Kafka Advertised Listeners** in `docker-compose.local.yml`:
   ```yaml
   # Changed from:
   KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:29092,PLAINTEXT_HOST://localhost:9092

   # To:
   KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:29092,PLAINTEXT_HOST://kafka:9092
   ```

2. **Added Consumer Optimization** for x-url-processor:
   - Inserted configuration into `pipeline_consumer_configs` table
   - Configured for web scraping workload (5 URLs batch, 10-min timeout)

## Services Fixed
- x-url-processor ✅
- calendar-fetcher
- text-embedder
- scheduled-consumers

## Verification
```bash
# Check service is connected
docker compose -f docker-compose.local.yml logs x-url-processor | grep "Successfully joined group"

# Check Kafka is healthy
docker compose -f docker-compose.local.yml ps kafka
```

## Note
The PLAINTEXT_HOST listener is now only accessible from within the Docker network at `kafka:9092`.
If you need to access Kafka from the host machine, you'll need to use port forwarding or add another listener.
