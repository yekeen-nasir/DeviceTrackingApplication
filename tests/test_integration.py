"""Integration tests for the Tracker system."""

import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
from uuid import uuid4

from libs.core.config import TrackerConfig
from libs.core.storage import SQLAlchemyStorage
from apps.tracker_agent.monitor import TelemetryCollector
from apps.tracker_agent.storage import LocalQueue

class TestIntegration:
    """Integration tests."""
    
    def test_local_queue_operations(self):
        """Test local queue for offline telemetry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "queue.db"
            queue = LocalQueue(db_path)
            
            # Queue should be empty
            assert queue.size() == 0
            
            # Enqueue items
            queue.enqueue({"seq": 1, "data": "test1"})
            queue.enqueue({"seq": 2, "data": "test2"})
            queue.enqueue({"seq": 3, "data": "test3"})
            
            assert queue.size() == 3
            
            # Dequeue items (FIFO)
            item1 = queue.dequeue()
            assert item1["seq"] == 1
            
            item2 = queue.dequeue()
            assert item2["seq"] == 2
            
            assert queue.size() == 1
            
            item3 = queue.dequeue()
            assert item3["seq"] == 3
            
            # Queue should be empty
            assert queue.size() == 0
            assert queue.dequeue() is None
    
    def test_telemetry_to_storage_flow(self):
        """Test telemetry collection to storage flow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup storage
            db_path = Path(tmpdir) / "tracker.db"
            storage = SQLAlchemyStorage(f"sqlite:///{db_path}")
            
            # Create device
            device_id = storage.create_device({
                "owner_id": uuid4(),
                "display_name": "Test Device",
                "platform": "linux"
            })
            
            # Collect telemetry
            collector = TelemetryCollector()
            telemetry = collector.collect_telemetry()
            
            # Store telemetry
            success = storage.store_telemetry(device_id, telemetry)
            assert success is True
            
            # Retrieve and verify
            events = storage.get_telemetry(device_id)
            assert len(events) == 1
            assert events[0]["seq"] == telemetry["seq"]
            assert events[0]["hostname"] == telemetry["hostname"]
