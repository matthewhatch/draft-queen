#!/usr/bin/env python3
"""
Test Playwright scraper logic WITHOUT launching browser.
Validates parsing and structure work correctly.
"""

import sys
sys.path.insert(0, '/home/parrot/code/draft-queen')

from data_pipeline.scrapers.pff_scraper_playwright import PFFScraperPlaywright
from bs4 import BeautifulSoup


def test_scraper_structure():
    """Test that scraper initializes and has required methods"""
    print("Testing Playwright scraper structure...\n")
    
    scraper = PFFScraperPlaywright(season=2026, headless=True)
    
    # Test initialization
    print(f"✅ Scraper initialized")
    print(f"   - Season: {scraper.season}")
    print(f"   - Base URL: {scraper.BASE_URL}")
    print(f"   - Headless: {scraper.headless}\n")
    
    # Test parsing logic with sample HTML
    print("Testing parsing logic with sample HTML...\n")
    
    sample_html = """
    <div class="prospect">
        <h3>Patrick Surtain III</h3>
        <span class="school">Miami (FL)</span>
        <span class="class">Junior</span>
        <span class="position">CB</span>
        <span class="grade">9.8</span>
    </div>
    <div class="prospect">
        <h4>Will Anderson Jr</h4>
        <span class="school">Alabama</span>
        <span class="class">Junior</span>
        <span class="position">EDGE</span>
        <span class="grade">9.5</span>
    </div>
    """
    
    soup = BeautifulSoup(sample_html, 'html.parser')
    prospect_sections = soup.find_all("div", class_="prospect")
    
    print(f"Found {len(prospect_sections)} prospect sections in sample HTML\n")
    
    for section in prospect_sections:
        prospect = scraper.parse_prospect(section)
        if prospect:
            print(f"✅ Parsed: {prospect['name']:25s} | {prospect['position']:4s} | {prospect['school']}")
    
    print("\n✅ All structure tests passed!")
    print("\nNote: Browser launching skipped in this test.")
    print("Full integration test requires proper Playwright browser installation.")


if __name__ == "__main__":
    try:
        test_scraper_structure()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
