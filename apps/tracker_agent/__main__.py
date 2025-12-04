"""Tracker agent entry point."""

import sys
import argparse
from pathlib import Path

from libs.core.config import load_config
from libs.core.logging import setup_logging
from .enroll import DeviceEnroller
from .runner import AgentRunner
from .service import ServiceManager

logger = setup_logging("tracker-agent")

def main():
    """Main entry point for tracker agent."""
    parser = argparse.ArgumentParser(description="Tracker Device Agent")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Enroll command
    enroll_parser = subparsers.add_parser("enroll", help="Enroll device")
    enroll_parser.add_argument("--server", required=True, help="Server URL")
    enroll_parser.add_argument("--token", required=True, help="Enrollment token")
    enroll_parser.add_argument("--display-name", required=True, help="Device display name")
    enroll_parser.add_argument("--accept-terms", action="store_true", help="Accept terms")
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Run agent")
    run_parser.add_argument("--foreground", action="store_true", help="Run in foreground")
    
    # Service commands
    service_parser = subparsers.add_parser("service", help="Service management")
    service_parser.add_argument("action", choices=["install", "uninstall", "status"])
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        config = load_config(component="agent")
        
        if args.command == "enroll":
            enroller = DeviceEnroller(config)
            result = enroller.enroll(
                args.server,
                args.token,
                args.display_name,
                args.accept_terms
            )
            print(f"\n✓ Device enrolled successfully!")
            print(f"  Device ID: {result['device_id']}")
            print(f"  Name: {result['display_name']}")
            print(f"  Platform: {result['platform']}")
            print(f"\nRun 'tracker-agent run' to start the agent")
            
        elif args.command == "run":
            runner = AgentRunner(config)
            print("Starting Tracker agent...")
            print(f"Device ID: {config.device_id}")
            print(f"Server: {config.server_url}")
            print(f"Heartbeat: {config.heartbeat_seconds}s")
            print("\nPress Ctrl+C to stop")
            runner.run()
            
        elif args.command == "service":
            manager = ServiceManager(config)
            if args.action == "install":
                manager.install()
                print("✓ Service installed successfully")
            elif args.action == "uninstall":
                manager.uninstall()
                print("✓ Service uninstalled")
            elif args.action == "status":
                status = manager.status()
                print(f"Service status: {status}")
        
    except Exception as e:
        logger.error(f"Agent error: {e}")
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
