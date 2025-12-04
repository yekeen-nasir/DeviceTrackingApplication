"""Command management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from uuid import UUID

from libs.core.storage import Device, Command as CommandModel
from libs.core.models import Command, CommandAck, CommandType, CommandStatus
from libs.core.logging import setup_logging
from ..db import get_db
from ..auth import get_current_device

logger = setup_logging("tracker-server.routers.commands")

router = APIRouter()

class CommandList(BaseModel):
    commands: List[Command]

@router.get("/devices/{device_id}/commands", response_model=CommandList)
async def get_device_commands(
    device_id: UUID,
    device: Device = Depends(get_current_device),
    db: Session = Depends(get_db)
):
    """Get pending commands for device."""
    # Verify device ID matches authenticated device
    if str(device.id) != str(device_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Get pending commands
    now = datetime.utcnow()
    commands = db.query(CommandModel).filter(
        CommandModel.device_id == device_id,
        CommandModel.status == CommandStatus.QUEUED,
        (CommandModel.expires_at == None) | (CommandModel.expires_at > now)
    ).all()
    
    # Convert to response models
    command_list = []
    for cmd in commands:
        command_list.append(Command(
            id=cmd.id,
            device_id=cmd.device_id,
            type=cmd.type,
            payload=cmd.payload or {},
            status=cmd.status,
            created_at=cmd.created_at,
            expires_at=cmd.expires_at,
            must_ack=cmd.must_ack
        ))
        
        # Mark as acknowledged if required
        if cmd.must_ack:
            cmd.status = CommandStatus.ACKED
    
    db.commit()
    
    logger.info(f"Device {device_id} polled {len(command_list)} commands")
    
    return CommandList(commands=command_list)

@router.post("/commands/{command_id}/ack")
async def acknowledge_command(
    command_id: UUID,
    ack: CommandAck,
    device: Device = Depends(get_current_device),
    db: Session = Depends(get_db)
):
    """Acknowledge command execution."""
    # Find command
    command = db.query(CommandModel).filter(
        CommandModel.id == command_id,
        CommandModel.device_id == device.id
    ).first()
    
    if not command:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Command not found"
        )
    
    # Update status
    command.status = ack.status
    if ack.details:
        command.payload = {**(command.payload or {}), "ack_details": ack.details}
    
    db.commit()
    
    logger.info(f"Command {command_id} acknowledged: {ack.status}")
    
    return {"status": "acknowledged"}
