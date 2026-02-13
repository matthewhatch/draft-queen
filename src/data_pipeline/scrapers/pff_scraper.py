"""
PFF.com Draft Big Board Production Scraper

Production-ready implementation with:
- Comprehensive error handling and recovery
- Structured logging (timestamps, counts, errors)
- Cache fallback mechanism
- Rate limiting (3-5s delays)
- Async/await for performance
- Data validation framework
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from bs4 import BeautifulSoup

# Configure logging
logger = logging.getLogger(__name__)


class PFFScraperConfig:
    """Configuration for PFF scraper"""

    BASE_URL = "https://www.pff.com/draft/big-board"
    CACHE_DIR = Path(__file__).parent.parent.parent / "data" / "cache" / "pff"
    DEFAULT_SEASON = 2026
    RATE_LIMIT_DELAY = 4.0  # seconds between requests
    REQUEST_TIMEOUT = 15000  # milliseconds
    MAX_RETRIES = 2
    HEADLESS = True


class PFFProspectValidator:
    """Validates PFF prospect data"""

    VALID_POSITIONS = {
        "QB", "RB", "FB", "WR", "TE", "LT", "LG", "C", "RG", "RT",
        "DT", "DE", "EDGE", "LB", "CB", "S", "SS", "FS", "K", "P"
    }

    @staticmethod
    def validate_grade(grade: Optional[str]) -> bool:
        """Validate prospect grade (0-100 scale)"""
        if not grade:
            return True  # Missing grades acceptable
        try:
            grade_val = float(grade)
            return 0 <= grade_val <= 100
        except (ValueError, TypeError):
            return False

    @staticmethod
    def validate_position(position: Optional[str]) -> bool:
        """Validate prospect position code"""
        if not position:
            return True  # Missing position acceptable
        return position.upper() in PFFProspectValidator.VALID_POSITIONS

    @staticmethod
    def validate_prospect(prospect: Dict) -> bool:
        """Validate complete prospect record"""
        if not prospect.get("name"):
            return False

        if prospect.get("grade") and not PFFProspectValidator.validate_grade(prospect["grade"]):
            return False

        if prospect.get("position") and not PFFProspectValidator.validate_position(prospect["position"]):
            return False

        return True


class PFFScraper:
    """Production PFF.com Draft Big Board scraper"""

    def __init__(
        self,
        season: int = PFFScraperConfig.DEFAULT_SEASON,
        headless: bool = PFFScraperConfig.HEADLESS,
        cache_enabled: bool = True,
    ):
        """Initialize scraper with configuration"""
        self.season = season
        self.headless = headless
        self.cache_enabled = cache_enabled
        self.prospects = []
        self.cache_dir = PFFScraperConfig.CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Configure logging
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Configure logging with timestamps and structured output"""
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - PFF_SCRAPER - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)

    def _get_cache_path(self, page_num: int) -> Path:
        """Get cache file path for page"""
        return self.cache_dir / f"season_{self.season}_page_{page_num}.json"

    def _load_cache(self, page_num: int) -> Optional[List[Dict]]:
        """Load prospects from cache"""
        if not self.cache_enabled:
            return None

        cache_path = self._get_cache_path(page_num)
        if not cache_path.exists():
            return None

        try:
            with open(cache_path, "r") as f:
                data = json.load(f)
                age_seconds = time.time() - data.get("timestamp", 0)
                age_hours = age_seconds / 3600

                if age_hours > 24:  # Cache valid for 24 hours
                    logger.info(f"Cache for page {page_num} is stale ({age_hours:.1f}h old)")
                    return None

                logger.info(f"Loaded {len(data.get('prospects', []))} prospects from cache (page {page_num})")
                return data.get("prospects", [])
        except Exception as e:
            logger.warning(f"Error loading cache: {e}")
            return None

    def _save_cache(self, page_num: int, prospects: List[Dict]) -> None:
        """Save prospects to cache"""
        if not self.cache_enabled:
            return

        try:
            cache_path = self._get_cache_path(page_num)
            cache_data = {
                "timestamp": time.time(),
                "season": self.season,
                "page": page_num,
                "prospects": prospects,
                "count": len(prospects),
            }

            with open(cache_path, "w") as f:
                json.dump(cache_data, f, indent=2)

            logger.info(f"Cached {len(prospects)} prospects for page {page_num}")
        except Exception as e:
            logger.error(f"Error saving cache: {e}")

    def parse_prospect(self, prospect_div) -> Optional[Dict]:
        """
        Parse prospect from HTML div using actual PFF DOM structure
        
        Expected structure:
          div.g-card.g-card--border-gray
            div.m-ranking-header
              div.m-ranking-header__main-details
                h3.m-ranking-header__title → a (player name)
              div.m-ranking-header__details
                div.m-stat:nth-child(1) → div.g-data (position)
                div.m-stat:nth-child(2) → div.g-data (class)
            div.g-card__content
              div.m-stat-cluster
                div (×N)
                  div.g-label (field name)
                  div.g-data (field value)
              table.g-table
                tbody → tr:first
                  td[data-cell-label="Season Grade"] → div.kyber-grade-badge__info-text
        """
        try:
            # Extract name from header
            header = prospect_div.find("div", class_="m-ranking-header")
            if not header:
                logger.debug("Ranking header not found in prospect div")
                return None

            # Name is in h3.m-ranking-header__title → a tag
            title_elem = header.find("h3", class_="m-ranking-header__title")
            if not title_elem:
                logger.debug("Title element not found in header")
                return None
                
            name_link = title_elem.find("a")
            name = name_link.get_text(strip=True) if name_link else None
            if not name:
                logger.debug("No name text found")
                return None

            # Extract position and class from header details
            details = header.find("div", class_="m-ranking-header__details")
            position = None
            class_str = None
            
            if details:
                stats = details.find_all("div", class_="m-stat")
                if len(stats) >= 1:
                    pos_data = stats[0].find("div", class_="g-data")
                    position = pos_data.get_text(strip=True) if pos_data else None
                    if position == "—":  # Normalize em-dash to None
                        position = None
                if len(stats) >= 2:
                    class_data = stats[1].find("div", class_="g-data")
                    class_str = class_data.get_text(strip=True) if class_data else None
                    if class_str == "—":  # Normalize em-dash to None
                        class_str = None

            # Extract school, height, weight from stat cluster
            school = None
            height = None
            weight = None
            
            stat_cluster = prospect_div.find("div", class_="m-stat-cluster")
            if stat_cluster:
                # Iterate through stat divs
                stat_divs = stat_cluster.find_all("div", recursive=False)
                for stat_div in stat_divs:
                    label_elem = stat_div.find("div", class_="g-label")
                    data_elem = stat_div.find("div", class_="g-data")
                    if not (label_elem and data_elem):
                        continue
                    
                    label_text = label_elem.get_text(strip=True).lower()
                    value_text = data_elem.get_text(strip=True)
                    
                    if label_text == "school":
                        # Extract span text from g-data (removes SVG icon)
                        span = data_elem.find("span")
                        school = span.get_text(strip=True) if span else value_text
                        if school == "—":  # Normalize em-dash to None
                            school = None
                    elif label_text == "height":
                        height = value_text if value_text != "—" else None
                    elif label_text == "weight":
                        weight = value_text if value_text != "—" else None

            # Extract grade from table
            grade = None
            table = prospect_div.find("table", class_="g-table")
            if table:
                tbody = table.find("tbody")
                if tbody:
                    first_row = tbody.find("tr")
                    if first_row:
                        # Grade is in td[data-cell-label="Season Grade"]
                        grade_cell = first_row.find("td", attrs={"data-cell-label": "Season Grade"})
                        if grade_cell:
                            grade_badge = grade_cell.find("div", class_="kyber-grade-badge__info-text")
                            grade = grade_badge.get_text(strip=True) if grade_badge else None

            prospect = {
                "name": name,
                "position": position,
                "school": school,
                "class": class_str,
                "height": height,
                "weight": weight,
                "grade": grade,
                "scraped_at": datetime.utcnow().isoformat(),
            }

            # Validate before returning
            if not PFFProspectValidator.validate_prospect(prospect):
                logger.debug(f"Invalid prospect: {prospect}")
                return None

            return prospect

        except Exception as e:
            logger.debug(f"Error parsing prospect: {e}")
            return None

    async def scrape_page(self, page_num: int, retry_count: int = 0) -> List[Dict]:
        """
        Scrape single page of PFF Big Board prospects
        
        PFF uses pagination buttons (arrow icons) to navigate between pages.
        We navigate to the desired page by clicking the next button repeatedly.
        """
        # Try cache first
        cached = self._load_cache(page_num)
        if cached:
            return cached

        try:
            from playwright.async_api import async_playwright

            logger.info(f"Scraping page {page_num}...")

            async with async_playwright() as playwright:
                try:
                    browser = await playwright.chromium.launch(
                        headless=self.headless,
                        args=["--disable-dev-shm-usage"],
                    )
                except Exception as e:
                    logger.error(f"Browser launch failed: {e}")
                    raise
                logger.info(f"Browser launched successfully")
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                )

                try:
                    page = await context.new_page()
                    url = f"{PFFScraperConfig.BASE_URL}?season={self.season}"

                    logger.info(f"Loading {url}")
                    await page.goto(url, wait_until="load", timeout=PFFScraperConfig.REQUEST_TIMEOUT)
                    logger.info(f"Page loaded successfully")
                    
                    # Wait for prospect cards to be rendered
                    try:
                        logger.info(f"Waiting for selector: div.g-card (timeout: 5000ms)")
                        await page.wait_for_selector("div.g-card", timeout=5000)
                        logger.info(f"Prospect cards rendered")
                    except Exception as e:
                        logger.warning(f"Prospect selector not found after wait: {e}")
                    
                    # Navigate to desired page by clicking next button
                    if page_num > 1:
                        logger.info(f"Navigating to page {page_num}...")
                        for current_page in range(1, page_num):
                            # Find and click the next button
                            # The buttons have class "g-btn kyber-button" and contain SVG icons
                            try:
                                # Get all pagination buttons
                                next_buttons = await page.query_selector_all("button.g-btn")
                                
                                # The next button should be one of the last buttons (after first, prev buttons)
                                # Try to find one that's not disabled
                                clicked = False
                                for btn in next_buttons[-3:]:  # Check last 3 buttons (next should be second to last)
                                    is_disabled = await btn.get_attribute("disabled")
                                    if not is_disabled:
                                        await btn.click()
                                        clicked = True
                                        logger.info(f"Clicked next button (page {current_page} -> {current_page + 1})")
                                        break
                                
                                if not clicked:
                                    logger.warning(f"Could not find enabled next button")
                                    break
                                
                                # Wait for page to update
                                await asyncio.sleep(2.0)
                                await page.wait_for_selector("div.g-card", timeout=5000)
                                
                            except Exception as e:
                                logger.warning(f"Error navigating to page {current_page + 1}: {e}")
                                break
                    
                    # Wait for prospects to stabilize
                    await asyncio.sleep(1.0)

                    html = await page.content()
                    logger.info(f"Page {page_num} HTML retrieved: {len(html)} bytes")
                    
                    # Parse prospects
                    soup = BeautifulSoup(html, "html.parser")
                    prospects = []

                    # Get prospect cards
                    prospect_divs = soup.find_all("div", class_="g-card")
                    logger.info(f"Found {len(prospect_divs)} prospect divs in parsed HTML")
                    
                    for div in prospect_divs:
                        prospect = self.parse_prospect(div)
                        if prospect:
                            prospects.append(prospect)

                    logger.info(f"Extracted {len(prospects)} prospects from page {page_num}")

                    # Only cache if we found prospects
                    if prospects:
                        self._save_cache(page_num, prospects)
                    else:
                        logger.warning(f"Page {page_num} returned 0 prospects - not caching empty result")

                    await page.close()

                    return prospects

                finally:
                    await context.close()
                    await browser.close()

        except TimeoutError as e:
            logger.error(f"🔴 TIMEOUT on page {page_num}: {e}")
            logger.error(f"The page took longer than {PFFScraperConfig.REQUEST_TIMEOUT}ms to load")

            # Fallback to cache even if stale
            cache_path = self._get_cache_path(page_num)
            if cache_path.exists():
                logger.info(f"Using stale cache for page {page_num}")
                try:
                    with open(cache_path, "r") as f:
                        return json.load(f).get("prospects", [])
                except Exception as cache_e:
                    logger.error(f"Stale cache also failed: {cache_e}")

            # Retry if not exhausted
            if retry_count < PFFScraperConfig.MAX_RETRIES:
                logger.info(f"Retrying page {page_num} (attempt {retry_count + 1})")
                await asyncio.sleep(5.0)  # Wait before retry
                return await self.scrape_page(page_num, retry_count + 1)

            return []

        except Exception as e:
            logger.error(f"❌ Error scraping page {page_num}: {type(e).__name__}: {e}")

            # Fallback to cache
            cache_path = self._get_cache_path(page_num)
            if cache_path.exists():
                logger.info(f"Using cache after error for page {page_num}")
                try:
                    with open(cache_path, "r") as f:
                        return json.load(f).get("prospects", [])
                except Exception:
                    pass

            return []

    async def scrape_all_pages(self, max_pages: int = 10) -> List[Dict]:
        """
        Scrape all pages of prospects with rate limiting
        
        Args:
            max_pages: Maximum number of pages to scrape
            
        Returns:
            List of all prospect dictionaries
        """
        logger.info(f"Starting scrape: season={self.season}, max_pages={max_pages}")
        start_time = time.time()

        self.prospects = []

        for page_num in range(1, max_pages + 1):
            # Rate limiting
            if page_num > 1:
                await asyncio.sleep(PFFScraperConfig.RATE_LIMIT_DELAY)

            prospects = await self.scrape_page(page_num)

            if not prospects:
                logger.info(f"No more prospects found, stopping at page {page_num - 1}")
                break

            self.prospects.extend(prospects)

        elapsed = time.time() - start_time
        logger.info(f"Scrape complete: {len(self.prospects)} total prospects in {elapsed:.1f}s")

        return self.prospects

    def get_summary(self) -> Dict:
        """Get scrape summary statistics"""
        if not self.prospects:
            return {
                "total_prospects": 0,
                "by_position": {},
                "by_school": {},
                "scraped_at": datetime.utcnow().isoformat(),
            }

        by_position = {}
        by_school = {}

        for prospect in self.prospects:
            pos = prospect.get("position", "UNKNOWN")
            school = prospect.get("school", "UNKNOWN")

            by_position[pos] = by_position.get(pos, 0) + 1
            by_school[school] = by_school.get(school, 0) + 1

        return {
            "total_prospects": len(self.prospects),
            "by_position": by_position,
            "by_school": by_school,
            "scraped_at": datetime.utcnow().isoformat(),
        }

    def print_summary(self) -> None:
        """Print scrape summary"""
        summary = self.get_summary()

        print(f"\n{'='*60}")
        print(f"PFF Scraper Summary - Season {self.season}")
        print(f"{'='*60}\n")

        print(f"Total Prospects: {summary['total_prospects']}\n")

        if summary["by_position"]:
            print("By Position:")
            for pos in sorted(summary["by_position"].keys()):
                count = summary["by_position"][pos]
                print(f"  {pos:5s}: {count:3d}")
            print()

        if summary["by_school"]:
            print("Top Schools:")
            sorted_schools = sorted(
                summary["by_school"].items(), key=lambda x: x[1], reverse=True
            )
            for school, count in sorted_schools[:10]:
                print(f"  {school:30s}: {count:2d}")

        print(f"\nScraped at: {summary['scraped_at']}")
        print(f"{'='*60}\n")
