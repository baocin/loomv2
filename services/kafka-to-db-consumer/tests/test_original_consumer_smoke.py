"""Smoke tests for the original (hardcoded) Kafka to DB consumer."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiokafka import ConsumerRecord

from app.consumer import KafkaToDBConsumer


class TestOriginalConsumerSmoke:
    """Smoke tests for the original hardcoded consumer."""

    @pytest.mark.asyncio
    async def test_consumer_initialization(self, mock_db_pool, mock_kafka_consumer):
        """Test that the consumer can be initialized."""
        consumer = KafkaToDBConsumer(
            db_pool=mock_db_pool, kafka_consumer=mock_kafka_consumer
        )

        assert consumer.db_pool == mock_db_pool
        assert consumer.consumer == mock_kafka_consumer

    @pytest.mark.asyncio
    async def test_consumer_start_stop(self, mock_db_pool, mock_kafka_consumer):
        """Test that the consumer can start and stop cleanly."""
        consumer = KafkaToDBConsumer(
            db_pool=mock_db_pool, kafka_consumer=mock_kafka_consumer
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
    async def test_process_gps_message(
        self, mock_db_pool, mock_kafka_consumer, sample_gps_message
    ):
        """Test processing a GPS message."""
        consumer = KafkaToDBConsumer(
            db_pool=mock_db_pool, kafka_consumer=mock_kafka_consumer
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

        # Verify it's inserting into the correct table
        assert "INSERT INTO device_sensor_gps_raw" in sql_query
        assert "ON CONFLICT" in sql_query

    @pytest.mark.asyncio
    async def test_process_power_message(
        self, mock_db_pool, mock_kafka_consumer, sample_power_message
    ):
        """Test processing a power state message."""
        consumer = KafkaToDBConsumer(
            db_pool=mock_db_pool, kafka_consumer=mock_kafka_consumer
        )

        # Create a Kafka record
        record = ConsumerRecord(
            topic="device.state.power.raw",
            partition=0,
            offset=100,
            timestamp=1735228800000,
            timestamp_type=0,
            key=b"test-device-1",
            value=sample_power_message,
            checksum=None,
            serialized_key_size=13,
            serialized_value_size=len(str(sample_power_message)),
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

        # Verify it's inserting into the correct table
        assert "INSERT INTO device_state_power_raw" in sql_query

    @pytest.mark.asyncio
    async def test_process_unknown_topic(self, mock_db_pool, mock_kafka_consumer):
        """Test that unknown topics are handled gracefully."""
        consumer = KafkaToDBConsumer(
            db_pool=mock_db_pool, kafka_consumer=mock_kafka_consumer
        )

        # Create a record with unknown topic
        record = ConsumerRecord(
            topic="unknown.topic.raw",
            partition=0,
            offset=100,
            timestamp=1735228800000,
            timestamp_type=0,
            key=b"test-device-1",
            value={"test": "data"},
            checksum=None,
            serialized_key_size=13,
            serialized_value_size=10,
            headers=[],
        )

        # Process the message - should not raise exception
        await consumer.process_message(record)

        # Database should not be called for unknown topic
        mock_db_pool.acquire.assert_not_called()

    @pytest.mark.asyncio
    async def test_consumer_error_recovery(
        self, mock_db_pool, mock_kafka_consumer, sample_gps_message
    ):
        """Test that consumer recovers from errors."""
        consumer = KafkaToDBConsumer(
            db_pool=mock_db_pool, kafka_consumer=mock_kafka_consumer
        )

        # Make database raise an exception
        conn_context = mock_db_pool.acquire.return_value
        conn = conn_context.__aenter__.return_value
        conn.execute.side_effect = Exception("Database error")

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

        # Verify error was handled
        mock_db_pool.acquire.assert_called()

    @pytest.mark.asyncio
    async def test_consumer_metrics(
        self, mock_db_pool, mock_kafka_consumer, sample_gps_message
    ):
        """Test that consumer updates metrics."""
        consumer = KafkaToDBConsumer(
            db_pool=mock_db_pool, kafka_consumer=mock_kafka_consumer
        )

        # Mock metrics
        with patch.object(
            consumer, "messages_processed"
        ) as mock_processed, patch.object(consumer, "messages_failed") as mock_failed:
            mock_processed.labels = MagicMock(return_value=MagicMock(inc=MagicMock()))
            mock_failed.labels = MagicMock(return_value=MagicMock(inc=MagicMock()))

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

            # Process the message
            await consumer.process_message(record)

            # Verify metrics were updated
            mock_processed.labels.assert_called_with(topic="device.sensor.gps.raw")
            mock_processed.labels().inc.assert_called_once()
