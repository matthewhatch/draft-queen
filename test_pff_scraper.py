#!/usr/bin/env python3
"""
Test script for PFF.com Draft Big Board Scraper

Tests the scraper with various scenarios:
- Cache loading
- Single page scraping
- Multi-page scraping
- Data validation
- Summary generation

Usage:
    poetry run python test_pff_scraper.py [--pages N] [--no-cache] [--headless/--no-headless]

Examples:
    poetry run python test_pff_scraper.py                    # Scrape 3 pages with cache
    poetry run python test_pff_scraper.py --pages 5          # Scrape 5 pages
    poetry run python test_pff_scraper.py --no-cache         # Disable cache
    poetry run python test_pff_scraper.py --no-headless      # Show browser window
"""

import asyncio
import logging
import argparse
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress
from typing import List, Dict, Any

from data_pipeline.scrapers.pff_scraper import PFFScraper, PFFProspectValidator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
console = Console()


def print_header(title: str) -> None:
    """Print a formatted header."""
    console.print(f"\n[bold cyan]{title}[/bold cyan]")
    console.print("[dim]" + "=" * 100 + "[/dim]")


def print_prospects_table(prospects: List[Dict[str, Any]]) -> None:
    """Display prospects in a formatted table."""
    if not prospects:
        console.print("[yellow]⚠️  No prospects to display[/yellow]")
        return
    
    table = Table(title=f"PFF Prospects ({len(prospects)} total)", show_header=True, header_style="bold magenta")
    table.add_column("Name", style="cyan", width=25)
    table.add_column("Pos", style="yellow")
    table.add_column("School", style="green", width=20)
    table.add_column("Class", style="blue")
    table.add_column("Ht/Wt", style="white")
    table.add_column("Grade", style="red")
    
    for prospect in prospects[:50]:  # Limit to 50 rows for readability
        ht_wt = ""
        if prospect.get("height") and prospect.get("weight"):
            ht_wt = f"{prospect.get('height')}/{prospect.get('weight')}"
        elif prospect.get("height"):
            ht_wt = prospect.get("height")
        elif prospect.get("weight"):
            ht_wt = prospect.get("weight")
        
        table.add_row(
            prospect.get("name", "N/A"),
            prospect.get("position", "N/A"),
            prospect.get("school", "N/A"),
            prospect.get("class", "N/A"),
            ht_wt,
            prospect.get("grade", "N/A"),
        )
    
    console.print(table)
    
    if len(prospects) > 50:
        console.print(f"[dim]... and {len(prospects) - 50} more prospects[/dim]")


def print_summary(scraper: PFFScraper) -> None:
    """Print summary statistics."""
    summary = scraper.get_summary()
    
    print_header("SCRAPE SUMMARY")
    
    console.print(f"[green]✓[/green] Total Prospects: [bold]{summary['total_prospects']}[/bold]")
    console.print(f"[dim]Scraped at: {summary['scraped_at']}[/dim]")
    
    # Position breakdown
    if summary["by_position"]:
        console.print("\n[bold]📊 By Position:[/bold]")
        table = Table(show_header=False, show_edge=False)
        for pos in sorted(summary["by_position"].keys()):
            count = summary["by_position"][pos]
            bar_length = count // 5
            bar = "█" * bar_length
            table.add_row(f"[yellow]{pos:5s}[/yellow]", f"[cyan]{count:3d}[/cyan]", f"[dim]{bar}[/dim]")
        console.print(table)
    
    # School breakdown
    if summary["by_school"]:
        console.print("\n[bold]🏫 Top Schools:[/bold]")
        sorted_schools = sorted(
            summary["by_school"].items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:15]
        
        table = Table(show_header=False, show_edge=False)
        for school, count in sorted_schools:
            bar_length = count // 2
            bar = "█" * bar_length
            table.add_row(f"[blue]{school:30s}[/blue]", f"[cyan]{count:2d}[/cyan]", f"[dim]{bar}[/dim]")
        console.print(table)
    
    # Grade statistics
    grades = [float(p.get("grade", 0)) for p in scraper.prospects if p.get("grade")]
    if grades:
        avg_grade = sum(grades) / len(grades)
        max_grade = max(grades)
        min_grade = min(grades)
        console.print(f"\n[bold]⭐ Grade Statistics:[/bold]")
        console.print(f"  [red]Average:[/red] [bold]{avg_grade:.1f}[/bold]")
        console.print(f"  [green]Max:[/green] [bold]{max_grade:.1f}[/bold]")
        console.print(f"  [yellow]Min:[/yellow] [bold]{min_grade:.1f}[/bold]")


