"""Unit tests for AI context endpoint."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.auth import verify_api_key
from app.database import db_manager
from app.main import app


@pytest.fixture(autouse=True)
def mock_api_key():
    """Mock API key verification for all tests."""

    async def override_verify_api_key():
        return "test-api-key"

    app.dependency_overrides[verify_api_key] = override_verify_api_key
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio()
async def test_ai_context_success(test_client: AsyncClient):
    """Test successful AI context retrieval."""
    # Mock database connection and data
    mock_table_data = {
        "device_sensor_gps_raw": {
            "data": {
                "id": 1,
                "device_id": "test-device-123",
                "timestamp": datetime.utcnow().isoformat(),
                "latitude": 37.7749,
                "longitude": -122.4194,
                "accuracy": 10.5,
            },
            "row_count": 1000,
            "latest_timestamp": datetime.utcnow().isoformat(),
        },
        "device_audio_raw": {
            "data": {
                "id": 2,
                "device_id": "test-device-123",
                "timestamp": datetime.utcnow().isoformat(),
                "format": "wav",
                "sample_rate": 44100,
            },
            "row_count": 500,
            "latest_timestamp": datetime.utcnow().isoformat(),
        },
        "devices": {
            "data": {
                "device_id": "test-device-123",
                "device_name": "Test Device",
                "device_type": "mobile",
            },
            "row_count": 3,
            "latest_timestamp": datetime.utcnow().isoformat(),
        },
    }

    with patch.object(db_manager, "is_connected", True):
        with patch.object(
            db_manager,
            "get_latest_from_all_tables",
            AsyncMock(return_value=mock_table_data),
        ):
            response = await test_client.get("/ai/context")

    assert response.status_code == 200

    data = response.json()
    assert "timestamp" in data
    assert data["device_count"] == 3
    assert "summary" in data
    assert "tables" in data
    assert "context_prompt" in data

    # Check summary
    assert "3 tables in system" in data["summary"]["total_tables"]
    assert "3 tables with data" in data["summary"]["populated_tables"]
    assert "active_sensors" in data["summary"]

    # Check tables
    assert "device_sensor_gps_raw" in data["tables"]
    assert data["tables"]["device_sensor_gps_raw"]["row_count"] == 1000
    assert data["tables"]["device_sensor_gps_raw"]["data"]["latitude"] == 37.7749


@pytest.mark.asyncio()
async def test_ai_context_database_not_connected(test_client: AsyncClient):
    """Test AI context when database is not connected."""
    with patch.object(db_manager, "is_connected", False):
        response = await test_client.get("/ai/context")

    assert response.status_code == 503
    assert response.json()["detail"] == "Database not connected"


@pytest.mark.asyncio()
async def test_ai_context_with_empty_tables(test_client: AsyncClient):
    """Test AI context with empty tables."""
    mock_table_data = {
        "device_sensor_gps_raw": {
            "data": None,
            "row_count": 0,
            "latest_timestamp": None,
        },
        "devices": {
            "data": None,
            "row_count": 0,
            "latest_timestamp": None,
        },
    }

    with patch.object(db_manager, "is_connected", True):
        with patch.object(
            db_manager,
            "get_latest_from_all_tables",
            AsyncMock(return_value=mock_table_data),
        ):
            response = await test_client.get("/ai/context")

    assert response.status_code == 200

    data = response.json()
    assert data["device_count"] == 0
    assert "0 tables with data" in data["summary"]["populated_tables"]
    assert "No recent activity detected" in data["summary"]["latest_activity"]
    assert "No active sensors" in data["summary"]["active_sensors"]


@pytest.mark.asyncio()
async def test_ai_context_with_table_errors(test_client: AsyncClient):
    """Test AI context with table query errors."""
    mock_table_data = {
        "device_sensor_gps_raw": {
            "data": None,
            "row_count": None,
            "latest_timestamp": None,
            "error": "Table does not exist",
        },
        "devices": {
            "data": {
                "device_id": "test-device-123",
            },
            "row_count": 1,
            "latest_timestamp": datetime.utcnow().isoformat(),
        },
    }

    with patch.object(db_manager, "is_connected", True):
        with patch.object(
            db_manager,
            "get_latest_from_all_tables",
            AsyncMock(return_value=mock_table_data),
        ):
            response = await test_client.get("/ai/context")

    assert response.status_code == 200

    data = response.json()
    assert "1 tables with errors" in data["summary"]["error_tables"]
    assert data["tables"]["device_sensor_gps_raw"]["error"] == "Table does not exist"


@pytest.mark.asyncio()
async def test_ai_context_database_exception(test_client: AsyncClient):
    """Test AI context when database throws exception."""
    with patch.object(db_manager, "is_connected", True):
        with patch.object(
            db_manager,
            "get_latest_from_all_tables",
            AsyncMock(side_effect=Exception("Database error")),
        ):
            response = await test_client.get("/ai/context")

    assert response.status_code == 500
    assert "Failed to retrieve context" in response.json()["detail"]


@pytest.mark.asyncio()
async def test_ai_context_active_sensors_detection(test_client: AsyncClient):
    """Test active sensor detection in AI context."""
    mock_table_data = {
        "device_sensor_gps_raw": {
            "data": {"id": 1},
            "row_count": 100,
            "latest_timestamp": datetime.utcnow().isoformat(),
        },
        "device_sensor_accelerometer_raw": {
            "data": {"id": 2},
            "row_count": 200,
            "latest_timestamp": datetime.utcnow().isoformat(),
        },
        "device_health_heartrate_raw": {
            "data": {"id": 3},
            "row_count": 50,
            "latest_timestamp": datetime.utcnow().isoformat(),
        },
        "device_audio_raw": {
            "data": None,
            "row_count": 0,
            "latest_timestamp": None,
        },
        "devices": {
            "data": None,
            "row_count": 0,
            "latest_timestamp": None,
        },
    }

    with patch.object(db_manager, "is_connected", True):
        with patch.object(
            db_manager,
            "get_latest_from_all_tables",
            AsyncMock(return_value=mock_table_data),
        ):
            response = await test_client.get("/ai/context")

    assert response.status_code == 200

    data = response.json()
    assert (
        "3 active: GPS, Accelerometer, Heart Rate" in data["summary"]["active_sensors"]
    )


@pytest.mark.asyncio()
async def test_ai_context_active_processors_detection(test_client: AsyncClient):
    """Test active AI processor detection in AI context."""
    mock_table_data = {
        "media_audio_vad_filtered": {
            "data": {"id": 1},
            "row_count": 10,
            "latest_timestamp": datetime.utcnow().isoformat(),
        },
        "media_text_transcribed_words": {
            "data": {"id": 2},
            "row_count": 20,
            "latest_timestamp": datetime.utcnow().isoformat(),
        },
        "devices": {
            "data": None,
            "row_count": 0,
            "latest_timestamp": None,
        },
    }

    with patch.object(db_manager, "is_connected", True):
        with patch.object(
            db_manager,
            "get_latest_from_all_tables",
            AsyncMock(return_value=mock_table_data),
        ):
            response = await test_client.get("/ai/context")

    assert response.status_code == 200

    data = response.json()
    assert "2 active: VAD, Speech-to-Text" in data["summary"]["active_processors"]


@pytest.mark.asyncio()
async def test_ai_context_latest_activity_calculation(test_client: AsyncClient):
    """Test latest activity time calculation."""
    from datetime import timedelta

    now = datetime.utcnow()
    recent_time = (now - timedelta(seconds=30)).isoformat()
    older_time = (now - timedelta(hours=2)).isoformat()

    mock_table_data = {
        "device_sensor_gps_raw": {
            "data": {"id": 1},
            "row_count": 100,
            "latest_timestamp": recent_time,
        },
        "device_audio_raw": {
            "data": {"id": 2},
            "row_count": 50,
            "latest_timestamp": older_time,
        },
        "devices": {
            "data": None,
            "row_count": 0,
            "latest_timestamp": None,
        },
    }

    with patch.object(db_manager, "is_connected", True):
        with patch.object(
            db_manager,
            "get_latest_from_all_tables",
            AsyncMock(return_value=mock_table_data),
        ):
            response = await test_client.get("/ai/context")

    assert response.status_code == 200

    data = response.json()
    # Should show activity from the most recent table
    assert "ago in device_sensor_gps_raw" in data["summary"]["latest_activity"]
    assert "s ago" in data["summary"]["latest_activity"]  # Should be seconds ago
