"""API client for server communication."""

import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime

from libs.core.logging import setup_logging
from ..config import CliConfig

logger = setup_logging("trackerctl.api_client")

class ApiClient:
    """HTTP client for Tracker API."""
    
    def __init__(self, config: Optional[CliConfig] = None):
        """Initialize API client."""
        self.config = config or CliConfig()
        self.base_url = self.config.get_server()
        self.token = self.config.get_token()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Handle API response."""
        if response.status_code == 401:
            raise Exception("Authentication failed. Please login again.")
        elif response.status_code >= 400:
            try:
                error = response.json()
                message = error.get("error", {}).get("message", "Request failed")
            except Exception:
                message = f"Request failed with status {response.status_code}"
            raise Exception(message)
        
        try:
            return response.json()
        except Exception:
            return {"status": "success"}
    
    def login(self, email: str, password: str) -> str:
        """Login and get token."""
        if not self.base_url:
            raise Exception("Server URL not configured. Use 'trackerctl config --server <url>'")
        
        with httpx.Client() as client:
            response = client.post(
                f"{self.base_url}/api/v1/auth/login",
                json={"email": email, "password": password}
            )
            
            data = self._handle_response(response)
            token = data.get("access_token")
            
            if token:
                self.token = token
                self.config.set_token(token)
                self.config.set("user_email", email)
            
            return token
    
    def register(self, email: str, password: str, role: str = "user") -> str:
        """Register new user."""
        if not self.base_url:
            raise Exception("Server URL not configured")
        
        with httpx.Client() as client:
            response = client.post(
                f"{self.base_url}/api/v1/auth/register",
                json={"email": email, "password": password, "role": role}
            )
            
            data = self._handle_response(response)
            return data.get("access_token")
    
    def create_enrollment_token(self, expires_minutes: int = 10) -> Dict[str, Any]:
        """Create enrollment token."""
        with httpx.Client() as client:
            response = client.post(
                f"{self.base_url}/api/v1/enroll/tokens",
                json={"expires_minutes": expires_minutes},
                headers=self._get_headers()
            )
            
            return self._handle_response(response)
    
    def list_devices(self, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """List devices."""
        with httpx.Client() as client:
            response = client.get(
                f"{self.base_url}/api/v1/devices",
                params={"limit": limit, "offset": offset},
                headers=self._get_headers()
            )
            
            return self._handle_response(response)
    
    def get_device(self, device_id: str) -> Dict[str, Any]:
        """Get device details."""
        with httpx.Client() as client:
            response = client.get(
                f"{self.base_url}/api/v1/devices/{device_id}",
                headers=self._get_headers()
            )
            
            return self._handle_response(response)
    
    def mark_device_lost(self, device_id: str, message: Optional[str] = None) -> Dict[str, Any]:
        """Mark device as lost."""
        payload = {}
        if message:
            payload["message"] = message
        
        with httpx.Client() as client:
            response = client.post(
                f"{self.base_url}/api/v1/devices/{device_id}/lost",
                json=payload,
                headers=self._get_headers()
            )
            
            return self._handle_response(response)
    
    def mark_device_found(self, device_id: str) -> Dict[str, Any]:
        """Mark device as found."""
        with httpx.Client() as client:
            response = client.post(
                f"{self.base_url}/api/v1/devices/{device_id}/found",
                headers=self._get_headers()
            )
            
            return self._handle_response(response)
    
    def get_report(
        self,
        device_id: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get device report."""
        params = {}
        if from_date:
            params["from_date"] = from_date.isoformat()
        if to_date:
            params["to_date"] = to_date.isoformat()
        
        with httpx.Client() as client:
            response = client.get(
                f"{self.base_url}/api/v1/reports/{device_id}",
                params=params,
                headers=self._get_headers()
            )
            
            return self._handle_response(response)
