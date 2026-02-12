"""
PFF.com Draft Big Board Scraper - Corrected PoC with Selenium

UPDATE (Feb 10, 2026):
    Initial testing revealed the page IS JavaScript-rendered, not server-rendered.
    This version uses Selenium to execute JavaScript and render the DOM before parsing.

Technology Stack:
    - selenium==4.15.2 (browser automation)
    - beautifulsoup4==4.12.2 (HTML parsing after rendering)
    - lxml==4.9.3 (fast parser)
    - webdriver-manager==4.0.1 (automatic driver management)

Installation:
    pip install selenium beautifulsoup4 lxml webdriver-manager

Note:
    For production, consider:
    - Playwright (faster, more modern)
    - Puppeteer/Pyppeteer
    - Or find/negotiate access to official API
"""

import time
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup


class PFFScraperSelenium:
    """PFF Draft Big Board scraper using Selenium for JavaScript rendering"""

    BASE_URL = "https://www.pff.com/draft/big-board"

    def __init__(self, season: int = 2026, headless: bool = True):
        """
        Initialize scraper with Selenium WebDriver

        Args:
            season: Draft year (default 2026)
            headless: Run browser in headless mode (no GUI)
        """
        self.season = season
        self.headless = headless
        self.driver = None
        self.prospects = []

    def setup_driver(self) -> webdriver.Chrome:
        """
        Set up Selenium WebDriver with Chrome

        Returns:
            Configured Chrome WebDriver instance
        """
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless")
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        return driver

    def fetch_and_render_page(self, page: int) -> Optional[str]:
        """
        Fetch page and render JavaScript

        Args:
            page: Page number (1-indexed)

        Returns:
            Rendered HTML or None if fetch fails
        """
        try:
            url = f"{self.BASE_URL}?season={self.season}&page={page}"
            print(f"Loading page {page} in browser: {url}...")
            
            self.driver.get(url)
            
            # Wait for prospect data to load
            # Look for prospect cards or specific elements
            wait = WebDriverWait(self.driver, 10)
            
            # Wait for h3/h4 elements (prospect names) to appear
            try:
                wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "h3, h4")))
                print(f"  ✓ Page {page} rendered ({len(self.driver.page_source)} bytes)")
                
                # Give it a moment for all elements to fully load
                time.sleep(1)
                
                return self.driver.page_source
                
            except Exception as e:
                print(f"  ⚠️  Timeout waiting for elements: {e}")
                # Return what we have anyway
                return self.driver.page_source
            
        except Exception as e:
            print(f"  ✗ Error loading page {page}: {e}")
            return None

    def parse_prospect(self, prospect_section) -> Optional[Dict]:
        """
        Parse prospect from a section of HTML

        Args:
            prospect_section: BeautifulSoup element with prospect info

        Returns:
            Dictionary with prospect data or None
        """
        try:
            # Look for the name (usually in h3/h4)
            name_elem = prospect_section.find(["h3", "h4"])
            if not name_elem:
                return None
            
            name = name_elem.get_text(strip=True)
            if not name:
                return None

            # Extract text from the section
            text = prospect_section.get_text()
            
            # Parse position, class, school (usually on same line)
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            # Position is usually marked as "POSITION [value]"
            position = None
            player_class = None
            school = None
            height = None
            weight = None
            
            for i, line in enumerate(lines):
                if line.startswith("POSITION"):
                    position = lines[i+1] if i+1 < len(lines) else None
                elif line.startswith("CLASS"):
                    player_class = lines[i+1] if i+1 < len(lines) else None
                elif line.startswith("SCHOOL"):
                    school = lines[i+1] if i+1 < len(lines) else None
                elif line.startswith("HEIGHT"):
                    height = lines[i+1] if i+1 < len(lines) else None
                elif line.startswith("WEIGHT"):
                    weight_text = lines[i+1] if i+1 < len(lines) else None
                    if weight_text and weight_text != "—":
                        try:
                            weight = int(weight_text)
                        except:
                            pass

            return {
                "name": name,
                "position": position,
                "class": player_class,
                "school": school,
                "height": height,
                "weight": weight,
                "season": self.season,
            }

        except Exception as e:
            print(f"  Error parsing prospect: {e}")
            return None

    def extract_prospects_from_html(self, html: str) -> List[Dict]:
        """
        Extract all prospects from rendered HTML

        Args:
            html: Rendered HTML content

        Returns:
            List of prospect dictionaries
        """
        prospects = []
        try:
            soup = BeautifulSoup(html, "lxml")
            
            # Find all h3/h4 elements (prospect names)
            headings = soup.find_all(["h3", "h4"])
            
            print(f"  Found {len(headings)} potential prospects on page")
            
            for heading in headings:
                # Get the nearest parent section/container
                section = heading.find_parent()
                for _ in range(5):
                    if section:
                        prospect_data = self.parse_prospect(section)
                        if prospect_data:
                            prospects.append(prospect_data)
                            break
                    section = section.parent if section else None
            
            print(f"  ✓ Extracted {len(prospects)} prospects from page")
            return prospects

        except Exception as e:
            print(f"  ✗ Error extracting prospects: {e}")
            return []

    def scrape_all_pages(self, max_pages: Optional[int] = 2) -> List[Dict]:
        """
        Scrape all pages of the PFF Big Board

        Args:
            max_pages: Maximum pages to scrape (for testing)

        Returns:
            List of all prospects across all pages
        """
        try:
            self.driver = self.setup_driver()
            
            print(f"\n{'='*60}")
            print(f"PFF Draft Big Board Scraper (Selenium) - Season {self.season}")
            print(f"{'='*60}\n")

            all_prospects = []
            page = 1
            consecutive_failures = 0
            max_consecutive_failures = 2

            while True:
                if max_pages and page > max_pages:
                    print(f"\nReached max pages limit ({max_pages})")
                    break

                html = self.fetch_and_render_page(page)
                
                if not html:
                    consecutive_failures += 1
                    if consecutive_failures >= max_consecutive_failures:
                        print(f"\nStopped: {max_consecutive_failures} consecutive failures")
                        break
                    time.sleep(2)
                    page += 1
                    continue

                consecutive_failures = 0
                prospects = self.extract_prospects_from_html(html)
                
                if not prospects:
                    print(f"  No prospects extracted on page {page} - likely end of pages")
                    break

                all_prospects.extend(prospects)
                
                time.sleep(1)  # Respectful rate limiting
                page += 1

            print(f"\n{'='*60}")
            print(f"Scraping Complete: {len(all_prospects)} total prospects")
            print(f"{'='*60}\n")

            self.prospects = all_prospects
            return all_prospects

        finally:
            if self.driver:
                self.driver.quit()
                print("✓ Browser closed")

    def print_sample(self, count: int = 5) -> None:
        """
        Print sample prospects to console

        Args:
            count: Number of samples to print
        """
        print(f"\n{'='*60}")
        print(f"Sample Prospects (first {count})")
        print(f"{'='*60}\n")

        for i, prospect in enumerate(self.prospects[:count], 1):
            print(f"{i}. {prospect['name']:25s} {prospect['position']:4s if prospect['position'] else 'N/A':4s}")
            if prospect['school']:
                print(f"   School: {prospect['school']:20s} Class: {prospect['class'] if prospect['class'] else 'N/A'}")
            if prospect['height']:
                print(f"   Height: {prospect['height']:8s} Weight: {prospect['weight']}")
            print()


