"""Report generation commands."""

import typer
import json
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

from ..config import CliConfig
from ..clients.api_client import ApiClient

app = typer.Typer()

@app.command("export")
def export_report(
    device_id: str = typer.Argument(..., help="Device ID"),
    from_date: Optional[str] = typer.Option(None, "--from", "-f", help="Start date (YYYY-MM-DD)"),
    to_date: Optional[str] = typer.Option(None, "--to", "-t", help="End date (YYYY-MM-DD)"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path"),
    format: str = typer.Option("json", "--format", help="Output format (json/pdf)")
):
    """Export device tracking report."""
    try:
        client = ApiClient()
        
        # Parse dates
        from_dt = None
        to_dt = None
        
        if from_date:
            from_dt = datetime.strptime(from_date, "%Y-%m-%d")
        else:
            from_dt = datetime.now() - timedelta(days=30)
        
        if to_date:
            to_dt = datetime.strptime(to_date, "%Y-%m-%d")
        else:
            to_dt = datetime.now()
        
        typer.echo(f"Generating report for device {device_id[:8]}...")
        typer.echo(f"  Date range: {from_dt.date()} to {to_dt.date()}")
        
        # Get report
        report = client.get_report(device_id, from_dt, to_dt)
        
        # Format output
        if format == "json":
            output_data = json.dumps(report, indent=2)
        else:
            # For PDF, we'd need additional formatting
            typer.echo("PDF format not yet implemented, using JSON", err=True)
            output_data = json.dumps(report, indent=2)
        
        # Write to file or stdout
        if output:
            output.write_text(output_data)
            typer.echo(f"✓ Report saved to {output}")
        else:
            typer.echo(output_data)
        
        # Show summary
        if output:
            timeline_count = len(report.get("timeline", []))
            wifi_count = len(report.get("wifi_summary", []))
            command_count = len(report.get("commands", []))
            
            typer.echo(f"\n📊 Report Summary:")
            typer.echo(f"  • {timeline_count} telemetry events")
            typer.echo(f"  • {wifi_count} unique WiFi networks")
            typer.echo(f"  • {command_count} commands issued")
        
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

@app.command("summary")
def show_summary(
    device_id: str = typer.Argument(..., help="Device ID"),
    days: int = typer.Option(7, "--days", "-d", help="Number of days to summarize")
):
    """Show device tracking summary."""
    try:
        client = ApiClient()
        
        from_dt = datetime.now() - timedelta(days=days)
        to_dt = datetime.now()
        
        report = client.get_report(device_id, from_dt, to_dt)
        
        # Parse report data
        device = report.get("device", {})
        timeline = report.get("timeline", [])
        wifi_summary = report.get("wifi_summary", [])
        commands = report.get("commands", [])
        
        typer.echo(f"\n📱 Device: {device.get('display_name', 'Unknown')}")
        typer.echo(f"   Platform: {device.get('platform', 'Unknown')}")
        typer.echo(f"   Status: {'🔴 Lost' if device.get('lost') else '🟢 OK'}")
        
        if timeline:
            typer.echo(f"\n📍 Activity Summary ({days} days):")
            typer.echo(f"   Total events: {len(timeline)}")
            
            # Get unique IPs
            ips = set(e.get("ip") for e in timeline if e.get("ip"))
            typer.echo(f"   Unique IPs: {len(ips)}")
            
            # Get unique locations
            locations = set()
            for event in timeline:
                if event.get("location"):
                    loc = event["location"]
                    locations.add(f"{loc.get('city', 'Unknown')}, {loc.get('country', 'Unknown')}")
            
            if locations:
                typer.echo(f"   Locations visited:")
                for loc in list(locations)[:5]:  # Show max 5
                    typer.echo(f"     • {loc}")
        
        if wifi_summary:
            typer.echo(f"\n📶 WiFi Networks:")
            typer.echo(f"   Total unique networks: {len(wifi_summary)}")
            
            # Show top networks by frequency
            sorted_wifi = sorted(wifi_summary, key=lambda x: x.get("seen_count", 0), reverse=True)
            for network in sorted_wifi[:5]:  # Show top 5
                ssids = ", ".join(network.get("ssids", ["Unknown"]))
                count = network.get("seen_count", 0)
                typer.echo(f"     • {ssids} (seen {count} times)")
        
        if commands:
            typer.echo(f"\n⚡ Recent Commands:")
            for cmd in commands[-5:]:  # Show last 5
                cmd_type = cmd.get("type", "Unknown")
                status = cmd.get("status", "Unknown")
                typer.echo(f"     • {cmd_type}: {status}")
        
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)      