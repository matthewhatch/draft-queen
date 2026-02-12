"""
PFF.com Draft Big Board Scraper - Proof of Concept

Purpose:
    Extracts prospect grades and rankings from PFF's Draft Big Board
    (https://www.pff.com/draft/big-board?season=2026)

Status:
    PROOF OF CONCEPT - Initial Analysis (Feb 10, 2026)

⚠️  IMPORTANT FINDING:
    - Page IS JavaScript-rendered (NOT server-rendered)
    - Initial analysis was incorrect
    - BeautifulSoup4 alone is NOT sufficient
    - Requires: Selenium/Playwright for JavaScript execution
    - OR: Find and use the JSON API endpoint

Key Findings (Updated):
    - robots.txt permits scraping (/draft/big-board not disallowed)
    - Initial HTML is empty (data loaded via JavaScript)
    - No public JSON API found (404/500 on common patterns)
    - Requires DOM rendering to access data
    - Complexity: MEDIUM (not LOW as initially assessed)

Data Fields Extracted:
    - PFF Rank (position on big board)
    - Player Name
    - Position (QB, ED, LB, S, HB, WR, CB, T, G, TE, etc.)
    - College Class (Jr, Sr, RS Jr, RS Sr)
    - School
    - Height (e.g., "6' 5\"")
    - Weight (e.g., "225")
    - Age (e.g., "20.6" or null)
    - PFF Overall Grade (e.g., "91.6")
    - Position-specific Rank (e.g., "9th / 315 QB")
    - Speed (often "—" if unavailable)
    - Profile URL

Dependencies:
    - beautifulsoup4==4.12.2
    - requests==2.31.0
    - lxml==4.9.3 (or html.parser)

Author: Data Engineering Team
Date: Feb 10, 2026
"""

import re
import time
from typing import List, Dict, Optional
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup


