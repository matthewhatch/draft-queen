"""Prospect data query and export commands (US-028)."""

import click
import json
import csv
import sys
from typing import Optional, List, Dict, Any
from rich.console import Console
from rich.table import Table
from rich.status import Status
from pathlib import Path

console = Console()


@click.group()
def prospects():
    """Query and export prospect data."""
    pass


@prospects.command()
@click.option("--limit", default=50, type=int, help="Number of prospects to return")
@click.option("--offset", default=0, type=int, help="Offset for pagination")
@click.option("--position", type=str, help="Filter by position (QB, RB, WR, etc)")
@click.option("--college", type=str, help="Filter by college")
@click.option("--height-min", type=float, help="Minimum height (inches)")
@click.option("--height-max", type=float, help="Maximum height (inches)")
@click.option("--weight-min", type=int, help="Minimum weight (lbs)")
@click.option("--weight-max", type=int, help="Maximum weight (lbs)")
@click.option("--json-output", is_flag=True, help="Output as JSON")
@click.pass_context
def list(ctx, limit, offset, position, college, height_min, height_max, weight_min, weight_max, json_output):
    """List all prospects with key statistics.
    
    Examples:
        $ dq prospects list
        $ dq prospects list --limit 100
        $ dq prospects list --position QB --college Alabama
        $ dq prospects list --height-min 6.0 --json-output
    """
    from cli.client import APIClient
    
    client: APIClient = ctx.obj.get("client")
    
    # Build filters
    filters = {}
    if position:
        filters["position"] = position
    if college:
        filters["college"] = college
    if height_min:
        filters["height_min"] = height_min
    if height_max:
        filters["height_max"] = height_max
    if weight_min:
        filters["weight_min"] = weight_min
    if weight_max:
        filters["weight_max"] = weight_max
    
    try:
        with Status("[bold cyan]Fetching prospects...", console=console) as status:
            response = client.list_prospects(limit=limit, offset=offset)
        
        if not response.get("prospects"):
            console.print("[yellow]No prospects found[/yellow]")
            return
        
        if json_output:
            console.print_json(data=response)
        else:
            # Display as table
            table = Table(title=f"Prospects (showing {len(response['prospects'])} of {response.get('total', '?')})", 
                         show_header=True, header_style="bold magenta")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Position", style="yellow")
            table.add_column("College", style="blue")
            table.add_column("Height", style="white")
            table.add_column("Weight", style="white")
            
            for prospect in response["prospects"]:
                table.add_row(
                    str(prospect.get("id", "N/A"))[:8],
                    prospect.get("name", "N/A"),
                    prospect.get("position", "N/A"),
                    prospect.get("college", "N/A"),
                    f"{prospect.get('height', 'N/A')}\"",
                    f"{prospect.get('weight', 'N/A')} lbs"
                )
            
            console.print(table)
            
            if response.get("total", 0) > limit:
                console.print(f"\n[dim]Showing {offset}-{offset + limit} of {response.get('total', '?')} prospects[/dim]")
    
    except Exception as e:
        console.print(f"[red]Error fetching prospects: {e}[/red]")
        ctx.exit(1)


@prospects.command()
@click.argument("name")
@click.option("--json-output", is_flag=True, help="Output as JSON")
@click.pass_context
def search(ctx, name, json_output):
    """Search prospects by name (fuzzy matching).
    
    Examples:
        $ dq prospects search "Patrick Mahomes"
        $ dq prospects search "mahomes" --json-output
    """
    from cli.client import APIClient
    
    client: APIClient = ctx.obj.get("client")
    
    try:
        with Status(f"[bold cyan]Searching for '{name}'...", console=console) as status:
            response = client.search_prospects(name)
        
        if not response.get("prospects"):
            console.print(f"[yellow]No prospects found matching '{name}'[/yellow]")
            return
        
        if json_output:
            console.print_json(data=response)
        else:
            # Display as table
            table = Table(title=f"Search Results for '{name}' ({len(response['prospects'])} found)", 
                         show_header=True, header_style="bold magenta")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Position", style="yellow")
            table.add_column("College", style="blue")
            table.add_column("Match %", style="white")
            
            for prospect in response["prospects"]:
                table.add_row(
                    str(prospect.get("id", "N/A"))[:8],
                    prospect.get("name", "N/A"),
                    prospect.get("position", "N/A"),
                    prospect.get("college", "N/A"),
                    f"{prospect.get('match_score', 'N/A'):.1f}%"
                )
            
            console.print(table)
    
    except Exception as e:
        console.print(f"[red]Error searching prospects: {e}[/red]")
        ctx.exit(1)


