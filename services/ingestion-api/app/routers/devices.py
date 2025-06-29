"""Device management endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import verify_api_key
from app.database import get_db

router = APIRouter(prefix="/devices", tags=["devices"])


class DeviceCreate(BaseModel):
    """Request model for creating a device."""

    device_id: str = Field(..., description="Unique device identifier")
    name: str = Field(..., description="Human-readable device name")
    device_type: str = Field(
        ...,
        description="Type of device",
        pattern="^(mobile_android|mobile_ios|desktop_macos|desktop_linux|desktop_windows|service_scheduler|service_fetcher|service_consumer|browser_extension|other)$",
    )
    platform: str | None = Field(None, description="Platform details")
    model: str | None = Field(None, description="Device model")
    manufacturer: str | None = Field(None, description="Device manufacturer")
    os_version: str | None = Field(None, description="Operating system version")
    app_version: str | None = Field(None, description="App version")
    service_name: str | None = Field(
        None,
        description="For services: name of the service",
    )
    service_config: dict | None = Field(
        None,
        description="For services: configuration data",
    )
    tags: list[str] | None = Field(
        default_factory=list,
        description="Tags for categorization",
    )
    metadata: dict | None = Field(
        default_factory=dict,
        description="Additional metadata",
    )


class DeviceUpdate(BaseModel):
    """Request model for updating a device."""

    name: str | None = Field(None, description="Human-readable device name")
    platform: str | None = Field(None, description="Platform details")
    model: str | None = Field(None, description="Device model")
    manufacturer: str | None = Field(None, description="Device manufacturer")
    os_version: str | None = Field(None, description="Operating system version")
    app_version: str | None = Field(None, description="App version")
    service_config: dict | None = Field(
        None,
        description="For services: configuration data",
    )
    tags: list[str] | None = Field(None, description="Tags for categorization")
    metadata: dict | None = Field(None, description="Additional metadata")
    is_active: bool | None = Field(None, description="Whether device is active")


class DeviceResponse(BaseModel):
    """Response model for device data."""

    device_id: str
    name: str
    device_type: str
    platform: str | None
    model: str | None
    manufacturer: str | None
    os_version: str | None
    app_version: str | None
    service_name: str | None
    service_config: dict | None
    first_seen_at: datetime
    last_seen_at: datetime
    is_active: bool
    tags: list[str]
    metadata: dict
    created_at: datetime
    updated_at: datetime


class DeviceActivityResponse(BaseModel):
    """Response model for device activity summary."""

    device_id: str
    name: str
    device_type: str
    service_name: str | None
    is_active: bool
    last_data_received: datetime | None
    last_seen_at: datetime
    status: str  # active, idle, inactive, offline


@router.get("/", response_model=list[DeviceResponse])
async def list_devices(
    device_type: str | None = Query(None, description="Filter by device type"),
    service_name: str | None = Query(None, description="Filter by service name"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """List all registered devices with optional filtering."""
    query = "SELECT * FROM devices WHERE 1=1"
    params = {}

    if device_type:
        query += " AND device_type = :device_type"
        params["device_type"] = device_type

    if service_name:
        query += " AND service_name = :service_name"
        params["service_name"] = service_name

    if is_active is not None:
        query += " AND is_active = :is_active"
        params["is_active"] = is_active

    query += " ORDER BY last_seen_at DESC"

    result = await db.execute(text(query), params)
    devices = result.fetchall()

    return [
        DeviceResponse(
            device_id=row.device_id,
            name=row.name,
            device_type=row.device_type,
            platform=row.platform,
            model=row.model,
            manufacturer=row.manufacturer,
            os_version=row.os_version,
            app_version=row.app_version,
            service_name=row.service_name,
            service_config=row.service_config,
            first_seen_at=row.first_seen_at,
            last_seen_at=row.last_seen_at,
            is_active=row.is_active,
            tags=row.tags or [],
            metadata=row.metadata or {},
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in devices
    ]


@router.get("/activity", response_model=list[DeviceActivityResponse])
async def get_device_activity(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """Get activity summary for all devices."""
    query = """
        SELECT
            device_id,
            name,
            device_type,
            service_name,
            is_active,
            last_data_received,
            last_seen_at,
            status
        FROM device_activity_summary
        ORDER BY last_data_received DESC NULLS LAST
    """

    result = await db.execute(text(query))
    activities = result.fetchall()

    return [
        DeviceActivityResponse(
            device_id=row.device_id,
            name=row.name,
            device_type=row.device_type,
            service_name=row.service_name,
            is_active=row.is_active,
            last_data_received=row.last_data_received,
            last_seen_at=row.last_seen_at,
            status=row.status,
        )
        for row in activities
    ]


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """Get details for a specific device."""
    query = "SELECT * FROM devices WHERE device_id = :device_id"
    result = await db.execute(text(query), {"device_id": device_id})
    device = result.fetchone()

    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    return DeviceResponse(
        device_id=device.device_id,
        name=device.name,
        device_type=device.device_type,
        platform=device.platform,
        model=device.model,
        manufacturer=device.manufacturer,
        os_version=device.os_version,
        app_version=device.app_version,
        service_name=device.service_name,
        service_config=device.service_config,
        first_seen_at=device.first_seen_at,
        last_seen_at=device.last_seen_at,
        is_active=device.is_active,
        tags=device.tags or [],
        metadata=device.metadata or {},
        created_at=device.created_at,
        updated_at=device.updated_at,
    )


@router.post("/", response_model=DeviceResponse, status_code=201)
async def create_device(
    device: DeviceCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """Register a new device."""
    query = """
        INSERT INTO devices (
            device_id, name, device_type, platform, model, manufacturer,
            os_version, app_version, service_name, service_config, tags, metadata
        ) VALUES (
            :device_id, :name, :device_type, :platform, :model, :manufacturer,
            :os_version, :app_version, :service_name, :service_config, :tags, :metadata
        )
        ON CONFLICT (device_id) DO UPDATE SET
            name = EXCLUDED.name,
            last_seen_at = NOW(),
            updated_at = NOW()
        RETURNING *
    """

    params = {
        "device_id": device.device_id,
        "name": device.name,
        "device_type": device.device_type,
        "platform": device.platform,
        "model": device.model,
        "manufacturer": device.manufacturer,
        "os_version": device.os_version,
        "app_version": device.app_version,
        "service_name": device.service_name,
        "service_config": device.service_config,
        "tags": device.tags,
        "metadata": device.metadata,
    }

    result = await db.execute(text(query), params)
    await db.commit()
    created_device = result.fetchone()

    return DeviceResponse(
        device_id=created_device.device_id,
        name=created_device.name,
        device_type=created_device.device_type,
        platform=created_device.platform,
        model=created_device.model,
        manufacturer=created_device.manufacturer,
        os_version=created_device.os_version,
        app_version=created_device.app_version,
        service_name=created_device.service_name,
        service_config=created_device.service_config,
        first_seen_at=created_device.first_seen_at,
        last_seen_at=created_device.last_seen_at,
        is_active=created_device.is_active,
        tags=created_device.tags or [],
        metadata=created_device.metadata or {},
        created_at=created_device.created_at,
        updated_at=created_device.updated_at,
    )


@router.patch("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: str,
    update: DeviceUpdate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """Update device information."""
    # Build dynamic update query
    update_fields = []
    params = {"device_id": device_id}

    for field, value in update.dict(exclude_unset=True).items():
        update_fields.append(f"{field} = :{field}")
        params[field] = value

    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    query = f"""
        UPDATE devices
        SET {', '.join(update_fields)}, updated_at = NOW()
        WHERE device_id = :device_id
        RETURNING *
    """

    result = await db.execute(text(query), params)
    await db.commit()
    updated_device = result.fetchone()

    if not updated_device:
        raise HTTPException(status_code=404, detail="Device not found")

    return DeviceResponse(
        device_id=updated_device.device_id,
        name=updated_device.name,
        device_type=updated_device.device_type,
        platform=updated_device.platform,
        model=updated_device.model,
        manufacturer=updated_device.manufacturer,
        os_version=updated_device.os_version,
        app_version=updated_device.app_version,
        service_name=updated_device.service_name,
        service_config=updated_device.service_config,
        first_seen_at=updated_device.first_seen_at,
        last_seen_at=updated_device.last_seen_at,
        is_active=updated_device.is_active,
        tags=updated_device.tags or [],
        metadata=updated_device.metadata or {},
        created_at=updated_device.created_at,
        updated_at=updated_device.updated_at,
    )


@router.delete("/{device_id}", status_code=204)
async def delete_device(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    """Delete a device (soft delete by marking inactive)."""
    query = """
        UPDATE devices
        SET is_active = false, updated_at = NOW()
        WHERE device_id = :device_id
    """

    result = await db.execute(text(query), {"device_id": device_id})
    await db.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Device not found")
