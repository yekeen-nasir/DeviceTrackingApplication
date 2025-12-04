"""Device management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from uuid import UUID

from libs.core.storage import Device, User, Command as CommandModel
from libs.core.models import DeviceInfo, CommandType, CommandStatus
from libs.core.logging import setup_logging
from ..db import get_db
from ..auth import get_current_user

logger = setup_logging("tracker-server.routers.devices")

router = APIRouter()

class DeviceList(BaseModel):
    devices: List[DeviceInfo]
    total: int

class MarkLostRequest(BaseModel):
    message: Optional[str] = "This device has been marked as lost. If found, please contact the owner."

@router.get("", response_model=DeviceList)
async def list_devices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """List user's devices."""
    # Get devices
    query = db.query(Device).filter(Device.owner_id == current_user.id)
    total = query.count()
    devices = query.offset(offset).limit(limit).all()
    
    # Convert to response models
    device_list = []
    for device in devices:
        device_list.append(DeviceInfo(
            id=device.id,
            owner_id=device.owner_id,
            display_name=device.display_name,
            platform=device.platform,
            enrolled_at=device.enrolled_at,
            lost=device.lost,
            last_seen_at=device.last_seen_at,
            last_ip=device.last_ip,
            last_asn=device.last_asn,
            last_location=device.last_location,
            meta=device.meta or {}
        ))
    
    return DeviceList(devices=device_list, total=total)

@router.get("/{device_id}", response_model=DeviceInfo)
async def get_device(
    device_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get device details."""
    device = db.query(Device).filter(
        Device.id == device_id,
        Device.owner_id == current_user.id
    ).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    return DeviceInfo(
        id=device.id,
        owner_id=device.owner_id,
        display_name=device.display_name,
        platform=device.platform,
        enrolled_at=device.enrolled_at,
        lost=device.lost,
        last_seen_at=device.last_seen_at,
        last_ip=device.last_ip,
        last_asn=device.last_asn,
        last_location=device.last_location,
        meta=device.meta or {}
    )

@router.post("/{device_id}/lost")
async def mark_device_lost(
    device_id: UUID,
    request: MarkLostRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark device as lost."""
    device = db.query(Device).filter(
        Device.id == device_id,
        Device.owner_id == current_user.id
    ).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    # Mark as lost
    device.lost = True
    
    # Create commands for lost mode
    commands = [
        # Show message
        CommandModel(
            device_id=device.id,
            type=CommandType.SHOW_MESSAGE,
            payload={
                "title": "Device Lost",
                "body": request.message
            },
            status=CommandStatus.QUEUED
        ),
        # Play chime
        CommandModel(
            device_id=device.id,
            type=CommandType.PLAY_CHIME,
            payload={"repeat": 5},
            status=CommandStatus.QUEUED
        ),
        # Increase heartbeat
        CommandModel(
            device_id=device.id,
            type=CommandType.INCREASE_HEARTBEAT,
            payload={"seconds": 30},
            status=CommandStatus.QUEUED
        )
    ]
    
    for cmd in commands:
        db.add(cmd)
    
    db.commit()
    
    logger.info(f"Device {device_id} marked as lost by {current_user.email}")
    
    return {"status": "Device marked as lost", "commands_queued": len(commands)}

@router.post("/{device_id}/found")
async def mark_device_found(
    device_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark device as found."""
    device = db.query(Device).filter(
        Device.id == device_id,
        Device.owner_id == current_user.id
    ).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    # Mark as found
    device.lost = False
    
    # Reset heartbeat to normal
    command = CommandModel(
        device_id=device.id,
        type=CommandType.INCREASE_HEARTBEAT,
        payload={"seconds": 300},  # Back to 5 minutes
        status=CommandStatus.QUEUED
    )
    db.add(command)
    
    db.commit()
    
    logger.info(f"Device {device_id} marked as found by {current_user.email}")
    
    return {"status": "Device marked as found"}
