"""Device management commands."""

import typer
from typing import Optional
from datetime import datetime
from rich.console import Console
from rich.table import Table

from ..config import CliConfig
from ..clients.api_client import ApiClient

app = typer.Typer()
console = Console()

@app.command("list")
def list_devices(
    format: str = typer.Option("table", "--format", "-f", help="Output format (table/json)"),
    limit: int = typer.Option(10, "--limit", "-l", help="Number of devices to show"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """List all enrolled devices."""
    try:
        client = ApiClient()
        result = client.list_devices(limit=limit)
        
        if json_output or format == "json":
            import json
            typer.echo(json.dumps(result, indent=2))
            return
        
        devices = result.get("devices", [])
        
        if not devices:
            typer.echo("No devices found")
            return
        
        # Create table
        table = Table(title="Enrolled Devices")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Name", style="magenta")
        table.add_column("Platform", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Last Seen", style="blue")
        
        for device in devices:
            device_id = device["id"][:8] + "..."  # Truncate ID
            status = "🔴 Lost" if device.get("lost") else "🟢 OK"
            last_seen = device.get("last_seen_at", "Never")
            if last_seen != "Never":
                try:
                    dt = datetime.fromisoformat(last_seen.rstrip("Z"))
                    last_seen = dt.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    pass
            
            table.add_row(
                device_id,
                device["display_name"],
                device["platform"],
                status,
                last_seen
            )
        
        console.print(table)
        
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

@app.command("show")
def show_device(
    device_id: str = typer.Argument(..., help="Device ID"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """Show device details."""
    try:
        client = ApiClient()
        device = client.get_device(device_id)
        
        if json_output:
            import json
            typer.echo(json.dumps(device, indent=2))
            return
        
        # Display device info
        typer.echo(f"\n📱 Device Information")
        typer.echo(f"  ID: {device['id']}")
        typer.echo(f"  Name: {device['display_name']}")
        typer.echo(f"  Platform: {device['platform']}")
        typer.echo(f"  Status: {'🔴 Lost' if device.get('lost') else '🟢 OK'}")
        typer.echo(f"  Enrolled: {device.get('enrolled_at', 'Unknown')}")
        
        if device.get("last_seen_at"):
            typer.echo(f"\n📍 Last Known Status")
            typer.echo(f"  Last seen: {device['last_seen_at']}")
            if device.get("last_ip"):
                typer.echo(f"  IP: {device['last_ip']}")
            if device.get("last_location"):
                loc = device["last_location"]
                typer.echo(f"  Location: {loc.get('city', 'Unknown')}, {loc.get('country', 'Unknown')}")
        
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

@app.command("generate-enroll-token")
def generate_enrollment_token(
    expires: str = typer.Option("10m", "--expires", "-e", help="Token expiration (e.g., 10m, 1h)")
):
    """Generate device enrollment token."""
    try:
        # Parse expiration
        if expires.endswith("m"):
            minutes = int(expires[:-1])
        elif expires.endswith("h"):
            minutes = int(expires[:-1]) * 60
        else:
            minutes = int(expires)
        
        client = ApiClient()
        result = client.create_enrollment_token(minutes)
        
        token = result.get("token")
        expires_at = result.get("expires_at")
        
        typer.echo(f"\n🔑 Enrollment Token Generated")
        typer.echo(f"\nToken: {typer.style(token, fg=typer.colors.GREEN, bold=True)}")
        typer.echo(f"Expires: {expires_at}")
        typer.echo(f"\nTo enroll a device, run on the target device:")
        
        server = CliConfig().get_server()
        typer.echo(f"\n  tracker-agent enroll --server {server} --token {token} --display-name '<name>'")
        
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

@app.command("lost")
def mark_device_lost(
    device_id: str = typer.Argument(..., help="Device ID"),
    message: Optional[str] = typer.Option(None, "--message", "-m", help="Message to display on device")
):
    """Mark device as lost."""
    try:
        client = ApiClient()
        
        # Confirm action
        if not typer.confirm(f"Mark device {device_id} as LOST?"):
            typer.echo("Cancelled")
            return
        
        result = client.mark_device_lost(device_id, message)
        
        typer.echo(f"✓ Device marked as lost")
        typer.echo(f"  Commands queued: {result.get('commands_queued', 0)}")
        typer.echo("\nThe device will:")
        typer.echo("  • Display the lost message")
        typer.echo("  • Play an audible chime")
        typer.echo("  • Increase telemetry frequency")
        
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

@app.command("found")
def mark_device_found(
    device_id: str = typer.Argument(..., help="Device ID")
):
    """Mark device as found."""
    try:
        client = ApiClient()
        result = client.mark_device_found(device_id)
        
        typer.echo(f"✓ Device marked as found")
        typer.echo("  Heartbeat interval reset to normal (5 minutes)")
        
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

