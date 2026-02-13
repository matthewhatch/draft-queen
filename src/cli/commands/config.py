"""Configuration management commands (US-030)."""

import click
import yaml
import json
from pathlib import Path
from typing import Optional, Dict, Any
from rich.console import Console
from rich.status import Status
from rich.table import Table
from rich.prompt import Prompt, Confirm

console = Console()

CONFIG_DIR = Path.home() / ".dq"
CONFIG_FILE = CONFIG_DIR / "config.yaml"


def load_config() -> Dict[str, Any]:
    """Load configuration from file."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}
    return {}


def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


@click.group()
def config():
    """Manage CLI configuration."""
    pass


@config.command()
def init():
    """Interactive configuration setup wizard.
    
    This will guide you through setting up draft-queen CLI configuration
    including API endpoint, authentication, and preferences.
    
    Example:
        $ dq config init
    """
    console.print("[bold cyan]Draft Queen CLI - Configuration Setup[/bold cyan]")
    console.print()
    
    # Load existing config if available
    existing_config = load_config()
    
    # API URL
    default_url = existing_config.get("api_url", "http://localhost:8000")
    api_url = Prompt.ask(
        "[yellow]API Endpoint URL[/yellow]",
        default=default_url
    )
    
    # Profile name
    profile = Prompt.ask(
        "[yellow]Profile name[/yellow]",
        default=existing_config.get("profile", "default")
    )
    
    # Output format preference
    output_format = click.prompt(
        "[yellow]Preferred output format[/yellow]",
        type=click.Choice(["table", "json"]),
        default=existing_config.get("output_format", "table")
    )
    
    # Verbosity
    verbose = Confirm.ask(
        "[yellow]Enable verbose logging by default?[/yellow]",
        default=existing_config.get("verbose", False)
    )
    
    # Build new config
    new_config = {
        "api_url": api_url,
        "profile": profile,
        "output_format": output_format,
        "verbose": verbose,
    }
    
    # Save config
    try:
        save_config(new_config)
        console.print()
        console.print("[green]✓ Configuration saved[/green]")
        console.print(f"  Location: {CONFIG_FILE}")
        console.print()
        console.print("[bold]Configuration Details:[/bold]")
        for key, value in new_config.items():
            console.print(f"  {key}: {value}")
    except Exception as e:
        console.print(f"[red]Error saving configuration: {e}[/red]")
        raise


@config.command()
@click.pass_context
def validate(ctx):
    """Validate configuration file.
    
    Checks if the configuration file exists and is valid YAML.
    
    Example:
        $ dq config validate
    """
    try:
        config = load_config()
        
        # Check API endpoint connectivity
        api_url = config.get("api_url", "http://localhost:8000")
        
        with Status(f"[bold cyan]Validating configuration...", console=console) as status:
            # Test API connectivity
            try:
                from cli.client import APIClient
                client = APIClient(base_url=api_url)
                health = client.health_check()
                api_ok = True
            except Exception as e:
                api_ok = False
                api_error = str(e)
        
        console.print()
        
        # Display validation results
        table = Table(title="Configuration Validation", show_header=True, header_style="bold magenta")
        table.add_column("Check", style="cyan")
        table.add_column("Status", style="green")
        
        table.add_row(
            "Configuration file exists",
            "[green]✓[/green]" if CONFIG_FILE.exists() else "[red]✗[/red]"
        )
        
        table.add_row(
            "Configuration is valid YAML",
            "[green]✓[/green]" if config else "[red]✗[/red]"
        )
        
        table.add_row(
            f"API endpoint reachable ({api_url})",
            "[green]✓[/green]" if api_ok else f"[red]✗[/red] {api_error if not api_ok else ''}"
        )
        
        console.print(table)
        
        if api_ok:
            console.print("[green]✓ All checks passed![/green]")
        else:
            console.print("[yellow]⚠ Some checks failed[/yellow]")
    
    except Exception as e:
        console.print(f"[red]Error validating configuration: {e}[/red]")
        ctx.exit(1)


@config.command()
def show():
    """Display current configuration.
    
    Example:
        $ dq config show
    """
    config = load_config()
    
    if not config:
        console.print("[yellow]No configuration found[/yellow]")
        console.print(f"[dim]Run 'dq config init' to create configuration[/dim]")
        return
    
    console.print("[bold]Configuration Settings[/bold]")
    console.print()
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    for key, value in config.items():
        table.add_row(key, str(value))
    
    console.print(table)
    console.print()
    console.print(f"[dim]Config file: {CONFIG_FILE}[/dim]")


@config.command()
@click.argument("key")
@click.argument("value")
def set(key, value):
    """Update a configuration setting.
    
    Examples:
        $ dq config set api_url http://production-api:8000
        $ dq config set verbose true
        $ dq config set output_format json
    """
    config = load_config()
    
    # Parse value as appropriate type
    if value.lower() in ("true", "false"):
        parsed_value = value.lower() == "true"
    elif value.isdigit():
        parsed_value = int(value)
    else:
        parsed_value = value
    
    config[key] = parsed_value
    
    try:
        save_config(config)
        console.print(f"[green]✓ Updated {key}[/green]")
        console.print(f"  {key}: {parsed_value}")
    except Exception as e:
        console.print(f"[red]Error updating configuration: {e}[/red]")
        raise
