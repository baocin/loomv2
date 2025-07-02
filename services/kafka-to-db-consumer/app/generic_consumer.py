"""Generic Kafka to Database consumer using mapping configuration."""

import asyncio
import json
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

import asyncpg
import structlog
from aiokafka import AIOKafkaConsumer
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .mapping_engine import MappingEngine

logger = structlog.get_logger(__name__)


class GenericKafkaToDBConsumer:
    """Generic consumer that uses YAML mapping configuration to route messages to database tables."""

    def __init__(
        self,
        database_url: str,
        kafka_bootstrap_servers: str,
        group_id: str = "generic-kafka-to-db-consumer",
    ):
        """Initialize the generic consumer."""
        self.database_url = database_url
        self.kafka_bootstrap_servers = kafka_bootstrap_servers
        self.group_id = group_id

        self.consumer: Optional[AIOKafkaConsumer] = None
        self.db_pool: Optional[asyncpg.Pool] = None
        self.running = False

        # Initialize mapping engine
        self.mapping_engine = MappingEngine()

        # Get supported topics from configuration
        self.supported_topics = self.mapping_engine.get_supported_topics()

        logger.info(
            "Initialized generic consumer",
            supported_topics=len(self.supported_topics),
            topics=self.supported_topics[:5],
        )  # Log first 5 topics

    async def start(self):
        """Start the consumer service."""
        logger.info("Starting generic Kafka to DB consumer")

        # Validate mapping configuration
        config_errors = self.mapping_engine.validate_config()
        if config_errors:
            logger.error("Invalid mapping configuration", errors=config_errors)
            raise ValueError(f"Configuration errors: {config_errors}")

        # Initialize database connection pool
        self.db_pool = await asyncpg.create_pool(
            self.database_url,
            min_size=2,
            max_size=10,
            command_timeout=60,
        )

        if not self.supported_topics:
            logger.warning("No topics configured for consumption")
            return

        # Initialize Kafka consumer for all supported topics
        self.consumer = AIOKafkaConsumer(
            *self.supported_topics,
            bootstrap_servers=self.kafka_bootstrap_servers,
            group_id=self.group_id,
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )

        await self.consumer.start()
        self.running = True

        logger.info(
            "Generic Kafka to DB consumer started",
            topics=self.supported_topics,
            group_id=self.group_id,
        )

    async def stop(self):
        """Stop the consumer service."""
        logger.info("Stopping generic Kafka to DB consumer")
        self.running = False

        if self.consumer:
            await self.consumer.stop()

        if self.db_pool:
            await self.db_pool.close()

        logger.info("Generic Kafka to DB consumer stopped")

    async def consume_messages(self):
        """Main message consumption loop."""
        if not self.consumer or not self.db_pool:
            raise RuntimeError("Consumer not properly initialized")

        logger.info("Starting generic message consumption loop")

        try:
            async for message in self.consumer:
                if not self.running:
                    break

                try:
                    await self._process_message(message)
                except Exception as e:
                    logger.error(
                        "Failed to process message",
                        topic=message.topic,
                        partition=message.partition,
                        offset=message.offset,
                        error=str(e),
                        exc_info=True,
                    )

        except Exception as e:
            logger.error("Error in consumption loop", error=str(e), exc_info=True)
            raise

    async def _process_message(self, message):
        """Process a single Kafka message using mapping configuration."""
        topic = message.topic
        data = message.value

        logger.debug(
            "Processing message with generic consumer",
            topic=topic,
            trace_id=data.get("trace_id"),
            keys=list(data.keys()) if isinstance(data, dict) else None,
        )

        # Use mapping engine to convert message to database record(s)
        mapping_result = self.mapping_engine.map_message_to_record(topic, data)
        if not mapping_result:
            logger.warning("No mapping result for message", topic=topic)
            return

        table_name, record_data, upsert_key = mapping_result

        # Handle multiple records (for array mappings)
        if isinstance(record_data, list):
            await self._insert_multiple_records(
                table_name, record_data, upsert_key, topic, data
            )
        else:
            await self._insert_single_record(
                table_name, record_data, upsert_key, topic, data
            )

        logger.debug(
            "Message processed successfully with generic consumer",
            topic=topic,
            table=table_name,
            trace_id=(
                record_data.get("trace_id")
                if isinstance(record_data, dict)
                else "multiple"
            ),
        )

    async def _insert_single_record(
        self,
        table_name: str,
        record: Dict[str, Any],
        upsert_key: str,
        topic: str,
        original_message: Dict[str, Any],
    ):
        """Insert a single record into the database."""
        try:
            # Build dynamic INSERT query with ON CONFLICT
            columns = list(record.keys())
            placeholders = [f"${i+1}" for i in range(len(columns))]
            values = [record[col] for col in columns]

            # Get topic configuration for conflict strategy
            topic_config = self.mapping_engine.get_topic_mapping(topic)
            conflict_strategy = topic_config.get("conflict_strategy", "ignore")

            # Build conflict resolution clause
            if conflict_strategy == "ignore":
                conflict_clause = f"ON CONFLICT ({upsert_key}) DO NOTHING"
            elif conflict_strategy == "update":
                # Update all columns except the conflict key
                update_columns = [col for col in columns if col != upsert_key]
                if update_columns:
                    update_clauses = [
                        f"{col} = EXCLUDED.{col}" for col in update_columns
                    ]
                    conflict_clause = f"ON CONFLICT ({upsert_key}) DO UPDATE SET {', '.join(update_clauses)}"
                else:
                    conflict_clause = f"ON CONFLICT ({upsert_key}) DO NOTHING"
            else:
                # replace strategy - no conflict clause, will fail on duplicate
                conflict_clause = ""

            query = f"""
            INSERT INTO {table_name} ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
            {conflict_clause}
            """

            async with self.db_pool.acquire() as conn:
                await conn.execute(query, *values)

        except Exception as e:
            logger.error(
                "Failed to insert record",
                table=table_name,
                topic=topic,
                trace_id=record.get("trace_id"),
                error=str(e),
                columns=list(record.keys()),
                exc_info=True,
            )
            raise

    async def _insert_multiple_records(
        self,
        table_name: str,
        records: List[Dict[str, Any]],
        upsert_key: str,
        topic: str,
        original_message: Dict[str, Any],
    ):
        """Insert multiple records into the database (for array mappings)."""
        if not records:
            return

        try:
            # Get all unique columns across all records
            all_columns = set()
            for record in records:
                all_columns.update(record.keys())
            all_columns = sorted(list(all_columns))

            # Prepare batch insert
            placeholders_per_record = [f"${i+1}" for i in range(len(all_columns))]
            values_list = []

            for record in records:
                # Ensure all records have the same columns (fill missing with None)
                record_values = [record.get(col) for col in all_columns]
                values_list.extend(record_values)

            # Build query for batch insert
            num_records = len(records)
            value_groups = []
            for i in range(num_records):
                offset = i * len(all_columns)
                group_placeholders = [
                    f"${offset + j + 1}" for j in range(len(all_columns))
                ]
                value_groups.append(f"({', '.join(group_placeholders)})")

            # Get conflict strategy
            topic_config = self.mapping_engine.get_topic_mapping(topic)
            conflict_strategy = topic_config.get("conflict_strategy", "ignore")

            if conflict_strategy == "ignore":
                conflict_clause = f"ON CONFLICT ({upsert_key}) DO NOTHING"
            elif conflict_strategy == "update":
                update_columns = [col for col in all_columns if col != upsert_key]
                if update_columns:
                    update_clauses = [
                        f"{col} = EXCLUDED.{col}" for col in update_columns
                    ]
                    conflict_clause = f"ON CONFLICT ({upsert_key}) DO UPDATE SET {', '.join(update_clauses)}"
                else:
                    conflict_clause = f"ON CONFLICT ({upsert_key}) DO NOTHING"
            else:
                conflict_clause = ""

            query = f"""
            INSERT INTO {table_name} ({', '.join(all_columns)})
            VALUES {', '.join(value_groups)}
            {conflict_clause}
            """

            async with self.db_pool.acquire() as conn:
                await conn.execute(query, *values_list)

            logger.info(
                "Inserted multiple records",
                table=table_name,
                topic=topic,
                record_count=len(records),
                trace_id=original_message.get("trace_id"),
            )

        except Exception as e:
            logger.error(
                "Failed to insert multiple records",
                table=table_name,
                topic=topic,
                record_count=len(records),
                trace_id=original_message.get("trace_id"),
                error=str(e),
                exc_info=True,
            )
            raise

    async def reload_configuration(self):
        """Reload mapping configuration (for hot-reloading)."""
        logger.info("Reloading mapping configuration")

        # Reload config
        self.mapping_engine.reload_config()

        # Check if supported topics changed
        new_topics = self.mapping_engine.get_supported_topics()

        if set(new_topics) != set(self.supported_topics):
            logger.warning(
                "Topic configuration changed - restart required",
                old_topics=self.supported_topics,
                new_topics=new_topics,
            )
            # Note: In production, you might want to restart the consumer automatically
            # For now, just log the warning

        self.supported_topics = new_topics

        logger.info(
            "Configuration reloaded", supported_topics=len(self.supported_topics)
        )


