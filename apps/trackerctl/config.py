"""CLI configuration management."""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any

from libs.core.logging import setup_logging

logger = setup_logging("trackerctl.config")

class CliConfig:
    """Manage CLI configuration."""
    
    def __init__(self):
        """Initialize CLI config."""
        self.config_dir = Path.home() / ".config" / "tracker"
        self.config_file = self.config_dir / "cli.json"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self._load()
    
    def _load(self):
        """Load configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    self.data = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
                self.data = {}
        else:
            self.data = {}
    
    def _save(self):
        """Save configuration to file."""
        try:
            with open(self.config_file, "w") as f:
                os.chmod(self.config_file, 0o600)
                json.dump(self.data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.data.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set configuration value."""
        self.data[key] = value
        self._save()
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration."""
        return self.data.copy()
    
    def reset(self):
        """Reset configuration."""
        self.data = {}
        self._save()
    
    def get_server(self) -> Optional[str]:
        """Get server URL."""
        return self.get("server_url")
    
    def set_server(self, url: str):
        """Set server URL."""
        self.set("server_url", url)
    
    def get_token(self) -> Optional[str]:
        """Get auth token."""
        return self.get("auth_token")
    
    def set_token(self, token: str):
        """Set auth token."""
        self.set("auth_token", token)
    
    def clear_auth(self):
        """Clear authentication."""
        self.data.pop("auth_token", None)
        self.data.pop("user_email", None)
        self._save()
