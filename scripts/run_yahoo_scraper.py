#!/usr/bin/env python3
"""
Script to run the Yahoo Sports scraper and display results.

Usage:
    poetry run python run_yahoo_scraper.py
"""

import logging
import json
from typing import List, Dict, Any
from rich.console import Console
from rich.table import Table
from data_pipeline.sources.yahoo_sports_scraper import YahooSportsConnector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
console = Console()


def print_prospects_table(prospects: List[Dict[str, Any]]) -> None:
    """Print prospects in a formatted table."""
    if not prospects:
        console.print("[yellow]⚠️  No prospects found[/yellow]")
        return
    
    table = Table(title="Yahoo Sports Prospects", show_header=True, header_style="bold magenta")
    table.add_column("Name", style="cyan")
    table.add_column("Position", style="yellow")
    table.add_column("College", style="green")
    table.add_column("Height", style="blue")
    table.add_column("Weight", style="blue")
    table.add_column("Grade", style="red")
    table.add_column("Source", style="white")
    
    for prospect in prospects:
        table.add_row(
            prospect.get("name", "N/A"),
            prospect.get("position", "N/A"),
            prospect.get("college", "N/A"),
            str(prospect.get("height", "N/A")),
            str(prospect.get("weight", "N/A")),
            str(prospect.get("draft_grade", "N/A")),
            prospect.get("data_source", "N/A"),
        )
    
    console.print(table)


def print_prospects_json(prospects: List[Dict[str, Any]]) -> None:
    """Print prospects in JSON format."""
    print("\n" + "=" * 120)
    print("YAHOO SPORTS PROSPECTS (JSON)".center(120))
    print("=" * 120)
    print(json.dumps(prospects, indent=2))
    print("=" * 120)


def print_summary(prospects: List[Dict[str, Any]]) -> None:
    """Print summary statistics."""
    if not prospects:
        console.print("[yellow]⚠️  No prospects to summarize[/yellow]")
        return
    
    # Count by position
    positions = {}
    for prospect in prospects:
        pos = prospect.get("position", "Unknown")
        positions[pos] = positions.get(pos, 0) + 1
    
    # Count by college
    colleges = {}
    for prospect in prospects:
        college = prospect.get("college", "Unknown")
        colleges[college] = colleges.get(college, 0) + 1
    
    console.print("\n[bold cyan]SUMMARY[/bold cyan]")
    console.print(f"[green]✓[/green] Total Prospects: [bold]{len(prospects)}[/bold]")
    
    console.print(f"\n[bold]📊 Prospects by Position:[/bold]")
    for pos, count in sorted(positions.items()):
        console.print(f"   [yellow]{pos:8}[/yellow] : [cyan]{count:3}[/cyan] prospects")
    
    console.print(f"\n[bold]🏫 Top Colleges (by prospect count):[/bold]")
    top_colleges = sorted(colleges.items(), key=lambda x: x[1], reverse=True)[:10]
    for college, count in top_colleges:
        console.print(f"   [blue]{college:30}[/blue] : [cyan]{count:3}[/cyan] prospects")
    
    # Grade statistics
    grades = [p.get("draft_grade") for p in prospects if p.get("draft_grade")]
    if grades:
        avg_grade = sum(grades) / len(grades)
        max_grade = max(grades)
        min_grade = min(grades)
        console.print(f"\n[bold]⭐ Draft Grade Statistics:[/bold]")
        console.print(f"   Average Grade: [red]{avg_grade:.2f}[/red]")
        console.print(f"   Max Grade: [green]{max_grade:.2f}[/green]")
        console.print(f"   Min Grade: [yellow]{min_grade:.2f}[/yellow]")


def get_mock_prospects() -> List[Dict[str, Any]]:
    """Return mock Yahoo Sports data for demonstration."""
    return [
        {
            "name": "Will Anderson Jr.",
            "position": "EDGE",
            "college": "Alabama",
            "height": 6.3,
            "weight": 243,
            "draft_grade": 9.4,
            "data_source": "yahoo_mock",
        },
        {
            "name": "Bryce Young",
            "position": "QB",
            "college": "Alabama",
            "height": 6.0,
            "weight": 200,
            "draft_grade": 9.1,
            "data_source": "yahoo_mock",
        },
        {
            "name": "C.J. Stroud",
            "position": "QB",
            "college": "Ohio State",
            "height": 6.3,
            "weight": 218,
            "draft_grade": 9.0,
            "data_source": "yahoo_mock",
        },
        {
            "name": "Anthony Richardson",
            "position": "OT",
            "college": "Florida",
            "height": 6.7,
            "weight": 315,
            "draft_grade": 8.8,
            "data_source": "yahoo_mock",
        },
        {
            "name": "Jalen Carter",
            "position": "DT",
            "college": "Georgia",
            "height": 6.3,
            "weight": 308,
            "draft_grade": 8.7,
            "data_source": "yahoo_mock",
        },
        {
            "name": "Quentin Johnston",
            "position": "WR",
            "college": "TCU",
            "height": 6.3,
            "weight": 208,
            "draft_grade": 8.4,
            "data_source": "yahoo_mock",
        },
        {
            "name": "Jordan Addison",
            "position": "WR",
            "college": "Pitt",
            "height": 6.0,
            "weight": 198,
            "draft_grade": 8.5,
            "data_source": "yahoo_mock",
        },
        {
            "name": "Dalton Kincaid",
            "position": "TE",
            "college": "Utah",
            "height": 6.4,
            "weight": 248,
            "draft_grade": 8.3,
            "data_source": "yahoo_mock",
        },
    ]


def main():
    """Main entry point."""
    logger.info("Starting Yahoo Sports Scraper")
    console.print("[cyan]🔄 Fetching prospects from Yahoo Sports...[/cyan]")
    
    try:
        # Initialize scraper
        scraper = YahooSportsConnector()
        
        # Fetch prospects
        prospects = scraper.fetch_prospects()
        
        # If no live data, use mock data for demonstration
        if not prospects:
            console.print("\n[yellow]⚠️  No prospects found from live Yahoo Sports scraper[/yellow]")
            console.print("[dim]Using mock data for demonstration...[/dim]")
            prospects = get_mock_prospects()
        
        if prospects:
            data_source = prospects[0].get("data_source", "unknown")
            source_label = "[yellow](MOCK DATA)[/yellow]" if "mock" in data_source else "[green](LIVE DATA)[/green]"
            console.print(f"\n[green]✅ Successfully fetched {len(prospects)} prospects! {source_label}[/green]")
            
            # Display results
            print_prospects_table(prospects)
            print_summary(prospects)
            
            # Optional: Print JSON for debugging
            if len(prospects) <= 20:
                print_prospects_json(prospects)
        else:
            console.print("\n[red]❌ No prospects available[/red]")
            
    except Exception as e:
        logger.error(f"Error running scraper: {e}", exc_info=True)
        console.print(f"\n[red]❌ Error: {e}[/red]")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
