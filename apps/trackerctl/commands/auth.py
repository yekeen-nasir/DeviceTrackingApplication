"""Authentication commands."""

import typer
from typing import Optional
import getpass

from ..config import CliConfig
from ..clients.api_client import ApiClient

app = typer.Typer()

@app.command()
def login(
    server: Optional[str] = typer.Option(None, "--server", "-s", help="Server URL"),
    email: Optional[str] = typer.Option(None, "--email", "-e", help="Email address")
):
    """Login to Tracker server."""
    config = CliConfig()
    
    # Set server if provided
    if server:
        config.set_server(server)
    
    # Check if server is configured
    if not config.get_server():
        typer.echo("Error: No server configured. Use --server option or 'trackerctl config --server <url>'", err=True)
        raise typer.Exit(1)
    
    # Prompt for email if not provided
    if not email:
        email = typer.prompt("Email")
    
    # Prompt for password
    password = getpass.getpass("Password: ")
    
    try:
        client = ApiClient(config)
        token = client.login(email, password)
        
        typer.echo(f"✓ Logged in successfully as {email}")
        typer.echo(f"  Server: {config.get_server()}")
        
    except Exception as e:
        typer.echo(f"✗ Login failed: {e}", err=True)
        raise typer.Exit(1)

@app.command()
def logout():
    """Logout from Tracker server."""
    config = CliConfig()
    config.clear_auth()
    typer.echo("✓ Logged out successfully")

@app.command()
def register(
    email: str = typer.Argument(..., help="Email address"),
    role: str = typer.Option("user", "--role", "-r", help="User role (user/admin)")
):
    """Register a new user account."""
    config = CliConfig()
    
    if not config.get_server():
        typer.echo("Error: No server configured", err=True)
        raise typer.Exit(1)
    
    # Prompt for password
    password = getpass.getpass("Password: ")
    confirm = getpass.getpass("Confirm password: ")
    
    if password != confirm:
        typer.echo("Error: Passwords do not match", err=True)
        raise typer.Exit(1)
    
    try:
        client = ApiClient(config)
        token = client.register(email, password, role)
        
        typer.echo(f"✓ Account created successfully")
        typer.echo(f"  Email: {email}")
        typer.echo(f"  Role: {role}")
        typer.echo("\nUse 'trackerctl auth login' to sign in")
        
    except Exception as e:
        typer.echo(f"✗ Registration failed: {e}", err=True)
        raise typer.Exit(1)

@app.command()
def status():
    """Show authentication status."""
    config = CliConfig()
    
    server = config.get_server()
    token = config.get_token()
    email = config.get("user_email")
    
    if not server:
        typer.echo("✗ No server configured")
    else:
        typer.echo(f"Server: {server}")
    
    if token:
        typer.echo(f"✓ Logged in as: {email}")
    else:
        typer.echo("✗ Not logged in")
