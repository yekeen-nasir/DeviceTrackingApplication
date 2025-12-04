"""Storage interface and SQLAlchemy implementation."""

import json
from datetime import datetime
from typing import List, Optional, Dict, Any, Protocol
from uuid import UUID, uuid4
from pathlib import Path
from contextlib import contextmanager

from sqlalchemy import (
    create_engine, Column, String, Boolean, DateTime, Integer, Float,
    ForeignKey, Text, JSON, Enum, Index, and_, or_
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, INET
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship

from .models import Platform, CommandType, CommandStatus, AlertType, AlertSeverity
from .errors import StorageError

Base = declarative_base()


# -------------------------------------------------------------------------
# SQLAlchemy Models
# -------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    role = Column(String(50), default="user")

    devices = relationship("Device", back_populates="owner")
    enrollment_tokens = relationship("EnrollmentToken", back_populates="owner")


class Device(Base):
    __tablename__ = "devices"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    owner_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    display_name = Column(String(255), nullable=False)
    platform = Column(Enum(Platform), nullable=False)
    enrolled_at = Column(DateTime, default=datetime.utcnow)
    lost = Column(Boolean, default=False)
    last_seen_at = Column(DateTime)
    last_ip = Column(INET)
    last_asn = Column(Integer)
    last_location = Column(JSON)
    meta = Column(JSON, default={})

    owner = relationship("User", back_populates="devices")
    credentials = relationship("AgentCredential", back_populates="device")
    telemetry_events = relationship("TelemetryEvent", back_populates="device")
    commands = relationship("Command", back_populates="device")
    alerts = relationship("Alert", back_populates="device")

    __table_args__ = (
        Index("idx_devices_owner_id", "owner_id"),
        Index("idx_devices_last_seen_at", "last_seen_at"),
    )


class AgentCredential(Base):
    __tablename__ = "agent_credentials"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    device_id = Column(PG_UUID(as_uuid=True), ForeignKey("devices.id"), nullable=False)
    public_key = Column(Text, nullable=False)
    device_token = Column(String(255), unique=True, nullable=False)
    issued_at = Column(DateTime, default=datetime.utcnow)
    revoked = Column(Boolean, default=False)

    device = relationship("Device", back_populates="credentials")


class TelemetryEvent(Base):
    __tablename__ = "telemetry_events"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    device_id = Column(PG_UUID(as_uuid=True), ForeignKey("devices.id"), nullable=False)
    ts = Column(DateTime, nullable=False)
    seq = Column(Integer, nullable=False)
    hostname = Column(String(255))
    os = Column(String(100))
    wifi = Column(JSON, default=[])
    battery = Column(Integer)
    ip = Column(INET)
    asn = Column(Integer)
    location = Column(JSON)

    device = relationship("Device", back_populates="telemetry_events")

    __table_args__ = (
        Index("idx_telemetry_device_ts", "device_id", "ts"),
    )


class Command(Base):
    __tablename__ = "commands"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    device_id = Column(PG_UUID(as_uuid=True), ForeignKey("devices.id"), nullable=False)
    type = Column(Enum(CommandType), nullable=False)
    payload = Column(JSON, default={})
    status = Column(Enum(CommandStatus), default=CommandStatus.QUEUED)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    must_ack = Column(Boolean, default=True)

    device = relationship("Device", back_populates="commands")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    device_id = Column(PG_UUID(as_uuid=True), ForeignKey("devices.id"), nullable=False)
    type = Column(Enum(AlertType), nullable=False)
    severity = Column(Enum(AlertSeverity), nullable=False)
    details = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime)

    device = relationship("Device", back_populates="alerts")


class EnrollmentToken(Base):
    __tablename__ = "enrollment_tokens"

    token = Column(String(255), primary_key=True)
    owner_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)

    owner = relationship("User", back_populates="enrollment_tokens")


# -------------------------------------------------------------------------
# Storage Interface (Protocol)
# -------------------------------------------------------------------------

class StorageInterface(Protocol):
    """Protocol defining storage operations."""

    # def create_device(self, device_data: Dict[str, Any]) -> UUID:
    #     ...

    # def get_device(self, device_id: UUID) -> Optional[Dict[str, Any]]:
    #     ...

    # def update_device(self, device_id: UUID, updates: Dict[str, Any]) -> bool:
    #     ...

    # def store_telemetry(self, device_id: UUID, telemetry: Dict[str, Any]) -> bool:
    #     ...

    # def get_telemetry(self, device_id: UUID, limit: int = 10) -> List[Dict[str, Any]]:
    #     ...

    # def create_command(self, command_data: Dict[str, Any]) -> UUID:
    #     ...

    # def get_pending_commands(self, device_id: UUID) -> List[Dict[str, Any]]:
    #     ...

    def ack_command(self, command_id: UUID, status: str, details: Optional[str]) -> bool:
        """Acknowledge command execution."""
        with self.get_session() as session:
            command = session.query(Command).filter(Command.id == command_id).first()
            if not command:
                return False

            command.status = CommandStatus(status)
            if details:
                # Add details into payload safely
                payload = command.payload or {}
                payload["ack_details"] = details
                command.payload = payload

            return True

    def update_device(self, device_id: UUID, updates: Dict[str, Any]) -> bool:
        """Update a device record."""
        with self.get_session() as session:
            device = session.query(Device).filter(Device.id == device_id).first()
            if not device:
                return False
            
            for key, value in updates.items():
                if hasattr(device, key):
                    setattr(device, key, value)
            
            return True


