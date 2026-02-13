"""Historical data commands (US-028)."""

import click
import json
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.status import Status
from datetime import datetime

console = Console()


@click.group()
def history():
    """Access historical prospect data and snapshots."""
    pass


@history.command()
@click.argument("prospect_id")
@click.option("--json-output", is_flag=True, help="Output as JSON")
@click.option("--limit", default=20, type=int, help="Number of changes to show")
@click.pass_context
def get(ctx, prospect_id, json_output, limit):
    """Show historical changes for a specific prospect.
    
    Examples:
        $ dq history get abc123
        $ dq history get abc123 --limit 50 --json-output
    """
    from cli.client import APIClient
    
    client: APIClient = ctx.obj.get("client")
    
    try:
        with Status(f"[bold cyan]Fetching history for {prospect_id}...", console=console) as status:
            response = client.get_prospect_history(prospect_id)
        
        if not response.get("changes"):
            console.print(f"[yellow]No history found for prospect {prospect_id}[/yellow]")
            return
        
        changes = response["changes"][:limit]
        
        if json_output:
            console.print_json(data=changes)
        else:
            # Display as table
            table = Table(title=f"History for Prospect {prospect_id} (last {len(changes)} changes)", 
                         show_header=True, header_style="bold magenta")
            table.add_column("Date", style="cyan")
            table.add_column("Field", style="yellow")
            table.add_column("Old Value", style="red")
            table.add_column("New Value", style="green")
            table.add_column("Source", style="blue")
            
            for change in changes:
                table.add_row(
                    change.get("timestamp", "N/A")[:10],
                    change.get("field", "N/A"),
                    str(change.get("old_value", "N/A"))[:30],
                    str(change.get("new_value", "N/A"))[:30],
                    change.get("source", "N/A")
                )
            
            console.print(table)
            
            # Summary statistics
            console.print()
            console.print("[dim]Earliest change:[/dim]", changes[-1].get("timestamp", "N/A")[:10])
            console.print("[dim]Latest change:[/dim]", changes[0].get("timestamp", "N/A")[:10])
    
    except Exception as e:
        console.print(f"[red]Error fetching history: {e}[/red]")
        ctx.exit(1)


@history.command()
@click.argument("snapshot_date")
@click.option("--position", type=str, help="Filter by position")
@click.option("--college", type=str, help="Filter by college")
@click.option("--limit", default=50, type=int, help="Number of records")
@click.option("--json-output", is_flag=True, help="Output as JSON")
@click.pass_context
def snapshot(ctx, snapshot_date, position, college, limit, json_output):
    """Get prospect data as it existed on a specific date.
    
    This allows you to query historical snapshots to see how data
    looked on any previous date.
    
    Examples:
        $ dq history snapshot 2026-02-01
        $ dq history snapshot 2026-01-15 --position QB
        $ dq history snapshot 2025-12-01 --limit 100 --json-output
    """
    from cli.client import APIClient
    
    client: APIClient = ctx.obj.get("client")
    
    # Validate date format
    try:
        datetime.strptime(snapshot_date, "%Y-%m-%d")
    except ValueError:
        console.print("[red]Invalid date format. Use YYYY-MM-DD (e.g., 2026-02-01)[/red]")
        ctx.exit(1)
    
    try:
        with Status(f"[bold cyan]Fetching snapshot for {snapshot_date}...", console=console) as status:
            response = client.get_snapshot(snapshot_date)
        
        if not response.get("prospects"):
            console.print(f"[yellow]No data found for date {snapshot_date}[/yellow]")
            return
        
        prospects = response["prospects"]
        
        # Apply filters if requested
        if position:
            prospects = [p for p in prospects if p.get("position") == position]
        if college:
            prospects = [p for p in prospects if p.get("college") == college]
        
        prospects = prospects[:limit]
        
        if json_output:
            console.print_json(data=prospects)
        else:
            # Display as table
            table = Table(title=f"Prospect Snapshot as of {snapshot_date} ({len(prospects)} records)", 
                         show_header=True, header_style="bold magenta")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Position", style="yellow")
            table.add_column("College", style="blue")
            table.add_column("Height", style="white")
            table.add_column("Weight", style="white")
            
            for prospect in prospects:
                table.add_row(
                    str(prospect.get("id", "N/A"))[:8],
                    prospect.get("name", "N/A"),
                    prospect.get("position", "N/A"),
                    prospect.get("college", "N/A"),
                    f"{prospect.get('height', 'N/A')}\"",
                    f"{prospect.get('weight', 'N/A')} lbs"
                )
            
            console.print(table)
            console.print(f"\n[dim]Data snapshot captured on {snapshot_date}[/dim]")
    
    except Exception as e:
        console.print(f"[red]Error fetching snapshot: {e}[/red]")
        ctx.exit(1)
