"""Service installation and management."""

import os
import sys
import platform
import subprocess
from pathlib import Path
from typing import Optional

from libs.core.config import TrackerConfig
from libs.core.logging import setup_logging

logger = setup_logging("tracker-agent.service")

class ServiceManager:
    """Manages agent as a system service."""
    
    def __init__(self, config: TrackerConfig):
        """Initialize service manager."""
        self.config = config
        self.system = platform.system().lower()
    
    def install(self):
        """Install agent as a service."""
        if self.system == "linux":
            self._install_systemd()
        elif self.system == "darwin":
            self._install_launchd()
        elif self.system == "windows":
            self._install_windows_service()
        else:
            raise NotImplementedError(f"Service installation not supported on {self.system}")
    
    def uninstall(self):
        """Uninstall agent service."""
        if self.system == "linux":
            self._uninstall_systemd()
        elif self.system == "darwin":
            self._uninstall_launchd()
        elif self.system == "windows":
            self._uninstall_windows_service()
        else:
            raise NotImplementedError(f"Service uninstallation not supported on {self.system}")
    
    def status(self) -> str:
        """Get service status."""
        if self.system == "linux":
            return self._status_systemd()
        elif self.system == "darwin":
            return self._status_launchd()
        elif self.system == "windows":
            return self._status_windows_service()
        else:
            return "unknown"
    
    def _install_systemd(self):
        """Install systemd user service on Linux."""
        service_dir = Path.home() / ".config" / "systemd" / "user"
        service_dir.mkdir(parents=True, exist_ok=True)
        
        service_file = service_dir / "tracker-agent.service"
        
        # Get Python and script paths
        python_path = sys.executable
        agent_path = sys.argv[0]  # Current script path
        
        service_content = f"""[Unit]
Description=Tracker Device Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart={python_path} {agent_path} run
Restart=always
RestartSec=30
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
"""
        
        # Write service file
        service_file.write_text(service_content)
        
        # Reload systemd and enable service
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
        subprocess.run(["systemctl", "--user", "enable", "tracker-agent.service"], check=True)
        subprocess.run(["systemctl", "--user", "start", "tracker-agent.service"], check=True)
        
        logger.info("Systemd service installed and started")
    
    def _uninstall_systemd(self):
        """Uninstall systemd service."""
        subprocess.run(["systemctl", "--user", "stop", "tracker-agent.service"])
        subprocess.run(["systemctl", "--user", "disable", "tracker-agent.service"])
        
        service_file = Path.home() / ".config" / "systemd" / "user" / "tracker-agent.service"
        if service_file.exists():
            service_file.unlink()
        
        subprocess.run(["systemctl", "--user", "daemon-reload"])
        logger.info("Systemd service uninstalled")
    
    def _status_systemd(self) -> str:
        """Get systemd service status."""
        try:
            result = subprocess.run(
                ["systemctl", "--user", "is-active", "tracker-agent.service"],
                capture_output=True,
                text=True
            )
            return result.stdout.strip()
        except Exception:
            return "unknown"
    
    def _install_launchd(self):
        """Install launchd service on macOS."""
        plist_dir = Path.home() / "Library" / "LaunchAgents"
        plist_dir.mkdir(parents=True, exist_ok=True)
        
        plist_file = plist_dir / "com.tracker.agent.plist"
        
        python_path = sys.executable
        agent_path = sys.argv[0]
        
        plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.tracker.agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>{agent_path}</string>
        <string>run</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{str(self.config.data_dir)}/agent.log</string>
    <key>StandardErrorPath</key>
    <string>{str(self.config.data_dir)}/agent-error.log</string>
</dict>
</plist>"""
        
        plist_file.write_text(plist_content)
        
        subprocess.run(["launchctl", "load", str(plist_file)], check=True)
        logger.info("LaunchAgent installed and started")
    
    def _uninstall_launchd(self):
        """Uninstall launchd service."""
        plist_file = Path.home() / "Library" / "LaunchAgents" / "com.tracker.agent.plist"
        
        if plist_file.exists():
            subprocess.run(["launchctl", "unload", str(plist_file)])
            plist_file.unlink()
        
        logger.info("LaunchAgent uninstalled")
    
    def _status_launchd(self) -> str:
        """Get launchd service status."""
        try:
            result = subprocess.run(
                ["launchctl", "list", "com.tracker.agent"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return "active"
            return "inactive"
        except Exception:
            return "unknown"
    
    def _install_windows_service(self):
        """Install Windows service."""
        # This would require pywin32 or similar
        raise NotImplementedError("Windows service installation requires pywin32")
    
    def _uninstall_windows_service(self):
        """Uninstall Windows service."""
        raise NotImplementedError("Windows service uninstallation requires pywin32")
    
    def _status_windows_service(self) -> str:
        """Get Windows service status."""
        return "unknown"
