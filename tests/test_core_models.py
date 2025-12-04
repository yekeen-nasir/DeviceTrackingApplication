"""Tests for core models."""

import pytest
from datetime import datetime
from uuid import UUID
from pydantic import ValidationError

from libs.core.models import (
    WiFiNetwork, Location, TelemetryEvent, DeviceInfo,
    Platform, CommandType, Command, Alert, AlertSeverity
)

class TestModels:
    """Test Pydantic models validation."""
    
    def test_wifi_network_validation(self):
        """Test WiFi network model."""
        # Valid network
        wifi = WiFiNetwork(ssid="TestNet", bssid="aa:bb:cc:dd:ee:ff", signal=-50)
        assert wifi.ssid == "TestNet"
        assert wifi.signal == -50
        
        # Invalid signal strength
        with pytest.raises(ValidationError):
            WiFiNetwork(ssid="Test", bssid="aa:bb:cc:dd:ee:ff", signal=10)
        
        with pytest.raises(ValidationError):
            WiFiNetwork(ssid="Test", bssid="aa:bb:cc:dd:ee:ff", signal=-150)
    
    def test_telemetry_event(self):
        """Test telemetry event model."""
        event = TelemetryEvent(
            seq=1,
            ts=datetime.utcnow(),
            hostname="test-host",
            os="linux",
            wifi=[],
            battery=75
        )
        
        assert event.seq == 1
        assert event.hostname == "test-host"
        assert event.battery == 75
        
        # Invalid battery level
        with pytest.raises(ValidationError):
            TelemetryEvent(
                seq=1,
                ts=datetime.utcnow(),
                hostname="test",
                os="linux",
                battery=150
            )
    
    def test_device_info(self):
        """Test device info model."""
        device = DeviceInfo(
            owner_id=UUID("12345678-1234-5678-1234-567812345678"),
            display_name="Test Device",
            platform=Platform.LINUX
        )
        
        assert device.display_name == "Test Device"
        assert device.platform == Platform.LINUX
        assert device.lost is False
    
    def test_command_model(self):
        """Test command model."""
        cmd = Command(
            device_id=UUID("12345678-1234-5678-1234-567812345678"),
            type=CommandType.SHOW_MESSAGE,
            payload={"title": "Test", "body": "Message"}
        )
        
        assert cmd.type == CommandType.SHOW_MESSAGE
        assert cmd.must_ack is True
        assert cmd.payload["title"] == "Test"
