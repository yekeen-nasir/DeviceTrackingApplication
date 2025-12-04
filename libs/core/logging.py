"""Centralized logging setup for Tracker system."""

import logging
import sys
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

class StructuredFormatter(logging.Formatter):
    """JSON structured log formatter."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "component": record.name,
            "msg": record.getMessage(),
        }
        
        # Add extra fields
        if hasattr(record, "device_id"):
            log_obj["device_id"] = record.device_id
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id
            
        if record.exc_info:
            log_obj["exc_info"] = self.formatException(record.exc_info)
            
        return json.dumps(log_obj)

def setup_logging(
    component: str,
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
    structured: bool = True
) -> logging.Logger:
    """
    Setup logging for a component with both file and console handlers.
    
    Args:
        component: Name of the component (agent, server, cli)
        log_level: Logging level
        log_file: Optional log file path
        structured: Use structured JSON logging
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(component)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    logger.handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    if structured:
        console_handler.setFormatter(StructuredFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
    logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5  # 10MB per file, 5 backups
        )
        if structured:
            file_handler.setFormatter(StructuredFormatter())
        else:
            file_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            )
        logger.addHandler(file_handler)
    
    return logger

def redact_sensitive(data: Dict[str, Any]) -> Dict[str, Any]:
    """Redact sensitive fields from log data."""
    sensitive_keys = {"token", "password", "device_token", "private_key", "secret"}
    redacted = {}
    
    for key, value in data.items():
        if any(s in key.lower() for s in sensitive_keys):
            redacted[key] = "***REDACTED***"
        elif isinstance(value, dict):
            redacted[key] = redact_sensitive(value)
        else:
            redacted[key] = value
            
    return redacted