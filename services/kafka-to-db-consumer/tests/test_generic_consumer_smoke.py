"""Smoke tests for the generic Kafka to DB consumer."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiokafka import ConsumerRecord

from app.generic_consumer import GenericKafkaToDBConsumer
from app.mapping_engine import MappingEngine


class TestGenericConsumerSmoke:
    """Basic smoke tests to ensure the generic consumer can start and process messages."""

    @pytest.mark.asyncio
    async def test_consumer_initialization(
        self, mock_db_pool, mock_kafka_consumer, sample_mapping_config
    ):
        """Test that the consumer can be initialized with valid configuration."""
        consumer = GenericKafkaToDBConsumer(
            db_pool=mock_db_pool,
            kafka_consumer=mock_kafka_consumer,
            mapping_config=sample_mapping_config,
        )

        assert consumer.db_pool == mock_db_pool
        assert consumer.consumer == mock_kafka_consumer
        assert isinstance(consumer.mapping_engine, MappingEngine)
        assert consumer.mapping_engine.config == sample_mapping_config

    @pytest.mark.asyncio
    async def test_consumer_start_stop(
        self, mock_db_pool, mock_kafka_consumer, sample_mapping_config
    ):
        """Test that the consumer can start and stop cleanly."""
        consumer = GenericKafkaToDBConsumer(
            db_pool=mock_db_pool,
            kafka_consumer=mock_kafka_consumer,
            mapping_config=sample_mapping_config,
        )

        # Mock the consume method to prevent infinite loop
        consumer.consume = AsyncMock()

        # Start consumer
        consume_task = asyncio.create_task(consumer.start())

        # Give it a moment to start
        await asyncio.sleep(0.1)

        # Stop consumer
        await consumer.stop()

        # Ensure task completes
        await consume_task

        # Verify Kafka consumer lifecycle
        mock_kafka_consumer.start.assert_called_once()
        mock_kafka_consumer.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_single_gps_message(
        self,
        mock_db_pool,
        mock_kafka_consumer,
        sample_mapping_config,
        sample_gps_message,
    ):
        """Test processing a single GPS message."""
        consumer = GenericKafkaToDBConsumer(
            db_pool=mock_db_pool,
            kafka_consumer=mock_kafka_consumer,
            mapping_config=sample_mapping_config,
        )

        # Create a Kafka record
        record = ConsumerRecord(
            topic="device.sensor.gps.raw",
            partition=0,
            offset=100,
            timestamp=1735228800000,
            timestamp_type=0,
            key=b"test-device-1",
            value=sample_gps_message,
            checksum=None,
            serialized_key_size=13,
            serialized_value_size=len(str(sample_gps_message)),
            headers=[],
        )

        # Process the message
        await consumer.process_message(record)

        # Verify database interaction
        mock_db_pool.acquire.assert_called()

        # Get the connection context manager
        conn_context = mock_db_pool.acquire.return_value
        conn = conn_context.__aenter__.return_value

        # Verify execute was called
        conn.execute.assert_called_once()

        # Check the SQL query
        call_args = conn.execute.call_args
        sql_query = call_args[0][0]

        # Basic assertions about the query
        assert "INSERT INTO device_sensor_gps_raw" in sql_query
        assert "ON CONFLICT" in sql_query
        assert "trace_id" in sql_query
        assert "latitude" in sql_query
        assert "longitude" in sql_query

    @pytest.mark.asyncio
    async def test_process_multiple_message_types(
        self,
        mock_db_pool,
        mock_kafka_consumer,
        sample_mapping_config,
        sample_gps_message,
        sample_power_message,
        sample_twitter_message,
    ):
        """Test processing different types of messages."""
        consumer = GenericKafkaToDBConsumer(
            db_pool=mock_db_pool,
            kafka_consumer=mock_kafka_consumer,
            mapping_config=sample_mapping_config,
        )

        # Update mapping config to include all topics
        consumer.mapping_engine.config["topics"].update(
            {
                "device.state.power.raw": {
                    "table": "device_state_power_raw",
                    "field_mappings": {
                        "trace_id": "trace_id",
                        "device_id": "device_id",
                        "timestamp": "timestamp",
                        "data.battery_level": "battery_level",
                        "data.is_charging": "is_charging",
                    },
                    "required_fields": [
                        "trace_id",
                        "device_id",
                        "timestamp",
                        "data.battery_level",
                    ],
                },
                "external.twitter.liked.raw": {
                    "table": "twitter_posts",
                    "upsert_key": "tweet_id, timestamp",
                    "field_mappings": {
                        "trace_id": "trace_id",
                        "data.tweet_id": "tweet_id",
                        "data.tweet_text": "tweet_text",
                        "timestamp": "timestamp",
                        "device_id": "device_id",
                    },
                    "required_fields": ["trace_id", "data.tweet_id", "timestamp"],
                },
            }
        )

        # Create records for each message type
        records = [
            ConsumerRecord(
                topic="device.sensor.gps.raw",
                partition=0,
                offset=100,
                timestamp=1735228800000,
                timestamp_type=0,
                key=b"test-device-1",
                value=sample_gps_message,
                checksum=None,
                serialized_key_size=13,
                serialized_value_size=len(str(sample_gps_message)),
                headers=[],
            ),
            ConsumerRecord(
                topic="device.state.power.raw",
                partition=0,
                offset=101,
                timestamp=1735228800000,
                timestamp_type=0,
                key=b"test-device-1",
                value=sample_power_message,
                checksum=None,
                serialized_key_size=13,
                serialized_value_size=len(str(sample_power_message)),
                headers=[],
            ),
            ConsumerRecord(
                topic="external.twitter.liked.raw",
                partition=0,
                offset=102,
                timestamp=1735228800000,
                timestamp_type=0,
                key=b"test-device-1",
                value=sample_twitter_message,
                checksum=None,
                serialized_key_size=13,
                serialized_value_size=len(str(sample_twitter_message)),
                headers=[],
            ),
        ]

        # Process all messages
        for record in records:
            await consumer.process_message(record)

        # Verify database was called for each message
        assert mock_db_pool.acquire.call_count == 3

        # Get all SQL queries
        conn_context = mock_db_pool.acquire.return_value
        conn = conn_context.__aenter__.return_value

        # Check we have 3 execute calls
        assert conn.execute.call_count == 3

        # Verify different tables were targeted
        sql_queries = [call[0][0] for call in conn.execute.call_args_list]
        assert any("device_sensor_gps_raw" in q for q in sql_queries)
        assert any("device_state_power_raw" in q for q in sql_queries)
        assert any("twitter_posts" in q for q in sql_queries)

    @pytest.mark.asyncio
    async def test_consumer_error_handling(
        self, mock_db_pool, mock_kafka_consumer, sample_mapping_config
    ):
        """Test that consumer handles errors gracefully."""
        consumer = GenericKafkaToDBConsumer(
            db_pool=mock_db_pool,
            kafka_consumer=mock_kafka_consumer,
            mapping_config=sample_mapping_config,
        )

        # Create an invalid message (missing required fields)
        invalid_message = {
            "schema_version": "v1",
            "device_id": "test-device-1",
            # Missing timestamp and data
        }

        record = ConsumerRecord(
            topic="device.sensor.gps.raw",
            partition=0,
            offset=100,
            timestamp=1735228800000,
            timestamp_type=0,
            key=b"test-device-1",
            value=invalid_message,
            checksum=None,
            serialized_key_size=13,
            serialized_value_size=len(str(invalid_message)),
            headers=[],
        )

        # Process should not raise exception
        await consumer.process_message(record)

        # Database should not be called for invalid message
        mock_db_pool.acquire.assert_not_called()

    @pytest.mark.asyncio
    async def test_consumer_metrics_increment(
        self,
        mock_db_pool,
        mock_kafka_consumer,
        sample_mapping_config,
        sample_gps_message,
    ):
        """Test that consumer increments metrics on successful processing."""
        consumer = GenericKafkaToDBConsumer(
            db_pool=mock_db_pool,
            kafka_consumer=mock_kafka_consumer,
            mapping_config=sample_mapping_config,
        )

        # Mock metrics
        consumer.messages_processed = MagicMock()
        consumer.messages_failed = MagicMock()

        # Create a valid record
        record = ConsumerRecord(
            topic="device.sensor.gps.raw",
            partition=0,
            offset=100,
            timestamp=1735228800000,
            timestamp_type=0,
            key=b"test-device-1",
            value=sample_gps_message,
            checksum=None,
            serialized_key_size=13,
            serialized_value_size=len(str(sample_gps_message)),
            headers=[],
        )

        # Process the message
        await consumer.process_message(record)

        # Verify metrics were updated
        consumer.messages_processed.labels.assert_called_with(
            topic="device.sensor.gps.raw"
        )
        consumer.messages_processed.labels().inc.assert_called_once()

    @pytest.mark.asyncio
    async def test_consumer_database_error_recovery(
        self,
        mock_db_pool,
        mock_kafka_consumer,
        sample_mapping_config,
        sample_gps_message,
    ):
        """Test that consumer recovers from database errors."""
        consumer = GenericKafkaToDBConsumer(
            db_pool=mock_db_pool,
            kafka_consumer=mock_kafka_consumer,
            mapping_config=sample_mapping_config,
        )

        # Make database raise an exception
        conn_context = mock_db_pool.acquire.return_value
        conn = conn_context.__aenter__.return_value
        conn.execute.side_effect = Exception("Database connection lost")

        # Mock metrics
        consumer.messages_failed = MagicMock()

        # Create a record
        record = ConsumerRecord(
            topic="device.sensor.gps.raw",
            partition=0,
            offset=100,
            timestamp=1735228800000,
            timestamp_type=0,
            key=b"test-device-1",
            value=sample_gps_message,
            checksum=None,
            serialized_key_size=13,
            serialized_value_size=len(str(sample_gps_message)),
            headers=[],
        )

        # Process should not raise exception
        await consumer.process_message(record)

        # Verify error metrics were updated
        consumer.messages_failed.labels.assert_called_with(
            topic="device.sensor.gps.raw"
        )
        consumer.messages_failed.labels().inc.assert_called_once()
