"""Background tasks and alert processing."""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from typing import Dict, Any

from libs.core.storage import Device, Alert, TelemetryEvent
from libs.core.models import AlertType, AlertSeverity
from libs.core.logging import setup_logging

logger = setup_logging("tracker-server.tasks")

def check_alerts(device_id: str, telemetry: Dict[str, Any], db: Session):
    """
    Check for alert conditions based on telemetry.
    
    Args:
        device_id: Device UUID
        telemetry: Latest telemetry data
        db: Database session
    """
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        return
    
    # Check for new IP/ASN
    if device.last_asn and telemetry.get("asn"):
        if device.last_asn != telemetry["asn"]:
            alert = Alert(
                device_id=device_id,
                type=AlertType.NEW_IP,
                severity=AlertSeverity.WARNING,
                details={
                    "old_asn": device.last_asn,
                    "new_asn": telemetry["asn"],
                    "ip": telemetry.get("ip")
                }
            )
            db.add(alert)
            logger.info(f"Alert created: NEW_IP for device {device_id}")
    
    # Check for new WiFi networks
    if telemetry.get("wifi"):
        # Get recent telemetry to build known networks
        recent_events = db.query(TelemetryEvent).filter(
            TelemetryEvent.device_id == device_id,
            TelemetryEvent.ts >= datetime.utcnow() - timedelta(days=7)
        ).limit(100).all()
        
        known_bssids = set()
        for event in recent_events:
            if event.wifi:
                for network in event.wifi:
                    if "bssid" in network:
                        known_bssids.add(network["bssid"])
        
        # Check for new networks
        for network in telemetry["wifi"]:
            if network.get("bssid") and network["bssid"] not in known_bssids:
                alert = Alert(
                    device_id=device_id,
                    type=AlertType.NEW_WIFI,
                    severity=AlertSeverity.INFO,
                    details={
                        "ssid": network.get("ssid", "Unknown"),
                        "bssid": network["bssid"]
                    }
                )
                db.add(alert)
                logger.info(f"Alert created: NEW_WIFI for device {device_id}")
                break  # Only alert once per telemetry
    
    db.commit()

def check_heartbeat_alerts(db: Session):
    """Check for devices that haven't reported recently."""
    threshold = datetime.utcnow() - timedelta(minutes=15)  # 15 minutes threshold
    
    # Find devices that haven't reported
    devices = db.query(Device).filter(
        Device.lost == False,
        Device.last_seen_at < threshold
    ).all()
    
    for device in devices:
        # Check if we already have an unresolved alert
        existing = db.query(Alert).filter(
            Alert.device_id == device.id,
            Alert.type == AlertType.NO_HEARTBEAT,
            Alert.resolved_at == None
        ).first()
        
        if not existing:
            alert = Alert(
                device_id=device.id,
                type=AlertType.NO_HEARTBEAT,
                severity=AlertSeverity.WARNING,
                details={
                    "last_seen": device.last_seen_at.isoformat() if device.last_seen_at else None,
                    "threshold_minutes": 15
                }
            )
            db.add(alert)
            logger.warning(f"Alert created: NO_HEARTBEAT for device {device.id}")
    
    db.commit()