@prospects.command()
@click.argument("prospect_id")
@click.option("--json-output", is_flag=True, help="Output as JSON")
@click.pass_context
def get(ctx, prospect_id, json_output):
    """Show detailed prospect information.
    
    Examples:
        $ dq prospects get abc123
        $ dq prospects get abc123 --json-output
    """
    from cli.client import APIClient
    
    client: APIClient = ctx.obj.get("client")
    
    try:
        with Status(f"[bold cyan]Fetching prospect {prospect_id}...", console=console) as status:
            response = client.get_prospect(prospect_id)
        
        if not response.get("prospect"):
            console.print(f"[yellow]Prospect {prospect_id} not found[/yellow]")
            return
        
        prospect = response["prospect"]
        
        if json_output:
            console.print_json(data=prospect)
        else:
            # Display detailed information
            console.print(f"[bold cyan]{prospect.get('name', 'Unknown')}[/bold cyan]")
            console.print()
            
            # Basic info
            table = Table(show_header=False, box=None)
            table.add_column("", style="cyan", width=20)
            table.add_column("", style="green")
            
            table.add_row("ID", str(prospect.get("id", "N/A")))
            table.add_row("Position", prospect.get("position", "N/A"))
            table.add_row("College", prospect.get("college", "N/A"))
            table.add_row("Year", prospect.get("year", "N/A"))
            
            console.print(table)
            console.print()
            
            # Physical attributes
            if any(prospect.get(k) for k in ["height", "weight", "hand_size", "arm_length"]):
                console.print("[bold]Physical Attributes[/bold]")
                phys_table = Table(show_header=False, box=None)
                phys_table.add_column("", style="cyan", width=20)
                phys_table.add_column("", style="green")
                
                phys_table.add_row("Height", f"{prospect.get('height', 'N/A')}\"")
                phys_table.add_row("Weight", f"{prospect.get('weight', 'N/A')} lbs")
                phys_table.add_row("Hand Size", f"{prospect.get('hand_size', 'N/A')}\"")
                phys_table.add_row("Arm Length", f"{prospect.get('arm_length', 'N/A')}\"")
                
                console.print(phys_table)
                console.print()
            
            # Performance metrics
            if any(prospect.get(k) for k in ["forty_time", "vertical_jump", "broad_jump", "three_cone"]):
                console.print("[bold]Performance Metrics[/bold]")
                perf_table = Table(show_header=False, box=None)
                perf_table.add_column("", style="cyan", width=20)
                perf_table.add_column("", style="green")
                
                perf_table.add_row("40-Time", f"{prospect.get('forty_time', 'N/A')}s")
                perf_table.add_row("Vertical Jump", f"{prospect.get('vertical_jump', 'N/A')}\"")
                perf_table.add_row("Broad Jump", f"{prospect.get('broad_jump', 'N/A')}\"")
                perf_table.add_row("3-Cone Drill", f"{prospect.get('three_cone', 'N/A')}s")
                
                console.print(perf_table)
    
    except Exception as e:
        console.print(f"[red]Error fetching prospect: {e}[/red]")
        ctx.exit(1)


@prospects.command()
@click.option("--format", type=click.Choice(["json", "csv", "parquet"]), default="json", 
              help="Export format")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.option("--position", type=str, help="Filter by position")
@click.option("--college", type=str, help="Filter by college")
@click.option("--height-min", type=float, help="Minimum height (inches)")
@click.option("--height-max", type=float, help="Maximum height (inches)")
@click.option("--limit", default=None, type=int, help="Limit number of records")
@click.pass_context
def export(ctx, format, output, position, college, height_min, height_max, limit):
    """Export prospects in specified format.
    
    Examples:
        $ dq prospects export --format json --output prospects.json
        $ dq prospects export --format csv --output prospects.csv --position QB
        $ dq prospects export --format parquet --output prospects.parquet
    """
    from cli.client import APIClient
    
    client: APIClient = ctx.obj.get("client")
    
    # Build filters
    filters = {}
    if position:
        filters["position"] = position
    if college:
        filters["college"] = college
    if height_min:
        filters["height_min"] = height_min
    if height_max:
        filters["height_max"] = height_max
    if limit:
        filters["limit"] = limit
    
    try:
        with Status(f"[bold cyan]Exporting prospects as {format}...", console=console) as status:
            response = client.export_prospects(format=format, **filters)
        
        # Determine output destination
        if output:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            output_path = Path(f"prospects.{format}")
        
        # Write data to file
        if format == "json":
            with open(output_path, "w") as f:
                json.dump(response.get("data", []), f, indent=2)
        
        elif format == "csv":
            data = response.get("data", [])
            if data:
                # Write CSV
                with open(output_path, "w", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
        
        elif format == "parquet":
            # For parquet, write the response file if available
            if "file_content" in response:
                with open(output_path, "wb") as f:
                    f.write(response["file_content"])
        
        console.print(f"[green]✓ Exported {response.get('count', '?')} records[/green]")
        console.print(f"  Format: {format}")
        console.print(f"  Output: {output_path.resolve()}")
    
    except Exception as e:
        console.print(f"[red]Error exporting prospects: {e}[/red]")
        ctx.exit(1)
