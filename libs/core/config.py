"""Shared configuration management for all Tracker components."""

import os
import json
import tomllib
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

@dataclass
class TrackerConfig:
    """Base configuration for Tracker system."""
    
    # Server settings
    server_url: str = "http://localhost:8000"
    
    # Agent settings
    heartbeat_seconds: int = 300  # 5 minutes default
    poll_interval: int = 30  # 30 seconds
    device_id: Optional[str] = None
    device_token: Optional[str] = None
    
    # Storage settings
    db_url: str = "sqlite:///~/.local/share/tracker/tracker.db"
    
    # Security
    tls_verify: bool = True
    
    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = None
    
    # Paths
    config_dir: Path = field(default_factory=lambda: Path.home() / ".config" / "tracker")
    data_dir: Path = field(default_factory=lambda: Path.home() / ".local" / "share" / "tracker")
    keys_dir: Path = field(default_factory=lambda: Path.home() / ".local" / "share" / "tracker" / "keys")
    
    def __post_init__(self):
        """Ensure directories exist with proper permissions."""
        self.config_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.keys_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

def load_config(config_path: Optional[Path] = None, component: str = "agent") -> TrackerConfig:
    """
    Load configuration from file and environment variables.
    Priority: ENV > file > defaults
    """
    config = TrackerConfig()
    
    # Default paths based on component
    if config_path is None:
        config_path = config.config_dir / f"{component}.toml"
    
    # Load from file if exists
    if config_path.exists():
        with open(config_path, "rb") as f:
            file_config = tomllib.load(f)
            for key, value in file_config.items():
                if hasattr(config, key):
                    setattr(config, key, value)
    
    # Override with environment variables
    env_prefix = "TRACKER_"
    for key in dir(config):
        if not key.startswith("_"):
            env_key = f"{env_prefix}{key.upper()}"
            if env_value := os.environ.get(env_key):
                # Convert types as needed
                attr_type = type(getattr(config, key))
                if attr_type == bool:
                    setattr(config, key, env_value.lower() in ("true", "1", "yes"))
                elif attr_type == int:
                    setattr(config, key, int(env_value))
                elif attr_type == Path:
                    setattr(config, key, Path(env_value))
                else:
                    setattr(config, key, env_value)
    
    return config

def save_config(config: TrackerConfig, config_path: Optional[Path] = None, component: str = "agent"):
    """Save configuration to TOML file with restricted permissions."""
    if config_path is None:
        config_path = config.config_dir / f"{component}.toml"
    
    config_dict = {
        k: str(v) if isinstance(v, Path) else v
        for k, v in config.__dict__.items()
        if not k.startswith("_") and v is not None
    }
    
    # Write with restricted permissions
    import toml
    config_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with open(config_path, "w") as f:
        os.chmod(config_path, 0o600)
        toml.dump(config_dict, f)
