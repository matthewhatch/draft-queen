"""Draft Queen CLI - Main entry point."""

import click
import os
from pathlib import Path
from typing import Optional, Dict, Any
import yaml

from cli.client import APIClient
from cli.commands.pipeline import pipeline
from cli.commands.prospects import prospects
from cli.commands.history import history


class CliContext:
    """Shared CLI context."""
    
    def __init__(self, config_file: Optional[str] = None, api_url: Optional[str] = None):
        self.config = self._load_config(config_file)
        self.api_url = api_url or self.config.get("api_url", "http://localhost:8000")
        self.client = APIClient(base_url=self.api_url)
        self.verbose = False
    
    def _load_config(self, config_file: Optional[str]) -> Dict[str, Any]:
        """Load configuration from file."""
        if config_file and Path(config_file).exists():
            with open(config_file, "r") as f:
                return yaml.safe_load(f) or {}
        
        # Try default config locations
        default_paths = [
            Path.home() / ".dq" / "config.yaml",
            Path(".dq-config.yaml"),
            Path("~/.dq-config.yaml").expanduser(),
        ]
        
        for path in default_paths:
            if path.exists():
                try:
                    with open(path, "r") as f:
                        return yaml.safe_load(f) or {}
                except Exception:
                    pass
        
        return {}


@click.group()
@click.option("--config", type=click.Path(exists=True), help="Path to configuration file")
@click.option("--api-url", default=None, help="Base URL for API endpoint")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.pass_context
def cli(ctx, config, api_url, verbose):
    """Draft Queen CLI - Manage and analyze NFL draft data.
    
    \b
    Commands:
      pipeline   - Manage and monitor the data pipeline
      prospects  - Query and export prospect data
      quality    - Manage data quality rules and violations
      config     - Manage CLI configuration and authentication
      auth       - Authenticate with the backend
      health     - System diagnostics and health checks
    
    \b
    Examples:
      dq pipeline status
      dq prospects list --position QB
      dq quality violations
      dq config show
      dq auth login
    """
    cli_context = CliContext(config_file=config, api_url=api_url)
    cli_context.verbose = verbose
    
    # Ensure context object exists
    ctx.ensure_object(dict)
    ctx.obj = {
        "config": cli_context.config,
        "client": cli_context.client,
        "api_url": cli_context.api_url,
        "verbose": verbose,
        "cli_context": cli_context,
    }


# Register command groups
cli.add_command(pipeline)
cli.add_command(prospects)
cli.add_command(history)


@cli.command()
@click.pass_context
def version(ctx):
    """Show CLI and backend version information.
    
    Example:
        $ dq version
    """
    from rich.console import Console
    
    console = Console()
    
    console.print("[bold cyan]Draft Queen CLI[/bold cyan]")
    console.print(f"  CLI Version: 0.1.0")
    
    try:
        client = ctx.obj.get("client")
        response = client.get_version_info()
        console.print(f"  Backend Version: {response.get('version', 'unknown')}")
    except Exception as e:
        console.print(f"  Backend Version: [red]unavailable[/red]")
        if ctx.obj.get("verbose"):
            console.print(f"    Error: {e}")


def main():
    """Main entry point for CLI."""
    try:
        cli(obj={})
    except Exception as e:
        from rich.console import Console
        console = Console()
        console.print(f"[red]Error: {e}[/red]")
        exit(1)


if __name__ == "__main__":
    main()
