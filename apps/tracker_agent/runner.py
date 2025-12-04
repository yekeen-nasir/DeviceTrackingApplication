"""Agent heartbeat loop and command execution."""

import time
import json
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path
from queue import Queue, Empty
import threading

from libs.core.config import load_config, TrackerConfig
from libs.core.logging import setup_logging
from libs.core.errors import NetworkError
from libs.core.storage import SQLAlchemyStorage
from .monitor import TelemetryCollector
from .commands import CommandExecutor
from .storage import LocalQueue

logger = setup_logging("tracker-agent.runner")

class AgentRunner:
    """Main agent runner with heartbeat loop."""
    
    def __init__(self, config: Optional[TrackerConfig] = None):
        """Initialize agent runner."""
        self.config = config or load_config(component="agent")
        self.collector = TelemetryCollector()
        self.executor = CommandExecutor()
        self.local_queue = LocalQueue(self.config.data_dir / "queue.db")
        self.running = False
        self.heartbeat_interval = self.config.heartbeat_seconds
        self.poll_interval = self.config.poll_interval
        
        # Load device credentials
        self._load_credentials()
    
    def _load_credentials(self):
        """Load device credentials from config."""
        if not self.config.device_id or not self.config.device_token:
            raise ValueError("Device not enrolled. Run 'tracker-agent enroll' first.")
        
        logger.info(f"Loaded device credentials for {self.config.device_id}")
    
    def run(self):
        """Run the main agent loop."""
        logger.info("Starting tracker agent")
        self.running = True
        
        # Start command polling thread
        poll_thread = threading.Thread(target=self._command_poll_loop)
        poll_thread.daemon = True
        poll_thread.start()
        
        # Main heartbeat loop
        try:
            while self.running:
                self._heartbeat()
                time.sleep(self.heartbeat_interval)
        except KeyboardInterrupt:
            logger.info("Agent stopped by user")
        except Exception as e:
            logger.error(f"Agent error: {e}")
        finally:
            self.running = False
    
    def _heartbeat(self):
        """Send telemetry heartbeat to server."""
        try:
            # Collect telemetry
            telemetry = self.collector.collect_telemetry()
            
            # Try to send to server
            if self._send_telemetry(telemetry):
                logger.info(f"Telemetry sent successfully (seq={telemetry['seq']})")
                
                # Process any queued telemetry
                self._flush_queue()
            else:
                # Queue for later if sending fails
                self.local_queue.enqueue(telemetry)
                logger.warning("Telemetry queued for later delivery")
                
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")
    
    def _send_telemetry(self, telemetry: Dict[str, Any]) -> bool:
        """
        Send telemetry to server.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"{self.config.server_url}/api/v1/telemetry"
            headers = {
                "Authorization": f"Bearer {self.config.device_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                url,
                json=telemetry,
                headers=headers,
                verify=self.config.tls_verify,
                timeout=10
            )
            
            return response.status_code == 202
            
        except requests.RequestException as e:
            logger.error(f"Failed to send telemetry: {e}")
            return False
    
    def _flush_queue(self):
        """Attempt to send queued telemetry."""
        while True:
            item = self.local_queue.dequeue()
            if not item:
                break
            
            if not self._send_telemetry(item):
                # Re-queue if still failing
                self.local_queue.enqueue(item)
                break
            
            logger.info(f"Sent queued telemetry (seq={item['seq']})")
    
    def _command_poll_loop(self):
        """Poll for commands from server."""
        while self.running:
            try:
                commands = self._fetch_commands()
                for command in commands:
                    self._execute_command(command)
            except Exception as e:
                logger.error(f"Command poll error: {e}")
            
            time.sleep(self.poll_interval)
    
    def _fetch_commands(self) -> list:
        """Fetch pending commands from server."""
        try:
            url = f"{self.config.server_url}/api/v1/devices/{self.config.device_id}/commands"
            headers = {
                "Authorization": f"Bearer {self.config.device_token}"
            }
            
            response = requests.get(
                url,
                headers=headers,
                verify=self.config.tls_verify,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("commands", [])
            
        except Exception as e:
            logger.error(f"Failed to fetch commands: {e}")
        
        return []
    
    def _execute_command(self, command: Dict[str, Any]):
        """Execute a command and send acknowledgment."""
        command_id = command["id"]
        command_type = command["type"]
        
        logger.info(f"Executing command {command_id} (type={command_type})")
        
        # Execute command
        success, details = self.executor.execute(command)
        
        # Send acknowledgment
        self._ack_command(command_id, "DONE" if success else "FAILED", details)
    
    def _ack_command(self, command_id: str, status: str, details: Optional[str] = None):
        """Send command acknowledgment to server."""
        try:
            url = f"{self.config.server_url}/api/v1/commands/{command_id}/ack"
            headers = {
                "Authorization": f"Bearer {self.config.device_token}",
                "Content-Type": "application/json"
            }
            
            payload = {"status": status}
            if details:
                payload["details"] = details
            
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                verify=self.config.tls_verify,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Command {command_id} acknowledged as {status}")
            
        except Exception as e:
            logger.error(f"Failed to ack command {command_id}: {e}")
    
    def increase_heartbeat(self, seconds: int):
        """Temporarily increase heartbeat frequency."""
        self.heartbeat_interval = seconds
        logger.info(f"Heartbeat interval changed to {seconds} seconds")
