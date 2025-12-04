"""Command execution logic for tracker agent."""

import os
import platform
import subprocess
import threading
from typing import Dict, Any, Tuple, Optional
from datetime import datetime

from libs.core.logging import setup_logging
from libs.core.models import CommandType

logger = setup_logging("tracker-agent.commands")

class CommandExecutor:
    """Executes commands received from server."""
    
    def __init__(self):
        """Initialize command executor."""
        self.system = platform.system().lower()
        self.command_handlers = {
            CommandType.SHOW_MESSAGE: self._show_message,
            CommandType.PLAY_CHIME: self._play_chime,
            CommandType.INCREASE_HEARTBEAT: self._increase_heartbeat,
            CommandType.LOCK_SCREEN: self._lock_screen,
            CommandType.PING: self._ping,
        }
    
    def execute(self, command: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Execute a command.
        
        Args:
            command: Command dictionary with type and payload
        
        Returns:
            Tuple of (success, details)
        """
        try:
            command_type = CommandType(command["type"])
            payload = command.get("payload", {})
            
            if command_type not in self.command_handlers:
                return False, f"Unsupported command type: {command_type}"
            
            # Check if command is expired
            if expires_at := command.get("expires_at"):
                if datetime.fromisoformat(expires_at.rstrip("Z")) < datetime.utcnow():
                    return False, "Command expired"
            
            # Execute handler
            handler = self.command_handlers[command_type]
            return handler(payload)
            
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return False, str(e)
    
    def _show_message(self, payload: Dict[str, Any]) -> Tuple[bool, str]:
        """Show a message to the user."""
        title = payload.get("title", "Tracker Alert")
        body = payload.get("body", "")
        
        if self.system == "linux":
            try:
                # Try notify-send first
                subprocess.run(
                    ["notify-send", title, body],
                    check=True,
                    timeout=5
                )
                return True, "Message displayed via notify-send"
            except (subprocess.SubprocessError, FileNotFoundError):
                # Fallback to zenity
                try:
                    subprocess.run(
                        ["zenity", "--info", f"--title={title}", f"--text={body}"],
                        check=True,
                        timeout=5
                    )
                    return True, "Message displayed via zenity"
                except Exception:
                    pass
        
        elif self.system == "darwin":  # macOS
            try:
                script = f'display dialog "{body}" with title "{title}" buttons {{"OK"}} default button "OK"'
                subprocess.run(
                    ["osascript", "-e", script],
                    check=True,
                    timeout=5
                )
                return True, "Message displayed via AppleScript"
            except Exception:
                pass
        
        elif self.system == "windows":
            try:
                import ctypes
                ctypes.windll.user32.MessageBoxW(0, body, title, 0x40)
                return True, "Message displayed via Windows MessageBox"
            except Exception:
                pass
        
        # Fallback: print to console/log
        logger.warning(f"ALERT - {title}: {body}")
        print(f"\n{'='*50}")
        print(f"TRACKER ALERT: {title}")
        print(f"{body}")
        print(f"{'='*50}\n")
        return True, "Message displayed in console"
    
    def _play_chime(self, payload: Dict[str, Any]) -> Tuple[bool, str]:
        """Play an audible chime/beep."""
        repeat = payload.get("repeat", 3)
        
        if self.system in ["linux", "darwin"]:
            try:
                for _ in range(repeat):
                    # Use system beep
                    print("\a", end="", flush=True)
                    subprocess.run(["tput", "bel"], capture_output=True)
                    threading.Event().wait(0.5)
                return True, f"Played {repeat} beeps"
            except Exception:
                pass
        
        elif self.system == "windows":
            try:
                import winsound
                for _ in range(repeat):
                    winsound.Beep(1000, 500)  # 1000Hz for 500ms
                    threading.Event().wait(0.2)
                return True, f"Played {repeat} beeps"
            except Exception:
                pass
        
        # Fallback
        logger.warning(f"CHIME requested ({repeat} times)")
        return True, "Chime logged (audio not available)"
    
    def _increase_heartbeat(self, payload: Dict[str, Any]) -> Tuple[bool, str]:
        """Signal to increase heartbeat frequency."""
        seconds = payload.get("seconds", 30)
        
        # This is handled by the runner when it processes this command
        # We just acknowledge it here
        return True, f"Heartbeat interval will be set to {seconds} seconds"
    
    def _lock_screen(self, payload: Dict[str, Any]) -> Tuple[bool, str]:
        """Lock the device screen."""
        try:
            if self.system == "linux":
                # Try multiple methods
                lock_commands = [
                    ["loginctl", "lock-session"],
                    ["gnome-screensaver-command", "--lock"],
                    ["xdg-screensaver", "lock"],
                    ["xscreensaver-command", "-lock"],
                ]
                
                for cmd in lock_commands:
                    try:
                        subprocess.run(cmd, check=True, timeout=2)
                        return True, f"Screen locked using {cmd[0]}"
                    except Exception:
                        continue
            
            elif self.system == "darwin":
                # macOS lock screen
                subprocess.run(
                    ["/System/Library/CoreServices/Menu Extras/User.menu/Contents/Resources/CGSession", "-suspend"],
                    check=True,
                    timeout=2
                )
                return True, "Screen locked on macOS"
            
            elif self.system == "windows":
                subprocess.run(
                    ["rundll32.exe", "user32.dll,LockWorkStation"],
                    check=True,
                    timeout=2
                )
                return True, "Screen locked on Windows"
        
        except Exception as e:
            logger.error(f"Failed to lock screen: {e}")
        
        return False, "Screen lock not available or failed"
    
    def _ping(self, payload: Dict[str, Any]) -> Tuple[bool, str]:
        """Respond to ping command."""
        logger.info("PING command received")
        return True, f"Pong at {datetime.utcnow().isoformat()}Z"
