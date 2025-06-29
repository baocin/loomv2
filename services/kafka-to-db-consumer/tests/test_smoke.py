"""Main smoke tests for kafka-to-db-consumer service."""

import asyncio
import signal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.main import main, shutdown_handler


class TestServiceSmoke:
    """Smoke tests for the main service."""

    @pytest.mark.asyncio
    async def test_shutdown_handler(self):
        """Test that shutdown handler works correctly."""
        loop = asyncio.get_event_loop()

        # Mock tasks
        task1 = AsyncMock()
        task2 = AsyncMock()

        # Call shutdown handler
        with patch("asyncio.all_tasks", return_value={task1, task2}):
            with patch("sys.exit") as mock_exit:
                shutdown_handler(signal.SIGTERM, None)

                # Give async operations time to complete
                await asyncio.sleep(0.1)

                # Verify tasks were cancelled
                task1.cancel.assert_called_once()
                task2.cancel.assert_called_once()
                mock_exit.assert_called_once_with(0)

    @pytest.mark.asyncio
    async def test_main_startup_shutdown(self):
        """Test that the main function can start up and shut down cleanly."""
        # Mock all external dependencies
        with patch(
            "app.main.asyncpg.create_pool", new_callable=AsyncMock
        ) as mock_create_pool, patch(
            "app.main.AIOKafkaConsumer"
        ) as mock_kafka_consumer_class, patch(
            "app.main.yaml.safe_load"
        ) as mock_yaml_load, patch(
            "builtins.open", create=True
        ) as mock_open, patch(
            "app.main.logger"
        ) as mock_logger:
            # Setup mocks
            mock_pool = AsyncMock()
            mock_create_pool.return_value = mock_pool

            mock_consumer = AsyncMock()
            mock_consumer.start = AsyncMock()
            mock_consumer.stop = AsyncMock()
            mock_consumer.__aiter__ = AsyncMock(return_value=iter([]))  # Empty iterator
            mock_kafka_consumer_class.return_value = mock_consumer

            # Mock config file
            mock_yaml_load.return_value = {
                "schema_version": "v1",
                "defaults": {
                    "upsert_key": "trace_id, timestamp",
                    "conflict_strategy": "ignore",
                },
                "topics": {
                    "device.sensor.gps.raw": {
                        "table": "device_sensor_gps_raw",
                        "field_mappings": {"trace_id": "trace_id"},
                    }
                },
            }

            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file

            # Run main with a timeout
            try:
                await asyncio.wait_for(main(), timeout=1.0)
            except asyncio.TimeoutError:
                # Expected - the consumer runs forever
                pass

            # Verify startup sequence
            mock_create_pool.assert_called_once()
            mock_kafka_consumer_class.assert_called_once()
            mock_consumer.start.assert_called_once()
            mock_logger.info.assert_any_call("Starting Generic Kafka to DB Consumer...")

    @pytest.mark.asyncio
    async def test_main_database_connection_error(self):
        """Test that the service handles database connection errors gracefully."""
        with patch(
            "app.main.asyncpg.create_pool", new_callable=AsyncMock
        ) as mock_create_pool, patch("app.main.logger") as mock_logger, patch(
            "sys.exit"
        ) as mock_exit:
            # Make database connection fail
            mock_create_pool.side_effect = Exception("Cannot connect to database")

            # Run main
            await main()

            # Verify error was logged and service exited
            mock_logger.error.assert_called()
            assert "Cannot connect to database" in str(mock_logger.error.call_args)
            mock_exit.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_main_kafka_connection_error(self):
        """Test that the service handles Kafka connection errors gracefully."""
        with patch(
            "app.main.asyncpg.create_pool", new_callable=AsyncMock
        ) as mock_create_pool, patch(
            "app.main.AIOKafkaConsumer"
        ) as mock_kafka_consumer_class, patch(
            "app.main.yaml.safe_load"
        ) as mock_yaml_load, patch(
            "builtins.open", create=True
        ) as mock_open, patch(
            "app.main.logger"
        ) as mock_logger, patch(
            "sys.exit"
        ) as mock_exit:
            # Setup mocks
            mock_pool = AsyncMock()
            mock_create_pool.return_value = mock_pool

            # Make Kafka fail to start
            mock_consumer = AsyncMock()
            mock_consumer.start.side_effect = Exception("Cannot connect to Kafka")
            mock_kafka_consumer_class.return_value = mock_consumer

            # Mock config
            mock_yaml_load.return_value = {"topics": {}}
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file

            # Run main
            await main()

            # Verify error was logged and service exited
            mock_logger.error.assert_called()
            assert "Cannot connect to Kafka" in str(mock_logger.error.call_args)
            mock_exit.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_main_config_file_error(self):
        """Test that the service handles missing config file gracefully."""
        with patch(
            "app.main.asyncpg.create_pool", new_callable=AsyncMock
        ) as mock_create_pool, patch("builtins.open", create=True) as mock_open, patch(
            "app.main.logger"
        ) as mock_logger, patch(
            "sys.exit"
        ) as mock_exit:
            # Setup mocks
            mock_pool = AsyncMock()
            mock_create_pool.return_value = mock_pool

            # Make config file fail to open
            mock_open.side_effect = FileNotFoundError("Config file not found")

            # Run main
            await main()

            # Verify error was logged and service exited
            mock_logger.error.assert_called()
            assert "Config file not found" in str(mock_logger.error.call_args)
            mock_exit.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_consumer_processes_messages_continuously(self):
        """Test that the consumer processes messages in a loop."""
        from aiokafka import ConsumerRecord

        # Create test messages
        test_messages = [
            ConsumerRecord(
                topic="device.sensor.gps.raw",
                partition=0,
                offset=i,
                timestamp=1735228800000 + i * 1000,
                timestamp_type=0,
                key=b"test-device-1",
                value={
                    "trace_id": f"test-{i}",
                    "device_id": "test-device-1",
                    "timestamp": "2025-06-26T12:00:00Z",
                    "schema_version": "v1",
                    "data": {
                        "latitude": 37.7749 + i * 0.001,
                        "longitude": -122.4194 + i * 0.001,
                    },
                },
                checksum=None,
                serialized_key_size=13,
                serialized_value_size=100,
                headers=[],
            )
            for i in range(3)
        ]

        # Track processed messages
        processed_messages = []

        async def mock_execute(query, *args):
            processed_messages.append(query)
            return None

        with patch(
            "app.main.asyncpg.create_pool", new_callable=AsyncMock
        ) as mock_create_pool, patch(
            "app.main.AIOKafkaConsumer"
        ) as mock_kafka_consumer_class, patch(
            "app.main.yaml.safe_load"
        ) as mock_yaml_load, patch(
            "builtins.open", create=True
        ) as mock_open:
            # Setup database mock
            mock_pool = AsyncMock()
            mock_conn = AsyncMock()
            mock_conn.execute = mock_execute
            mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
            mock_create_pool.return_value = mock_pool

            # Setup Kafka mock to return test messages then stop
            mock_consumer = AsyncMock()
            mock_consumer.start = AsyncMock()
            mock_consumer.stop = AsyncMock()

            # Make consumer return test messages then raise to exit
            async def message_generator():
                for msg in test_messages:
                    yield msg
                raise KeyboardInterrupt("Test complete")

            mock_consumer.__aiter__ = message_generator
            mock_kafka_consumer_class.return_value = mock_consumer

            # Mock config
            mock_yaml_load.return_value = {
                "schema_version": "v1",
                "defaults": {
                    "upsert_key": "trace_id, timestamp",
                    "conflict_strategy": "ignore",
                },
                "topics": {
                    "device.sensor.gps.raw": {
                        "table": "device_sensor_gps_raw",
                        "field_mappings": {
                            "trace_id": "trace_id",
                            "device_id": "device_id",
                            "timestamp": "timestamp",
                            "data.latitude": "latitude",
                            "data.longitude": "longitude",
                        },
                        "required_fields": [
                            "trace_id",
                            "device_id",
                            "timestamp",
                            "data.latitude",
                            "data.longitude",
                        ],
                    }
                },
            }

            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file

            # Run main
            with pytest.raises(KeyboardInterrupt):
                await main()

            # Verify all messages were processed
            assert len(processed_messages) == 3
            for query in processed_messages:
                assert "INSERT INTO device_sensor_gps_raw" in query
