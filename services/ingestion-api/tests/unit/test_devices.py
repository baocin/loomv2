"""Unit tests for device management endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio()
async def test_list_devices(client, mock_db_session):
    """Test listing all devices."""
    # Mock database response
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [
        MagicMock(
            device_id="test-device-1",
            name="Test Device 1",
            device_type="mobile_android",
            platform="Android",
            model="Pixel 7",
            manufacturer="Google",
            os_version="13",
            app_version="1.0.0",
            service_name=None,
            service_config=None,
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
            is_active=True,
            tags=["test", "mobile"],
            metadata={"test": "data"},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        ),
        MagicMock(
            device_id="email-fetcher-account-1",
            name="Primary Email Fetcher",
            device_type="service_fetcher",
            platform=None,
            model=None,
            manufacturer=None,
            os_version=None,
            app_version=None,
            service_name="email-fetcher",
            service_config={"account": "account_1"},
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
            is_active=True,
            tags=[],
            metadata={},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        ),
    ]

    mock_db_session.execute = AsyncMock(return_value=mock_result)

    response = client.get("/devices/")
    assert response.status_code == 200

    devices = response.json()
    assert len(devices) == 2
    assert devices[0]["device_id"] == "test-device-1"
    assert devices[0]["device_type"] == "mobile_android"
    assert devices[1]["device_id"] == "email-fetcher-account-1"
    assert devices[1]["service_name"] == "email-fetcher"


@pytest.mark.asyncio()
async def test_list_devices_with_filters(client, mock_db_session):
    """Test listing devices with filters."""
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    # Test with device_type filter
    response = client.get("/devices/?device_type=service_fetcher")
    assert response.status_code == 200

    # Verify the query was called with correct parameters
    mock_db_session.execute.assert_called()
    call_args = mock_db_session.execute.call_args
    assert "device_type = :device_type" in call_args[0][0].text
    assert call_args[0][1]["device_type"] == "service_fetcher"


@pytest.mark.asyncio()
async def test_get_device(client, mock_db_session):
    """Test getting a specific device."""
    mock_result = MagicMock()
    mock_result.fetchone.return_value = MagicMock(
        device_id="test-device-1",
        name="Test Device 1",
        device_type="mobile_android",
        platform="Android",
        model="Pixel 7",
        manufacturer="Google",
        os_version="13",
        app_version="1.0.0",
        service_name=None,
        service_config=None,
        first_seen_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
        is_active=True,
        tags=["test"],
        metadata={"test": "data"},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    mock_db_session.execute = AsyncMock(return_value=mock_result)

    response = client.get("/devices/test-device-1")
    assert response.status_code == 200

    device = response.json()
    assert device["device_id"] == "test-device-1"
    assert device["name"] == "Test Device 1"
    assert device["device_type"] == "mobile_android"


@pytest.mark.asyncio()
async def test_get_device_not_found(client, mock_db_session):
    """Test getting a non-existent device."""
    mock_result = MagicMock()
    mock_result.fetchone.return_value = None
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    response = client.get("/devices/non-existent")
    assert response.status_code == 404
    assert response.json()["detail"] == "Device not found"


@pytest.mark.asyncio()
async def test_create_device(client, mock_db_session):
    """Test creating a new device."""
    device_data = {
        "device_id": "new-device-1",
        "name": "New Test Device",
        "device_type": "mobile_android",
        "platform": "Android",
        "model": "Pixel 8",
        "tags": ["new", "test"],
    }

    mock_result = MagicMock()
    mock_result.fetchone.return_value = MagicMock(
        device_id="new-device-1",
        name="New Test Device",
        device_type="mobile_android",
        platform="Android",
        model="Pixel 8",
        manufacturer=None,
        os_version=None,
        app_version=None,
        service_name=None,
        service_config=None,
        first_seen_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
        is_active=True,
        tags=["new", "test"],
        metadata={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    mock_db_session.execute = AsyncMock(return_value=mock_result)
    mock_db_session.commit = AsyncMock()

    response = client.post("/devices/", json=device_data)
    assert response.status_code == 201

    created_device = response.json()
    assert created_device["device_id"] == "new-device-1"
    assert created_device["name"] == "New Test Device"
    assert created_device["tags"] == ["new", "test"]


@pytest.mark.asyncio()
async def test_update_device(client, mock_db_session):
    """Test updating a device."""
    update_data = {
        "name": "Updated Device Name",
        "is_active": False,
        "tags": ["updated"],
    }

    mock_result = MagicMock()
    mock_result.fetchone.return_value = MagicMock(
        device_id="test-device-1",
        name="Updated Device Name",
        device_type="mobile_android",
        platform="Android",
        model="Pixel 7",
        manufacturer="Google",
        os_version="13",
        app_version="1.0.0",
        service_name=None,
        service_config=None,
        first_seen_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
        is_active=False,
        tags=["updated"],
        metadata={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    mock_db_session.execute = AsyncMock(return_value=mock_result)
    mock_db_session.commit = AsyncMock()

    response = client.patch("/devices/test-device-1", json=update_data)
    assert response.status_code == 200

    updated_device = response.json()
    assert updated_device["name"] == "Updated Device Name"
    assert updated_device["is_active"] is False
    assert updated_device["tags"] == ["updated"]


@pytest.mark.asyncio()
async def test_delete_device(client, mock_db_session):
    """Test soft deleting a device."""
    mock_result = MagicMock()
    mock_result.rowcount = 1
    mock_db_session.execute = AsyncMock(return_value=mock_result)
    mock_db_session.commit = AsyncMock()

    response = client.delete("/devices/test-device-1")
    assert response.status_code == 204


@pytest.mark.asyncio()
async def test_delete_device_not_found(client, mock_db_session):
    """Test deleting a non-existent device."""
    mock_result = MagicMock()
    mock_result.rowcount = 0
    mock_db_session.execute = AsyncMock(return_value=mock_result)
    mock_db_session.commit = AsyncMock()

    response = client.delete("/devices/non-existent")
    assert response.status_code == 404


@pytest.mark.asyncio()
async def test_get_device_activity(client, mock_db_session):
    """Test getting device activity summary."""
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [
        MagicMock(
            device_id="test-device-1",
            name="Test Device 1",
            device_type="mobile_android",
            service_name=None,
            is_active=True,
            last_data_received=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
            status="active",
        ),
        MagicMock(
            device_id="test-device-2",
            name="Test Device 2",
            device_type="desktop_macos",
            service_name=None,
            is_active=True,
            last_data_received=None,
            last_seen_at=datetime.now(UTC),
            status="offline",
        ),
    ]

    mock_db_session.execute = AsyncMock(return_value=mock_result)

    response = client.get("/devices/activity")
    assert response.status_code == 200

    activities = response.json()
    assert len(activities) == 2
    assert activities[0]["status"] == "active"
    assert activities[1]["status"] == "offline"
    assert activities[1]["last_data_received"] is None
