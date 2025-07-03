# Kafka to Database Consumer

A generic Kafka consumer service that routes messages from Kafka topics to PostgreSQL/TimescaleDB tables using configurable field mappings.

## Features

- **Flexible Configuration**: Supports both YAML-based and database-driven configuration
- **Dynamic Field Mapping**: Map Kafka message fields to database columns with transformations
- **Batch Processing**: Efficient batch inserts for array-based messages
- **Conflict Resolution**: Configurable upsert strategies (ignore, update, replace)
- **Hot Reloading**: Reload configuration without restarting the service
- **Health Monitoring**: REST API endpoints for health checks and status

## Configuration Modes

### 1. YAML-Based Configuration (Default)

Uses the `config/topic_mappings.yml` file to define topic-to-table mappings.

```bash
# Run with YAML configuration (default)
make dev
```

### 2. Database-Driven Configuration

Uses the new schema management tables in TimescaleDB to read topic configurations.

```bash
# Run with database configuration
USE_DATABASE_CONFIG=true make dev

# Or set in docker-compose
environment:
  - USE_DATABASE_CONFIG=true
```

## Database Configuration Setup

1. **Run the schema management migration**:
   ```sql
   -- This creates the schema management tables
   \i services/ingestion-api/migrations/032_create_kafka_schema_management.sql
   ```

2. **Import existing configurations**:
   ```bash
   cd scripts
   python import_kafka_schemas.py --yes
   ```

3. **Verify the import**:
   ```sql
   -- Check imported topics
   SELECT topic_name, table_name FROM topic_table_configs ORDER BY topic_name;
   
   -- Check field mappings for a specific topic
   SELECT * FROM topic_field_mappings WHERE topic_name = 'device.network.wifi.raw';
   ```

## Environment Variables

- `LOOM_DATABASE_URL`: PostgreSQL connection string (default: postgresql://loom:loom@localhost:5432/loom)
- `LOOM_KAFKA_BOOTSTRAP_SERVERS`: Kafka bootstrap servers (default: localhost:9092)
- `KAFKA_GROUP_ID`: Kafka consumer group ID (default: generic-kafka-to-db-consumer)
- `USE_DATABASE_CONFIG`: Use database-driven configuration (default: false)

## API Endpoints

- `GET /healthz` - Health check
- `GET /status` - Consumer status and configuration
- `GET /topics` - List supported topics and their configurations
- `GET /validate-config` - Validate current configuration
- `POST /reload-config` - Reload configuration (hot reload)

## Adding New Topics

### With Database Configuration

1. **Add the topic to kafka_topics table**:
   ```sql
   INSERT INTO kafka_topics (topic_name, category, source, datatype, description, retention_days)
   VALUES ('device.new.sensor.raw', 'device', 'new', 'sensor', 'New sensor data', 30);
   ```

2. **Configure table mapping**:
   ```sql
   INSERT INTO topic_table_configs (topic_name, table_name, upsert_key)
   VALUES ('device.new.sensor.raw', 'device_new_sensor_raw', 'device_id, timestamp');
   ```

3. **Add field mappings**:
   ```sql
   INSERT INTO topic_field_mappings (topic_name, table_name, source_field_path, target_column, data_type)
   VALUES 
   ('device.new.sensor.raw', 'device_new_sensor_raw', 'device_id', 'device_id', 'string'),
   ('device.new.sensor.raw', 'device_new_sensor_raw', 'timestamp', 'timestamp', 'timestamp'),
   ('device.new.sensor.raw', 'device_new_sensor_raw', 'value', 'sensor_value', 'float');
   ```

4. **Reload configuration**:
   ```bash
   curl -X POST http://localhost:8001/reload-config
   ```

### With YAML Configuration

Edit `config/topic_mappings.yml` and restart the service.

## Monitoring

```bash
# Check consumer status
curl http://localhost:8001/status | jq .

# View supported topics
curl http://localhost:8001/topics | jq .

# Validate configuration
curl http://localhost:8001/validate-config | jq .
```

## Development

```bash
# Install dependencies
make install

# Run tests
make test

# Run with hot reload
make dev

# Build Docker image
make docker
```

## Troubleshooting

1. **Consumer not processing messages**: Check consumer group offset and topic subscriptions
2. **Field mapping errors**: Enable debug logging to see detailed mapping information
3. **Database connection issues**: Verify DATABASE_URL and network connectivity
4. **Configuration not loading**: Check schema management tables are populated

## Architecture

The consumer uses a pluggable mapping engine architecture:

- `MappingEngine`: YAML-based configuration (original)
- `DatabaseMappingEngine`: Database-driven configuration (new)

Both engines implement the same interface, allowing seamless switching between configuration modes.