"""Tests for storage operations."""

import pytest
import tempfile
from pathlib import Path
from uuid import uuid4
from datetime import datetime

from libs.core.storage import SQLAlchemyStorage
from libs.core.models import Platform

class TestStorage:
    """Test storage operations."""
    
    @pytest.fixture
    def storage(self):
        """Create temporary storage instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            storage = SQLAlchemyStorage(f"sqlite:///{db_path}")
            yield storage
    
    def test_create_get_device(self, storage):
        """Test device creation and retrieval."""
        device_data = {
            "owner_id": uuid4(),
            "display_name": "Test Device",
            "platform": Platform.LINUX,
            "enrolled_at": datetime.utcnow()
        }
        
        # Create device
        device_id = storage.create_device(device_data)
        assert device_id is not None
        
        # Get device
        device = storage.get_device(device_id)
        assert device is not None
        assert device["display_name"] == "Test Device"
        assert device["platform"] == "linux"
    
    def test_store_get_telemetry(self, storage):
        """Test telemetry storage and retrieval."""
        # Create device first
        device_id = storage.create_device({
            "owner_id": uuid4(),
            "display_name": "Test",
            "platform": Platform.LINUX
        })
        
        # Store telemetry
        telemetry = {
            "seq": 1,
            "ts": datetime.utcnow(),
            "hostname": "test-host",
            "os": "linux",
            "wifi": [],
            "battery": 80
        }
        
        success = storage.store_telemetry(device_id, telemetry)
        assert success is True
        
        # Get telemetry
        events = storage.get_telemetry(device_id, limit=10)
        assert len(events) == 1
        assert events[0]["seq"] == 1
        assert events[0]["battery"] == 80
    
    def test_command_operations(self, storage):
        """Test command creation and acknowledgment."""
        # Create device
        device_id = storage.create_device({
            "owner_id": uuid4(),
            "display_name": "Test",
            "platform": Platform.LINUX
        })
        
        # Create command
        command_data = {
            "device_id": device_id,
            "type": "SHOW_MESSAGE",
            "payload": {"title": "Test", "body": "Message"}
        }
        
        command_id = storage.create_command(command_data)
        assert command_id is not None
        
        # Get pending commands
        commands = storage.get_pending_commands(device_id)
        assert len(commands) == 1
        assert commands[0]["type"] == "SHOW_MESSAGE"
        
        # Acknowledge command
        success = storage.ack_command(command_id, "DONE", "Executed successfully")
        assert success is True
        
        # No more pending commands
        commands = storage.get_pending_commands(device_id)
        assert len(commands) == 0