def validate_prospects(prospects: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate all prospects and return validation report."""
    report = {
        "total": len(prospects),
        "valid": 0,
        "invalid": 0,
        "issues": [],
    }
    
    for prospect in prospects:
        if PFFProspectValidator.validate_prospect(prospect):
            report["valid"] += 1
        else:
            report["invalid"] += 1
            report["issues"].append({
                "name": prospect.get("name"),
                "reason": "Failed validation"
            })
    
    return report


def print_validation_report(report: Dict[str, Any]) -> None:
    """Print data validation report."""
    print_header("DATA VALIDATION REPORT")
    
    total = report["total"]
    valid = report["valid"]
    invalid = report["invalid"]
    
    valid_pct = (valid / total * 100) if total > 0 else 0
    invalid_pct = (invalid / total * 100) if total > 0 else 0
    
    console.print(f"Total Prospects: [bold]{total}[/bold]")
    console.print(f"[green]✓ Valid:[/green] [bold]{valid}[/bold] ([green]{valid_pct:.1f}%[/green])")
    console.print(f"[red]✗ Invalid:[/red] [bold]{invalid}[/bold] ([red]{invalid_pct:.1f}%[/red])")
    
    if report["issues"]:
        console.print(f"\n[bold]Issues Found:[/bold]")
        for issue in report["issues"][:10]:
            console.print(f"  [yellow]•[/yellow] {issue['name']}: {issue['reason']}")
        if len(report["issues"]) > 10:
            console.print(f"  [dim]... and {len(report['issues']) - 10} more[/dim]")


async def test_single_page(scraper: PFFScraper) -> None:
    """Test scraping a single page."""
    print_header("TEST: Single Page Scrape")
    
    console.print("[cyan]Scraping page 1...[/cyan]")
    prospects = await scraper.scrape_page(1)
    
    console.print(f"\n[green]✓[/green] Scraped [bold]{len(prospects)}[/bold] prospects")
    
    if prospects:
        print_prospects_table(prospects)
    else:
        console.print("[yellow]⚠️  No prospects found on page 1[/yellow]")


async def test_multi_page(scraper: PFFScraper, max_pages: int = 3) -> None:
    """Test scraping multiple pages."""
    print_header(f"TEST: Multi-Page Scrape ({max_pages} pages)")
    
    with Progress() as progress:
        task = progress.add_task("[cyan]Scraping pages...", total=max_pages)
        
        prospects = await scraper.scrape_all_pages(max_pages=max_pages)
        progress.update(task, completed=max_pages)
    
    console.print(f"\n[green]✓[/green] Scraped [bold]{len(prospects)}[/bold] prospects total")
    
    # Show sample
    if prospects:
        console.print("\n[bold]Sample Prospects:[/bold]")
        print_prospects_table(prospects[:10])


async def test_cache(scraper: PFFScraper) -> None:
    """Test cache functionality."""
    print_header("TEST: Cache Functionality")
    
    console.print("[cyan]Attempting to load from cache (page 1)...[/cyan]")
    
    # First load (may hit live scraper)
    console.print("[dim]First load:[/dim]")
    prospects1 = await scraper.scrape_page(1)
    console.print(f"  Found {len(prospects1)} prospects")
    
    # Second load (should hit cache)
    console.print("[dim]Second load (should use cache):[/dim]")
    prospects2 = await scraper.scrape_page(1)
    console.print(f"  Found {len(prospects2)} prospects")
    
    # Verify cache is working
    if len(prospects1) == len(prospects2) and len(prospects1) > 0:
        console.print("[green]✓ Cache working correctly[/green]")
    else:
        console.print("[yellow]⚠️  Cache behavior unexpected[/yellow]")


async def main():
    """Main test execution."""
    parser = argparse.ArgumentParser(
        description="Test PFF.com Draft Big Board Scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("--pages", type=int, default=3, help="Number of pages to scrape (default: 3)")
    parser.add_argument("--no-cache", action="store_true", help="Disable cache")
    parser.add_argument("--headless", action="store_true", default=True, help="Run browser in headless mode (default: True)")
    parser.add_argument("--no-headless", dest="headless", action="store_false", help="Show browser window")
    parser.add_argument("--test", choices=["single", "multi", "cache", "all"], default="all", help="Test type to run")
    
    args = parser.parse_args()
    
    # Print banner
    console.print("[bold cyan]" + "=" * 100 + "[/bold cyan]")
    console.print("[bold cyan]PFF SCRAPER TEST SUITE[/bold cyan]".center(100))
    console.print("[bold cyan]" + "=" * 100 + "[/bold cyan]")
    
    console.print(f"\n[dim]Configuration:[/dim]")
    console.print(f"  Max Pages: {args.pages}")
    console.print(f"  Cache: {'Enabled' if not args.no_cache else 'Disabled'}")
    console.print(f"  Headless: {args.headless}")
    console.print(f"  Test Type: {args.test}")
    console.print()
    
    try:
        # Initialize scraper
        scraper = PFFScraper(
            season=2026,
            headless=args.headless,
            cache_enabled=not args.no_cache,
        )
        
        # Run tests
        if args.test in ("single", "all"):
            await test_single_page(scraper)
        
        if args.test in ("multi", "all"):
            # Create fresh scraper for multi-page test
            scraper = PFFScraper(
                season=2026,
                headless=args.headless,
                cache_enabled=not args.no_cache,
            )
            await test_multi_page(scraper, max_pages=args.pages)
        
        if args.test in ("cache", "all"):
            # Create fresh scraper for cache test
            scraper = PFFScraper(
                season=2026,
                headless=args.headless,
                cache_enabled=not args.no_cache,
            )
            await test_cache(scraper)
        
        # Final summary and validation
        if scraper.prospects:
            print_summary(scraper)
            
            validation_report = validate_prospects(scraper.prospects)
            print_validation_report(validation_report)
        
        console.print("\n[green]✓ All tests completed[/green]\n")
        return 0
        
    except Exception as e:
        console.print(f"\n[red]❌ Test failed: {e}[/red]")
        logger.exception("Test error")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
