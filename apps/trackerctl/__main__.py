"""TrackerCTL CLI entry point."""

import sys
import typer
from typing import Optional
from pathlib import Path

from libs.core.config import load_config
from libs.core.logging import setup_logging
from .commands import auth, device, report, alerts
from .config import CliConfig

logger = setup_logging("trackerctl")

app = typer.Typer(
    help="Tracker System CLI - Manage devices and tracking",
    no_args_is_help=True
)

# Add command groups
app.add_typer(auth.app, name="auth", help="Authentication commands")
app.add_typer(device.app, name="device", help="Device management")
app.add_typer(report.app, name="report", help="Report generation")
app.add_typer(alerts.app, name="alerts", help="Alert monitoring")

@app.command()
def version():
    """Show version information."""
    typer.echo("TrackerCTL v1.0.0")
    typer.echo("Python Device Tracking System")

@app.command()
def config(
    show: bool = typer.Option(False, "--show", help="Show current configuration"),
    server: Optional[str] = typer.Option(None, "--server", help="Set server URL"),
    reset: bool = typer.Option(False, "--reset", help="Reset configuration")
):
    """Manage CLI configuration."""
    cli_config = CliConfig()
    
    if reset:
        cli_config.reset()
        typer.echo("✓ Configuration reset")
        return
    
    if server:
        cli_config.set_server(server)
        typer.echo(f"✓ Server set to: {server}")
    
    if show or (not server and not reset):
        config_data = cli_config.get_all()
        typer.echo("Current configuration:")
        for key, value in config_data.items():
            if key == "token" and value:
                value = "***" + value[-8:]  # Mask token
            typer.echo(f"  {key}: {value}")

def main():
    """Main entry point."""
    try:
        app()
    except Exception as e:
        logger.error(f"CLI error: {e}")
        typer.echo(f"Error: {e}", err=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
