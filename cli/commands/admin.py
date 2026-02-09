"""System administration commands (US-030)."""

import click
from rich.console import Console
from rich.status import Status
from rich.table import Table
from rich.panel import Panel

console = Console()


@click.group()
def health():
    """System diagnostics and health checks."""
    pass


@health.command("check")
@click.pass_context
def health_check(ctx):
    """Perform system health check.
    
    Verifies connectivity and status of all system components.
    
    Example:
        $ dq health check
    """
    from cli.client import APIClient
    
    client: APIClient = ctx.obj.get("client")
    
    try:
        with Status("[bold cyan]Running health checks...", console=console) as status:
            response = client.health_check()
        
        console.print()
        
        if response.get("status") == "healthy":
            console.print(Panel("[green]✓ System Healthy[/green]", expand=False))
        else:
            console.print(Panel("[yellow]⚠ System Issues Detected[/yellow]", expand=False))
        
        # Display component status
        console.print()
        console.print("[bold]Component Status[/bold]")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details", style="white")
        
        components = response.get("components", {})
        for component_name, component_status in components.items():
            status_color = "green" if component_status.get("healthy", False) else "red"
            status_badge = f"[{status_color}]{'✓' if component_status.get('healthy', False) else '✗'}[/{status_color}]"
            
            table.add_row(
                component_name,
                status_badge,
                component_status.get("message", "")
            )
        
        console.print(table)
        
        # Overall metrics
        if response.get("metrics"):
            console.print()
            console.print("[bold]System Metrics[/bold]")
            
            metrics_table = Table(show_header=False, box=None)
            metrics_table.add_column("", style="cyan", width=20)
            metrics_table.add_column("", style="green")
            
            for metric_name, metric_value in response["metrics"].items():
                metrics_table.add_row(metric_name, str(metric_value))
            
            console.print(metrics_table)
    
    except Exception as e:
        console.print(f"[red]Health check failed: {e}[/red]")
        ctx.exit(1)


@click.group()
def db():
    """Database management commands."""
    pass


@db.command("migrate")
@click.pass_context
def db_migrate(ctx):
    """Run database migrations.
    
    Applies any pending database schema migrations to the database.
    
    Example:
        $ dq db migrate
    """
    from cli.client import APIClient
    
    client: APIClient = ctx.obj.get("client")
    
    if not click.confirm("[yellow]Run database migrations?[/yellow]"):
        console.print("[yellow]Cancelled[/yellow]")
        return
    
    try:
        with Status("[bold cyan]Running migrations...", console=console) as status:
            response = client.run_db_migration()
        
        console.print(f"[green]✓ Migrations completed[/green]")
        
        if response.get("migrations_applied"):
            console.print(f"  Applied {response['migrations_applied']} migration(s)")
        
        if response.get("current_version"):
            console.print(f"  Current schema version: {response['current_version']}")
    
    except Exception as e:
        console.print(f"[red]Migration failed: {e}[/red]")
        ctx.exit(1)


@db.command("backup")
@click.option("--output", "-o", type=click.Path(), help="Backup file path")
@click.pass_context
def db_backup(ctx, output):
    """Create database backup.
    
    Creates a backup of the database and optionally saves to file.
    
    Examples:
        $ dq db backup
        $ dq db backup --output backup.sql
    """
    from cli.client import APIClient
    from pathlib import Path
    from datetime import datetime
    
    client: APIClient = ctx.obj.get("client")
    
    if not click.confirm("[yellow]Create database backup?[/yellow]"):
        console.print("[yellow]Cancelled[/yellow]")
        return
    
    try:
        with Status("[bold cyan]Creating backup...", console=console) as status:
            response = client.create_db_backup()
        
        # Determine output path
        if output:
            backup_path = Path(output)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = Path(f"backup_{timestamp}.sql")
        
        # Save backup if content available
        if response.get("backup_id"):
            console.print(f"[green]✓ Backup created[/green]")
            console.print(f"  Backup ID: {response['backup_id']}")
            console.print(f"  Size: {response.get('size', 'N/A')}")
            console.print(f"  Location: {response.get('location', 'N/A')}")
        else:
            console.print("[yellow]Backup initiated[/yellow]")
    
    except Exception as e:
        console.print(f"[red]Backup failed: {e}[/red]")
        ctx.exit(1)


# Register db as a group
health.add_command(db)