# ============================================================================
# EXAMPLE USAGE / TESTING
# ============================================================================

if __name__ == "__main__":
    """
    Test the corrected Selenium-based scraper

    Note:
        This requires Selenium and ChromeDriver
        Installation: pip install selenium webdriver-manager beautifulsoup4 lxml
        
    First run will download ChromeDriver (~200MB)
    """
    
    print("⚠️  IMPORTANT NOTICE:")
    print("=" * 60)
    print("This PoC requires Selenium and ChromeDriver to be installed.")
    print("Install dependencies with:")
    print("  pip install selenium webdriver-manager beautifulsoup4 lxml")
    print("=" * 60)
    print()
    
    try:
        # Initialize scraper
        scraper = PFFScraperSelenium(season=2026, headless=True)

        # Scrape (limited to 2 pages for testing)
        prospects = scraper.scrape_all_pages(max_pages=2)

        # Print samples
        if prospects:
            scraper.print_sample(count=10)
            print(f"\n✓ Successfully scraped {len(prospects)} prospects")
        else:
            print("⚠️  No prospects scraped - check page structure")
            
    except ImportError as e:
        print(f"\n✗ Missing dependency: {e}")
        print("\nPlease install required packages:")
        print("  pip install selenium webdriver-manager beautifulsoup4 lxml")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
