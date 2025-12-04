import platform
import socket
import subprocess
import json
import re
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

from libs.core.models import TelemetryEvent, WiFiNetwork
from libs.core.logging import setup_logging

logger = setup_logging("tracker-agent.monitor")

class TelemetryCollector:
    """Collects system telemetry from the device."""
    
    def __init__(self):
        self.seq = 0
        self._load_sequence()
    
    def _load_sequence(self):
        """Load sequence number from persistent storage."""
        seq_file = Path.home() / ".local" / "share" / "tracker" / "sequence"
        if seq_file.exists():
            try:
                self.seq = int(seq_file.read_text())
            except Exception:
                self.seq = 0
    
    def _save_sequence(self):
        """Save sequence number to persistent storage."""
        seq_file = Path.home() / ".local" / "share" / "tracker" / "sequence"
        seq_file.parent.mkdir(parents=True, exist_ok=True)
        seq_file.write_text(str(self.seq))
    
    def collect_telemetry(self) -> Dict[str, Any]:
        """
        Collect all telemetry from the system.
        
        Returns:
            Dictionary containing telemetry data
        """
        self.seq += 1
        self._save_sequence()
        
        telemetry = {
            "seq": self.seq,
            "ts": datetime.utcnow().isoformat() + "Z",
            "hostname": self._get_hostname(),
            "os": self._get_os_info(),
            "wifi": self._scan_wifi(),
            "battery": self._get_battery_level(),
            "meta": {}
        }
        
        logger.info(f"Collected telemetry seq={self.seq}")
        return telemetry
    
    def _get_hostname(self) -> str:
        """Get system hostname."""
        try:
            return socket.gethostname()
        except Exception as e:
            logger.error(f"Failed to get hostname: {e}")
            return "unknown"
    
    def _get_os_info(self) -> str:
        """Get operating system information."""
        system = platform.system().lower()
        version = platform.release()
        return f"{system}-{version}"
    
    def _scan_wifi(self) -> List[Dict[str, Any]]:
        """
        Scan for WiFi networks (platform-specific).
        
        Returns:
            List of WiFi network information
        """
        system = platform.system().lower()
        
        if system == "linux":
            return self._scan_wifi_linux()
        elif system == "darwin":  # macOS
            return self._scan_wifi_macos()
        elif system == "windows":
            return self._scan_wifi_windows()
        else:
            logger.warning(f"WiFi scanning not implemented for {system}")
            return []
    
    def _scan_wifi_linux(self) -> List[Dict[str, Any]]:
        """Scan WiFi on Linux using nmcli or iwlist."""
        networks = []
        
        try:
            # Try nmcli first (NetworkManager)
            result = subprocess.run(
                ["nmcli", "-t", "-f", "SSID,BSSID,SIGNAL", "dev", "wifi"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = line.split(':')
                        if len(parts) >= 3:
                            networks.append({
                                "ssid": parts[0] or "Hidden",
                                "bssid": parts[1],
                                "signal": -int(parts[2]) if parts[2] else -100
                            })
        except (subprocess.SubprocessError, FileNotFoundError):
            # Try iwlist as fallback
            try:
                result = subprocess.run(
                    ["sudo", "iwlist", "scan"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    current_network = {}
                    for line in result.stdout.split('\n'):
                        if "Address:" in line:
                            match = re.search(r'Address: ([\w:]+)', line)
                            if match:
                                if current_network:
                                    networks.append(current_network)
                                current_network = {"bssid": match.group(1)}
                        elif "ESSID:" in line:
                            match = re.search(r'ESSID:"([^"]*)"', line)
                            if match and current_network:
                                current_network["ssid"] = match.group(1) or "Hidden"
                        elif "Signal level=" in line:
                            match = re.search(r'Signal level=(-?\d+)', line)
                            if match and current_network:
                                current_network["signal"] = int(match.group(1))
                    
                    if current_network and "ssid" in current_network:
                        networks.append(current_network)
                        
            except Exception as e:
                logger.error(f"WiFi scan failed: {e}")
        
        return networks[:10]  # Limit to 10 networks
    
    def _scan_wifi_macos(self) -> List[Dict[str, Any]]:
        """Scan WiFi on macOS using airport utility."""
        networks = []
        
        try:
            # Use airport utility
            result = subprocess.run(
                ["/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport", "-s"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n')[1:]:  # Skip header
                    parts = line.split()
                    if len(parts) >= 3:
                        networks.append({
                            "ssid": parts[0],
                            "bssid": parts[1],
                            "signal": int(parts[2])
                        })
        except Exception as e:
            logger.error(f"WiFi scan failed on macOS: {e}")
        
        return networks[:10]
    
    def _scan_wifi_windows(self) -> List[Dict[str, Any]]:
        """Scan WiFi on Windows using netsh."""
        networks = []
        
        try:
            result = subprocess.run(
                ["netsh", "wlan", "show", "networks", "mode=bssid"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                current_ssid = None
                for line in result.stdout.split('\n'):
                    if "SSID" in line and ":" in line:
                        ssid = line.split(":", 1)[1].strip()
                        current_ssid = ssid if ssid else "Hidden"
                    elif "BSSID" in line and ":" in line and current_ssid:
                        bssid = line.split(":", 1)[1].strip()
                        signal_line = next((l for l in result.stdout.split('\n') if "Signal" in l), None)
                        signal = -100
                        if signal_line:
                            match = re.search(r'(\d+)%', signal_line)
                            if match:
                                # Convert percentage to dBm approximation
                                signal = -100 + int(match.group(1))
                        
                        networks.append({
                            "ssid": current_ssid,
                            "bssid": bssid,
                            "signal": signal
                        })
        except Exception as e:
            logger.error(f"WiFi scan failed on Windows: {e}")
        
        return networks[:10]
    
    def _get_battery_level(self) -> Optional[int]:
        """Get battery level if available."""
        system = platform.system().lower()
        
        try:
            if system == "linux":
                # Check /sys/class/power_supply/BAT*/capacity
                bat_paths = list(Path("/sys/class/power_supply").glob("BAT*/capacity"))
                if bat_paths:
                    return int(bat_paths[0].read_text().strip())
            
            elif system == "darwin":
                result = subprocess.run(
                    ["pmset", "-g", "batt"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    match = re.search(r'(\d+)%', result.stdout)
                    if match:
                        return int(match.group(1))
            
            elif system == "windows":
                result = subprocess.run(
                    ["WMIC", "Path", "Win32_Battery", "Get", "EstimatedChargeRemaining"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if line.strip().isdigit():
                            return int(line.strip())
        
        except Exception as e:
            logger.debug(f"Battery level not available: {e}")
        
        return None