# -------------------------------------------------------------------------
# SQLAlchemy Storage Implementation
# -------------------------------------------------------------------------

class SQLAlchemyStorage:
    """SQLAlchemy implementation of storage interface."""

    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    @contextmanager
    def get_session(self):
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise StorageError(f"Database operation failed: {e}")
        finally:
            session.close()

    # ------------------------ Device Ops ------------------------

    def create_device(self, device_data: Dict[str, Any]) -> UUID:
        with self.get_session() as session:
            device = Device(**device_data)
            session.add(device)
            session.flush()
            return device.id

    def get_device(self, device_id: UUID) -> Optional[Dict[str, Any]]:
        with self.get_session() as session:
            device = session.query(Device).filter(Device.id == device_id).first()
            if not device:
                return None

            return {
                "id": str(device.id),
                "owner_id": str(device.owner_id),
                "display_name": device.display_name,
                "platform": device.platform.value,
                "enrolled_at": device.enrolled_at.isoformat() if device.enrolled_at else None,
                "lost": device.lost,
                "last_seen_at": device.last_seen_at.isoformat() if device.last_seen_at else None,
                "last_ip": str(device.last_ip) if device.last_ip else None,
                "last_asn": device.last_asn,
                "last_location": device.last_location,
                "meta": device.meta
            }

    def update_device(self, device_id: UUID, updates: Dict[str, Any]) -> bool:
        with self.get_session() as session:
            device = session.query(Device).filter(Device.id == device_id).first()
            if not device:
                return False

            for key, val in updates.items():
                if hasattr(device, key):
                    setattr(device, key, val)

            return True

    # ------------------------ Telemetry ------------------------

    def store_telemetry(self, device_id: UUID, telemetry: Dict[str, Any]) -> bool:
        with self.get_session() as session:
            event = TelemetryEvent(device_id=device_id, **telemetry)
            session.add(event)

            # Update device last activity
            device = session.query(Device).filter(Device.id == device_id).first()
            if device:
                device.last_seen_at = telemetry.get("ts", datetime.utcnow())
                device.last_ip = telemetry.get("ip", device.last_ip)
                device.last_location = telemetry.get("location", device.last_location)
                device.last_asn = telemetry.get("asn", device.last_asn)

            return True

    def get_telemetry(self, device_id: UUID, limit: int = 10) -> List[Dict[str, Any]]:
        with self.get_session() as session:
            events = (
                session.query(TelemetryEvent)
                .filter(TelemetryEvent.device_id == device_id)
                .order_by(TelemetryEvent.ts.desc())
                .limit(limit)
                .all()
            )

            return [
                {
                    "id": str(e.id),
                    "device_id": str(e.device_id),
                    "ts": e.ts.isoformat(),
                    "seq": e.seq,
                    "hostname": e.hostname,
                    "os": e.os,
                    "wifi": e.wifi,
                    "battery": e.battery,
                    "ip": str(e.ip) if e.ip else None,
                    "asn": e.asn,
                    "location": e.location,
                }
                for e in events
            ]

    # ------------------------ Commands ------------------------

    def create_command(self, command_data: Dict[str, Any]) -> UUID:
        with self.get_session() as session:
            command = Command(**command_data)
            session.add(command)
            session.flush()
            return command.id

    def get_pending_commands(self, device_id: UUID) -> List[Dict[str, Any]]:
        with self.get_session() as session:
            now = datetime.utcnow()
            cmds = (
                session.query(Command)
                .filter(
                    and_(
                        Command.device_id == device_id,
                        Command.status == CommandStatus.QUEUED,
                        or_(Command.expires_at.is_(None), Command.expires_at > now)
                    )
                )
                .all()
            )

            return [
                {
                    "id": str(c.id),
                    "type": c.type.value,
                    "payload": c.payload,
                    "expires_at": c.expires_at.isoformat() if c.expires_at else None,
                    "must_ack": c.must_ack
                }
                for c in cmds
            ]

    def ack_command(self, command_id: UUID, status: str, details: Optional[str]) -> bool:
        with self.get_session() as session:
            command = session.query(Command).filter(Command.id == command_id).first()
            if not command:
                return False

            command.status = CommandStatus(status)
            if details:
                command.payload = {**command.payload, "ack_details": details}

            return True
