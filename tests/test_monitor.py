"""Tests for telemetry monitoring."""

import pytest
from unittest.mock import patch, MagicMock

from apps.tracker_agent.monitor import TelemetryCollector

class TestTelemetryCollector:
    """Test telemetry collection."""
    
    def test_collect_telemetry(self):
        """Test basic telemetry collection."""
        collector = TelemetryCollector()
        
        telemetry = collector.collect_telemetry()
        
        assert telemetry is not None
        assert "seq" in telemetry
        assert "ts" in telemetry
        assert "hostname" in telemetry
        assert "os" in telemetry
        assert "wifi" in telemetry
        assert telemetry["seq"] == 1
    
    def test_sequence_increment(self):
        """Test sequence number increments."""
        collector = TelemetryCollector()
        
        t1 = collector.collect_telemetry()
        t2 = collector.collect_telemetry()
        t3 = collector.collect_telemetry()
        
        assert t1["seq"] == 1
        assert t2["seq"] == 2
        assert t3["seq"] == 3
    
    @patch('platform.system')
    def test_os_detection(self, mock_system):
        """Test OS detection."""
        collector = TelemetryCollector()
        
        mock_system.return_value = "Linux"
        telemetry = collector.collect_telemetry()
        assert "linux" in telemetry["os"].lower()
        
        mock_system.return_value = "Windows"
        collector.seq = 0  # Reset
        telemetry = collector.collect_telemetry()
        assert "windows" in telemetry["os"].lower()
    
    @patch('subprocess.run')
    def test_wifi_scan_linux(self, mock_run):
        """Test WiFi scanning on Linux."""
        collector = TelemetryCollector()
        
        # Mock nmcli output
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "TestNet:aa:bb:cc:dd:ee:ff:75\nHiddenNet:11:22:33:44:55:66:60"
        mock_run.return_value = mock_result
        
        networks = collector._scan_wifi_linux()
        
        assert len(networks) == 2
        assert networks[0]["ssid"] == "TestNet"
        assert networks[0]["bssid"] == "aa:bb:cc:dd:ee:ff"
        assert networks[0]["signal"] == -75
