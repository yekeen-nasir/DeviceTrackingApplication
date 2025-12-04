"""Report generation endpoints."""

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from libs.core.storage import Device, User, TelemetryEvent, Command as CommandModel
from libs.core.models import Report
from libs.core.logging import setup_logging
from ..db import get_db
from ..auth import get_current_user

logger = setup_logging("tracker-server.routers.reports")

router = APIRouter()

@router.get("/{device_id}")
async def generate_report(
    device_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None)
):
    """Generate device tracking report."""
    # Get device
    device = db.query(Device).filter(
        Device.id == device_id,
        Device.owner_id == current_user.id
    ).first()
    
    if not device:
        raise HTTPException(
            status_code=404,
            detail="Device not found"
        )
    
    # Default date range (last 30 days)
    if not to_date:
        to_date = datetime.utcnow()
    if not from_date:
        from_date = to_date - timedelta(days=30)
    
    # Get telemetry events
    telemetry_events = db.query(TelemetryEvent).filter(
        TelemetryEvent.device_id == device_id,
        TelemetryEvent.ts >= from_date,
        TelemetryEvent.ts <= to_date
    ).order_by(TelemetryEvent.ts.asc()).all()
    
    # Build timeline
    timeline = []
    for event in telemetry_events:
        timeline.append({
            "ts": event.ts.isoformat(),
            "seq": event.seq,
            "hostname": event.hostname,
            "ip": str(event.ip) if event.ip else None,
            "asn": event.asn,
            "location": event.location,
            "wifi": event.wifi,
            "battery": event.battery
        })
    
    # Build WiFi summary
    wifi_map = {}
    for event in telemetry_events:
        if event.wifi:
            for network in event.wifi:
                bssid = network.get("bssid")
                if bssid:
                    if bssid not in wifi_map:
                        wifi_map[bssid] = {
                            "bssid": bssid,
                            "ssids": set(),
                            "first_seen": event.ts,
                            "last_seen": event.ts,
                            "count": 0
                        }
                    wifi_map[bssid]["ssids"].add(network.get("ssid", "Unknown"))
                    wifi_map[bssid]["last_seen"] = event.ts
                    wifi_map[bssid]["count"] += 1
    
    wifi_summary = []
    for bssid, data in wifi_map.items():
        wifi_summary.append({
            "bssid": bssid,
            "ssids": list(data["ssids"]),
            "first_seen": data["first_seen"].isoformat(),
            "last_seen": data["last_seen"].isoformat(),
            "seen_count": data["count"]
        })
    
    # Get commands
    commands = db.query(CommandModel).filter(
        CommandModel.device_id == device_id,
        CommandModel.created_at >= from_date,
        CommandModel.created_at <= to_date
    ).all()
    
    command_history = []
    for cmd in commands:
        command_history.append({
            "id": str(cmd.id),
            "type": cmd.type.value,
            "status": cmd.status.value,
            "created_at": cmd.created_at.isoformat(),
            "payload": cmd.payload
        })
    
    # Build ownership proof
    ownership_proof = {
        "device_id": str(device.id),
        "owner_id": str(device.owner_id),
        "owner_email": current_user.email,
        "enrolled_at": device.enrolled_at.isoformat(),
        "display_name": device.display_name
    }
    
    # Build report
    report = {
        "device": {
            "id": str(device.id),
            "display_name": device.display_name,
            "platform": device.platform.value,
            "lost": device.lost,
            "last_seen_at": device.last_seen_at.isoformat() if device.last_seen_at else None
        },
        "timeline": timeline,
        "wifi_summary": wifi_summary,
        "commands": command_history,
        "ownership_proof": ownership_proof,
        "report_generated": datetime.utcnow().isoformat(),
        "date_range": {
            "from": from_date.isoformat(),
            "to": to_date.isoformat()
        }
    }
    
    logger.info(f"Report generated for device {device_id} by {current_user.email}")
    
    return JSONResponse(content=report)