class PFFScraperPoC:
    """Proof-of-concept scraper for PFF Draft Big Board"""

    BASE_URL = "https://www.pff.com/draft/big-board"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        ),
        "Referer": "https://www.pff.com/",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    def __init__(self, season: int = 2026, delay_between_requests: float = 1.5):
        """
        Initialize scraper

        Args:
            season: Draft year (default 2026)
            delay_between_requests: Seconds to wait between page requests
        """
        self.season = season
        self.delay_between_requests = delay_between_requests
        self.prospects = []
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def fetch_page(self, page: int) -> Optional[str]:
        """
        Fetch HTML for a specific page

        Args:
            page: Page number (1-indexed)

        Returns:
            HTML content or None if fetch fails
        """
        try:
            url = f"{self.BASE_URL}?season={self.season}&page={page}"
            print(f"Fetching page {page} from {url}...")
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            print(f"  ✓ Page {page} fetched ({len(response.content)} bytes)")
            return response.text
            
        except requests.RequestException as e:
            print(f"  ✗ Error fetching page {page}: {e}")
            return None

    def parse_prospect(self, prospect_elem) -> Optional[Dict]:
        """
        Parse a single prospect element from the HTML

        Args:
            prospect_elem: BeautifulSoup element representing one prospect card

        Returns:
            Dictionary with prospect data or None if parsing fails
        """
        try:
            # Extract PFF Rank from the label "PFF Rank X"
            rank_text = prospect_elem.find("div", string=re.compile(r"PFF Rank"))
            if not rank_text or not rank_text.next_sibling:
                return None
            
            pff_rank = int(rank_text.next_sibling.string.strip())

            # Extract name (h3 or heading)
            name_elem = prospect_elem.find(["h3", "h4"])
            name = name_elem.get_text(strip=True) if name_elem else None
            if not name:
                return None

            # Extract position, class, school
            position_elem = prospect_elem.find("div", string=re.compile(r"POSITION"))
            position = (
                position_elem.next_sibling.strip()
                if position_elem and position_elem.next_sibling
                else None
            )

            class_elem = prospect_elem.find("div", string=re.compile(r"CLASS"))
            player_class = (
                class_elem.next_sibling.strip()
                if class_elem and class_elem.next_sibling
                else None
            )

            school_elem = prospect_elem.find("div", string=re.compile(r"SCHOOL"))
            school = (
                school_elem.next_sibling.strip()
                if school_elem and school_elem.next_sibling
                else None
            )

            # Extract measurables
            height_elem = prospect_elem.find("div", string=re.compile(r"HEIGHT"))
            height = (
                height_elem.next_sibling.strip()
                if height_elem and height_elem.next_sibling
                else None
            )

            weight_elem = prospect_elem.find("div", string=re.compile(r"WEIGHT"))
            weight_text = (
                weight_elem.next_sibling.strip()
                if weight_elem and weight_elem.next_sibling
                else None
            )
            weight = None
            if weight_text and weight_text != "—":
                try:
                    weight = int(weight_text)
                except ValueError:
                    pass

            age_elem = prospect_elem.find("div", string=re.compile(r"AGE"))
            age_text = (
                age_elem.next_sibling.strip()
                if age_elem and age_elem.next_sibling
                else None
            )
            age = None
            if age_text and age_text != "—":
                try:
                    age = float(age_text)
                except ValueError:
                    pass

            # Extract speed (often not available)
            speed_elem = prospect_elem.find("div", string=re.compile(r"SPEED"))
            speed = (
                speed_elem.next_sibling.strip()
                if speed_elem and speed_elem.next_sibling
                else None
            )
            if speed == "—":
                speed = None

            # Extract PFF grade and ranking
            # Structure: [Year] [Grade] [Position Rank]
            grade = None
            position_rank = None
            
            # Look for the grade in a table or structured format
            grade_elems = prospect_elem.find_all(string=re.compile(r"^\d{4}$"))
            if grade_elems:
                # Get text following the year
                year_elem = grade_elems[0]
                parent = year_elem.parent
                
                # Find grade (should be numeric like "91.6")
                grade_text = parent.find_next(string=re.compile(r"^\d+\.?\d*$"))
                if grade_text:
                    try:
                        grade = float(grade_text.string.strip())
                    except ValueError:
                        pass
                
                # Find position rank (e.g., "9th / 315 QB")
                rank_text = parent.find_next(string=re.compile(r"^\d+(?:st|nd|rd|th).*\d+"))
                if rank_text:
                    position_rank = rank_text.string.strip()

            return {
                "pff_rank": pff_rank,
                "name": name,
                "position": position,
                "class": player_class,
                "school": school,
                "height": height,
                "weight": weight,
                "age": age,
                "speed": speed,
                "pff_grade": grade,
                "position_rank": position_rank,
                "season": self.season,
            }

        except Exception as e:
            print(f"  Error parsing prospect: {e}")
            return None

    def extract_prospects_from_html(self, html: str) -> List[Dict]:
        """
        Extract all prospects from page HTML

        Args:
            html: HTML content

        Returns:
            List of prospect dictionaries
        """
        prospects = []
        try:
            soup = BeautifulSoup(html, "lxml")
            
            # Find all prospect cards - they appear to be organized in sections
            # Each prospect has a card-like structure with their rank, name, position, etc.
            
            # Strategy: Find all elements that contain "PFF Rank" 
            # and extract the prospect card from there
            rank_labels = soup.find_all(string=re.compile(r"PFF Rank"))
            
            for rank_label in rank_labels:
                # The prospect card is the parent or ancestor
                prospect_elem = rank_label.find_parent()
                
                # Keep going up until we find a proper container
                # (usually a div or section with enough data)
                for _ in range(5):
                    if prospect_elem:
                        prospect_data = self.parse_prospect(prospect_elem)
                        if prospect_data:
                            prospects.append(prospect_data)
                            break
                    prospect_elem = prospect_elem.parent if prospect_elem else None

            print(f"  ✓ Extracted {len(prospects)} prospects from page")
            return prospects

        except Exception as e:
            print(f"  ✗ Error extracting prospects: {e}")
            return []

    def scrape_all_pages(self, max_pages: Optional[int] = None) -> List[Dict]:
        """
        Scrape all pages of the PFF Big Board

        Args:
            max_pages: Maximum pages to scrape (for testing)

        Returns:
            List of all prospects across all pages
        """
        print(f"\n{'='*60}")
        print(f"PFF Draft Big Board Scraper - Season {self.season}")
        print(f"{'='*60}\n")

        all_prospects = []
        page = 1
        consecutive_failures = 0
        max_consecutive_failures = 3

        while True:
            if max_pages and page > max_pages:
                print(f"\nReached max pages limit ({max_pages})")
                break

            html = self.fetch_page(page)
            
            if not html:
                consecutive_failures += 1
                if consecutive_failures >= max_consecutive_failures:
                    print(
                        f"\nStopped: {max_consecutive_failures} consecutive failures"
                    )
                    break
                time.sleep(self.delay_between_requests)
                page += 1
                continue

            consecutive_failures = 0
            prospects = self.extract_prospects_from_html(html)
            
            if not prospects:
                print(f"  No prospects found on page {page} - likely end of pages")
                break

            all_prospects.extend(prospects)

            # Respectful rate limiting
            if page < 20:  # Don't sleep after last page
                time.sleep(self.delay_between_requests)

            page += 1

        print(f"\n{'='*60}")
        print(f"Scraping Complete: {len(all_prospects)} total prospects")
        print(f"{'='*60}\n")

        self.prospects = all_prospects
        return all_prospects

    def scrape_first_page(self) -> List[Dict]:
        """
        Scrape only the first page (for quick testing)

        Returns:
            List of prospects from page 1
        """
        print("\n[Quick Test] Scraping first page only...\n")
        html = self.fetch_page(1)
        if html:
            return self.extract_prospects_from_html(html)
        return []

    def export_to_json(self, filename: str) -> None:
        """
        Export scraped data to JSON file

        Args:
            filename: Output JSON filename
        """
        import json
        
        with open(filename, "w") as f:
            json.dump(self.prospects, f, indent=2)
        print(f"✓ Exported {len(self.prospects)} prospects to {filename}")

    def print_sample(self, count: int = 5) -> None:
        """
        Print sample prospects to console

        Args:
            count: Number of samples to print
        """
        print(f"\n{'='*60}")
        print(f"Sample Prospects (first {count})")
        print(f"{'='*60}\n")

        for prospect in self.prospects[:count]:
            print(f"#{prospect['pff_rank']:3d} {prospect['name']:25s} {prospect['position']:4s}")
            print(f"      {prospect['school']:20s} {prospect['class']:7s}")
            if prospect['height']:
                print(f"      Height: {prospect['height']:8s} Weight: {prospect['weight']}")
            if prospect['pff_grade']:
                print(f"      Grade: {prospect['pff_grade']:5.1f}  Rank: {prospect['position_rank']}")
            print()


# ============================================================================
# EXAMPLE USAGE / TESTING
# ============================================================================

if __name__ == "__main__":
    """
    Quick test of the scraper

    To test:
        python -m data_pipeline.scrapers.pff_scraper_poc

    Note:
        First run will be slower (full scrape)
        Add `max_pages=1` for quick first-page test
    """
    
    # Initialize scraper
    scraper = PFFScraperPoC(season=2026, delay_between_requests=1.5)

    # Option 1: Quick test (first page only)
    # prospects = scraper.scrape_first_page()
    
    # Option 2: Full scrape (all pages)
    prospects = scraper.scrape_all_pages(max_pages=2)  # Test with 2 pages

    # Print samples
    if prospects:
        scraper.print_sample(count=10)
        print(f"\n✓ Successfully scraped {len(prospects)} prospects")
        print("\nSample data:")
        for p in prospects[:3]:
            print(f"  - {p['name']} ({p['position']}) from {p['school']}")
    else:
        print("✗ No prospects scraped")
