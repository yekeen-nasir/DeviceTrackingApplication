"""Telemetry ingestion endpoints."""

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Dict, Any

from libs.core.storage import Device, TelemetryEvent
from libs.core.models import TelemetryEvent as TelemetryModel
from libs.core.logging import setup_logging, redact_sensitive
from ..db import get_db
from ..auth import get_current_device
from ..ipgeo import get_ip_location

logger = setup_logging("tracker-server.routers.telemetry")

router = APIRouter()

@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def ingest_telemetry(
    telemetry: TelemetryModel,
    request: Request,
    device: Device = Depends(get_current_device),
    db: Session = Depends(get_db)
):
    """Receive telemetry from device."""
    # Get client IP
    client_ip = request.client.host
    if "x-forwarded-for" in request.headers:
        client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()
    
    # Get IP location
    location_data = await get_ip_location(client_ip)
    
    # Store telemetry event
    event = TelemetryEvent(
        device_id=device.id,
        ts=telemetry.ts,
        seq=telemetry.seq,
        hostname=telemetry.hostname,
        os=telemetry.os,
        wifi=telemetry.wifi if telemetry.wifi else [],
        battery=telemetry.battery,
        ip=client_ip,
        asn=location_data.get("asn"),
        location=location_data
    )
    db.add(event)
    
    # Update device last_seen
    device.last_seen_at = telemetry.ts
    device.last_ip = client_ip
    device.last_asn = location_data.get("asn")
    device.last_location = location_data
    
    db.commit()
    
    # Log telemetry (with sensitive data redacted)
    safe_telemetry = redact_sensitive(telemetry.dict())
    logger.info(f"Telemetry received from {device.id}: seq={telemetry.seq}")
    
    # Check for alerts (simplified)
    from ..tasks import check_alerts
    check_alerts(device.id, telemetry.dict(), db)
    
    return Response(status_code=status.HTTP_202_ACCEPTED)
