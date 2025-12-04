"""Device enrollment logic."""

import os
import json
import requests
from pathlib import Path
from typing import Optional, Dict, Any
import platform
from datetime import datetime

from libs.core.config import TrackerConfig, save_config
from libs.core.crypto import generate_keypair, save_keypair
from libs.core.logging import setup_logging
from libs.core.models import EnrollmentRequest, EnrollmentResponse, Platform
from libs.core.errors import EnrollmentError

logger = setup_logging("tracker-agent.enroll")

class DeviceEnroller:
    """Handles device enrollment process."""
    
    def __init__(self, config: TrackerConfig):
        """Initialize enroller with config."""
        self.config = config
    
    def enroll(
        self,
        server_url: str,
        token: str,
        display_name: str,
        accept_terms: bool = False
    ) -> Dict[str, Any]:
        """
        Enroll device with server.
        
        Args:
            server_url: Server URL
            token: Enrollment token
            display_name: Display name for device
            accept_terms: Whether user has accepted terms
        
        Returns:
            Enrollment result with device_id and token
        
        Raises:
            EnrollmentError: If enrollment fails
        """
        if not accept_terms:
            raise EnrollmentError("Must accept terms and conditions to enroll")
        
        # Show consent prompt
        if not self._show_consent():
            raise EnrollmentError("Enrollment cancelled - consent required")
        
        logger.info(f"Starting enrollment with server {server_url}")
        
        try:
            # Generate device keypair
            private_key, public_key = generate_keypair()
            
            # Detect platform
            system = platform.system().lower()
            if system == "linux":
                # Check if running in Termux
                if os.environ.get("TERMUX_VERSION"):
                    device_platform = Platform.TERMUX
                else:
                    device_platform = Platform.LINUX
            elif system == "darwin":
                device_platform = Platform.MACOS
            elif system == "windows":
                device_platform = Platform.WINDOWS
            else:
                device_platform = Platform.LINUX  # Default fallback
            
            # Prepare enrollment request
            enrollment_data = {
                "token": token,
                "pubkey": public_key,
                "platform": device_platform.value,
                "display_name": display_name
            }
            
            # Send enrollment request
            url = f"{server_url}/api/v1/enroll/claim"
            response = requests.post(
                url,
                json=enrollment_data,
                timeout=10,
                verify=self.config.tls_verify
            )
            
            if response.status_code != 200:
                error_msg = f"Enrollment failed: {response.status_code}"
                if response.text:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("error", {}).get("message", error_msg)
                    except Exception:
                        pass
                raise EnrollmentError(error_msg)
            
            # Parse response
            result = response.json()
            device_id = result["device_id"]
            device_token = result["device_token"]
            
            # Save credentials
            save_keypair(private_key, public_key, self.config.keys_dir, "device")
            
            # Update config
            self.config.server_url = server_url
            self.config.device_id = device_id
            self.config.device_token = device_token
            save_config(self.config, component="agent")
            
            # Log enrollment
            self._log_enrollment(device_id, display_name)
            
            logger.info(f"Successfully enrolled device {device_id}")
            
            return {
                "device_id": device_id,
                "display_name": display_name,
                "platform": device_platform.value,
                "enrolled": True
            }
            
        except requests.RequestException as e:
            raise EnrollmentError(f"Network error during enrollment: {e}")
        except Exception as e:
            raise EnrollmentError(f"Enrollment failed: {e}")
    
    def _show_consent(self) -> bool:
        """
        Show consent prompt to user.
        
        Returns:
            True if user consents, False otherwise
        """
        print("\n" + "="*60)
        print("TRACKER DEVICE ENROLLMENT - CONSENT REQUIRED")
        print("="*60)
        print("""
This system will collect and transmit the following data:
- Device hostname and operating system information
- WiFi network information (SSIDs and BSSIDs)
- IP address and approximate geographic location
- Battery level (if available)
- Device status and health metrics

This data will be sent to the tracking server periodically.

IMPORTANT:
- This system can ONLY track enrolled devices
- You must be the rightful owner of this device
- You must comply with all local laws and regulations
- This is NOT for tracking phones by phone number
- This is NOT for unauthorized surveillance

By enrolling, you confirm that:
1. You are the owner of this device or have explicit permission
2. You understand what data will be collected
3. You accept the terms and conditions
4. You will use this system responsibly and legally
        """)
        print("="*60)
        
        response = input("\nDo you accept these terms and wish to enroll? (yes/no): ")
        return response.lower() in ["yes", "y"]
    
    def _log_enrollment(self, device_id: str, display_name: str):
        """Log enrollment for audit purposes."""
        log_file = self.config.data_dir / "enrollment.log"
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "device_id": device_id,
            "display_name": display_name,
            "consent": True
        }
        
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