# Global consumer instance
consumer: Optional[GenericKafkaToDBConsumer] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global consumer

    # Configuration from environment
    import os

    database_url = os.getenv(
        "LOOM_DATABASE_URL", "postgresql://loom:loom@localhost:5432/loom"
    )
    kafka_servers = os.getenv("LOOM_KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    group_id = os.getenv("KAFKA_GROUP_ID", "generic-kafka-to-db-consumer")

    # Startup
    consumer = GenericKafkaToDBConsumer(database_url, kafka_servers, group_id)
    await consumer.start()

    # Start consumption task
    consumption_task = asyncio.create_task(consumer.consume_messages())

    yield

    # Shutdown
    if consumer:
        await consumer.stop()
    consumption_task.cancel()

    try:
        await consumption_task
    except asyncio.CancelledError:
        pass


# Create FastAPI app
app = FastAPI(
    title="Generic Kafka to Database Consumer",
    description="Configurable data ingestion from Kafka topics to database tables using YAML mappings",
    version="2.0.0",
    lifespan=lifespan,
)


@app.get("/healthz")
async def health_check():
    """Health check endpoint."""
    global consumer
    return JSONResponse(
        content={
            "status": "healthy",
            "service": "generic-kafka-to-db-consumer",
            "consumer_running": consumer.running if consumer else False,
            "supported_topics": len(consumer.supported_topics) if consumer else 0,
        }
    )


@app.get("/status")
async def get_status():
    """Get consumer status and configuration."""
    global consumer

    if not consumer:
        return JSONResponse(
            content={"error": "Consumer not initialized"}, status_code=503
        )

    return JSONResponse(
        content={
            "consumer_running": consumer.running,
            "supported_topics": consumer.supported_topics,
            "topic_count": len(consumer.supported_topics),
            "kafka_servers": consumer.kafka_bootstrap_servers,
            "group_id": consumer.group_id,
            "configuration_valid": len(consumer.mapping_engine.validate_config()) == 0,
        }
    )


@app.get("/topics")
async def get_topics():
    """Get supported topics and their configurations."""
    global consumer

    if not consumer:
        return JSONResponse(
            content={"error": "Consumer not initialized"}, status_code=503
        )

    topics_info = {}
    for topic in consumer.supported_topics:
        topic_config = consumer.mapping_engine.get_topic_mapping(topic)
        if topic_config:
            topics_info[topic] = {
                "table": topic_config.get("table"),
                "description": topic_config.get("description"),
                "upsert_key": topic_config.get("upsert_key", "trace_id"),
                "field_count": len(topic_config.get("field_mappings", {})),
                "required_fields": topic_config.get("required_fields", []),
            }

    return JSONResponse(content=topics_info)


@app.post("/reload-config")
async def reload_config():
    """Reload mapping configuration."""
    global consumer

    if not consumer:
        return JSONResponse(
            content={"error": "Consumer not initialized"}, status_code=503
        )

    try:
        await consumer.reload_configuration()

        # Validate new configuration
        config_errors = consumer.mapping_engine.validate_config()

        return JSONResponse(
            content={
                "status": "success",
                "message": "Configuration reloaded",
                "supported_topics": len(consumer.supported_topics),
                "configuration_valid": len(config_errors) == 0,
                "errors": config_errors,
            }
        )

    except Exception as e:
        logger.error("Failed to reload configuration", error=str(e))
        return JSONResponse(
            content={"error": f"Failed to reload configuration: {str(e)}"},
            status_code=500,
        )


@app.get("/validate-config")
async def validate_config():
    """Validate current mapping configuration."""
    global consumer

    if not consumer:
        return JSONResponse(
            content={"error": "Consumer not initialized"}, status_code=503
        )

    errors = consumer.mapping_engine.validate_config()

    return JSONResponse(
        content={
            "valid": len(errors) == 0,
            "errors": errors,
            "supported_topics": len(consumer.supported_topics),
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.generic_consumer:app",
        host="0.0.0.0",
        port=8001,
        log_level="info",
        reload=False,
    )
