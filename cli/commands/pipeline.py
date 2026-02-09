"""Pipeline management commands (US-027)."""

import click
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.status import Status
from datetime import datetime
import json

console = Console()


@click.group()
def pipeline():
    """Manage and monitor the data pipeline."""
    pass


@pipeline.command()
@click.pass_context
def status(ctx):
    """Show current pipeline execution status.
    
    Example:
        $ dq pipeline status
    """
    from cli.client import APIClient
    
    client: APIClient = ctx.obj.get("client")
    
    try:
        with Status("[bold cyan]Fetching pipeline status...", console=console) as status:
            response = client.get_pipeline_status()
        
        # Display status information
        table = Table(title="Pipeline Status", show_header=True, header_style="bold magenta")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        
        for key, value in response.items():
            if isinstance(value, (dict, list)):
                value = json.dumps(value, indent=2)
            table.add_row(str(key), str(value))
        
        console.print(table)
    
    except Exception as e:
        console.print(f"[red]Error fetching pipeline status: {e}[/red]")
        ctx.exit(1)


@pipeline.command()
@click.option("--stages", multiple=True, help="Specific stages to run (yahoo, espn, reconciliation, quality, snapshot)")
@click.pass_context
def run(ctx, stages):
    """Trigger immediate pipeline execution.
    
    Example:
        $ dq pipeline run
        $ dq pipeline run --stages yahoo --stages espn
    """
    from cli.client import APIClient
    
    client: APIClient = ctx.obj.get("client")
    
    try:
        with Status("[bold cyan]Triggering pipeline execution...", console=console) as status:
            stages_list = list(stages) if stages else None
            response = client.trigger_pipeline(stages=stages_list)
        
        if "execution_id" in response:
            console.print(f"[green]✓ Pipeline triggered successfully[/green]")
            console.print(f"  Execution ID: {response['execution_id']}")
            if stages_list:
                console.print(f"  Stages: {', '.join(stages_list)}")
        else:
            console.print("[yellow]Pipeline triggered[/yellow]")
            console.print(response)
    
    except Exception as e:
        console.print(f"[red]Error triggering pipeline: {e}[/red]")
        ctx.exit(1)


@pipeline.command()
@click.argument("execution_id")
@click.pass_context
def logs(ctx, execution_id):
    """View logs for specific execution.
    
    Example:
        $ dq pipeline logs abc123def456
    """
    from cli.client import APIClient
    
    client: APIClient = ctx.obj.get("client")
    
    try:
        with Status(f"[bold cyan]Fetching logs for execution {execution_id}...", console=console) as status:
            response = client.get_pipeline_logs(execution_id)
        
        if "logs" in response:
            console.print(f"[bold]Logs for execution {execution_id}[/bold]")
            console.print(response["logs"])
        else:
            console.print(response)
    
    except Exception as e:
        console.print(f"[red]Error fetching logs: {e}[/red]")
        ctx.exit(1)


@pipeline.command()
@click.option("--limit", default=10, type=int, help="Number of recent executions to show")
@click.pass_context
def history(ctx, limit):
    """Show pipeline execution history.
    
    Example:
        $ dq pipeline history
        $ dq pipeline history --limit 20
    """
    from cli.client import APIClient
    
    client: APIClient = ctx.obj.get("client")
    
    try:
        with Status("[bold cyan]Fetching pipeline history...", console=console) as status:
            response = client.get_pipeline_history(limit=limit)
        
        if "executions" in response:
            table = Table(title=f"Last {limit} Pipeline Executions", show_header=True, header_style="bold magenta")
            table.add_column("ID", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("Started", style="yellow")
            table.add_column("Duration", style="blue")
            
            for exec_info in response["executions"]:
                status_color = "green" if exec_info.get("status") == "success" else "red" if exec_info.get("status") == "failed" else "yellow"
                table.add_row(
                    exec_info.get("id", "N/A"),
                    f"[{status_color}]{exec_info.get('status', 'N/A')}[/{status_color}]",
                    exec_info.get("started_at", "N/A"),
                    exec_info.get("duration", "N/A")
                )
            
            console.print(table)
        else:
            console.print(response)
    
    except Exception as e:
        console.print(f"[red]Error fetching history: {e}[/red]")
        ctx.exit(1)


@pipeline.command()
@click.argument("execution_id")
@click.pass_context
def retry(ctx, execution_id):
    """Retry failed pipeline execution.
    
    Example:
        $ dq pipeline retry abc123def456
    """
    from cli.client import APIClient
    
    client: APIClient = ctx.obj.get("client")
    
    if not click.confirm(f"Retry execution {execution_id}?"):
        console.print("[yellow]Cancelled[/yellow]")
        return
    
    try:
        with Status(f"[bold cyan]Retrying execution {execution_id}...", console=console) as status:
            response = client.retry_pipeline_execution(execution_id)
        
        console.print(f"[green]✓ Execution retry started[/green]")
        if "new_execution_id" in response:
            console.print(f"  New execution ID: {response['new_execution_id']}")
    
    except Exception as e:
        console.print(f"[red]Error retrying execution: {e}[/red]")
        ctx.exit(1)


@pipeline.group()
def config():
    """Manage pipeline configuration."""
    pass


@config.command("show")
@click.pass_context
def config_show(ctx):
    """Display current configuration.
    
    Example:
        $ dq pipeline config show
    """
    from cli.client import APIClient
    
    client: APIClient = ctx.obj.get("client")
    
    try:
        with Status("[bold cyan]Fetching configuration...", console=console) as status:
            response = client.get_pipeline_config()
        
        table = Table(title="Pipeline Configuration", show_header=True, header_style="bold magenta")
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="green")
        
        for key, value in response.items():
            if isinstance(value, (dict, list)):
                value = json.dumps(value, indent=2)
            table.add_row(str(key), str(value))
        
        console.print(table)
    
    except Exception as e:
        console.print(f"[red]Error fetching configuration: {e}[/red]")
        ctx.exit(1)


@config.command("set")
@click.argument("key")
@click.argument("value")
@click.pass_context
def config_set(ctx, key, value):
    """Update pipeline configuration.
    
    Example:
        $ dq pipeline config set retry_attempts 5
        $ dq pipeline config set timeout 300
    """
    from cli.client import APIClient
    
    client: APIClient = ctx.obj.get("client")
    
    # Try to parse value as JSON for complex types
    try:
        parsed_value = json.loads(value)
    except json.JSONDecodeError:
        parsed_value = value
    
    try:
        with Status(f"[bold cyan]Updating configuration...", console=console) as status:
            response = client.update_pipeline_config(key, parsed_value)
        
        console.print(f"[green]✓ Configuration updated[/green]")
        console.print(f"  {key}: {parsed_value}")
    
    except Exception as e:
        console.print(f"[red]Error updating configuration: {e}[/red]")
        ctx.exit(1)
