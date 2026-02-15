#!/usr/bin/env python3
"""
PFF Scraper Example/Test Runner

Demonstrates the production scraper with:
- Logging output
- Cache handling
- Error recovery
- Summary statistics
"""

import asyncio
import sys


async def main():
    """Run PFF scraper example"""
    # Add src to path
    from pathlib import Path
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root / "src"))

    from data_pipeline.scrapers.pff_scraper import PFFScraper

    print("=" * 70)
    print("PFF Scraper - Production Example")
    print("=" * 70)
    print()

    # Initialize scraper with cache enabled
    scraper = PFFScraper(season=2026, headless=True, cache_enabled=True)

    # Scrape up to 2 pages
    prospects = await scraper.scrape_all_pages(max_pages=2)

    # Print summary
    scraper.print_summary()

    # Print sample prospects if available
    if prospects:
        print("Sample Prospects:")
        print("-" * 70)
        for i, prospect in enumerate(prospects[:5], 1):
            print(f"\n{i}. {prospect['name']}")
            if prospect.get("position"):
                print(f"   Position: {prospect['position']}")
            if prospect.get("school"):
                print(f"   School: {prospect['school']}")
            if prospect.get("class"):
                print(f"   Class: {prospect['class']}")
            if prospect.get("grade"):
                print(f"   Grade: {prospect['grade']}")

        print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
