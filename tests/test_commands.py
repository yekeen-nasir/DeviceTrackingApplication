"""Tests for command execution."""

import pytest
from unittest.mock import patch, MagicMock

from apps.tracker_agent.commands import CommandExecutor

class TestCommandExecutor:
    """Test command execution."""
    
    def test_ping_command(self):
        """Test PING command execution."""
        executor = CommandExecutor()
        
        command = {
            "type": "PING",
            "payload": {}
        }
        
        success, details = executor.execute(command)
        
        assert success is True
        assert "Pong" in details
    
    def test_expired_command(self):
        """Test expired command rejection."""
        executor = CommandExecutor()
        
        command = {
            "type": "PING",
            "payload": {},
            "expires_at": "2020-01-01T00:00:00"  # Past date
        }
        
        success, details = executor.execute(command)
        
        assert success is False
        assert "expired" in details.lower()
    
    @patch('subprocess.run')
    def test_show_message_linux(self, mock_run):
        """Test SHOW_MESSAGE on Linux."""
        executor = CommandExecutor()
        executor.system = "linux"
        
        command = {
            "type": "SHOW_MESSAGE",
            "payload": {
                "title": "Test Alert",
                "body": "This is a test"
            }
        }
        
        mock_run.return_value = MagicMock(returncode=0)
        success, details = executor.execute(command)
        
        assert success is True
        assert "notify-send" in details or "zenity" in details
        
        # Verify subprocess was called
        mock_run.assert_called()
        call_args = mock_run.call_args[0][0]
        assert "notify-send" in call_args or "zenity" in call_args
