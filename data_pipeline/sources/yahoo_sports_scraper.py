"""Yahoo Sports prospect data scraper."""

import requests
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from config import settings
from rapidfuzz import fuzz
import re

logger = logging.getLogger(__name__)


class YahooSportsConnector:
    """Fetches prospect data from Yahoo Sports."""

    # Yahoo Sports prospect list URL
    BASE_URL = "https://sports.yahoo.com/nfl/draft/"
    RATE_LIMIT_DELAY = 2.5  # Seconds between requests

    def __init__(self):
        """Initialize Yahoo Sports connector."""
        self.session = self._create_session()
        self.cached_prospects = {}
        self.last_request_time = 0

    def _create_session(self) -> requests.Session:
        """Create requests session with retry strategy."""
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=2,  # Exponential backoff: 1s, 2s, 4s
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set headers to mimic real browser
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "DNT": "1",
            }
        )

        logger.info("Yahoo Sports session created with retry strategy")
        return session

    def _apply_rate_limit(self):
        """Respect rate limiting - 2-3s delays between requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.RATE_LIMIT_DELAY:
            sleep_time = self.RATE_LIMIT_DELAY - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.1f}s")
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    def _fetch_url(self, url: str) -> Optional[str]:
        """
        Fetch URL content with rate limiting and error handling.

        Args:
            url: URL to fetch

        Returns:
            HTML content or None if fetch fails
        """
        try:
            self._apply_rate_limit()
            logger.debug(f"Fetching: {url}")

            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            logger.debug(f"Successfully fetched {url} (status: {response.status_code})")
            return response.text

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None

    def _parse_player_stats(self, player_html: str) -> Dict[str, Any]:
        """
        Parse individual player stats from HTML.

        Args:
            player_html: HTML snippet containing player stats

        Returns:
            Dictionary with player stats
        """
        soup = BeautifulSoup(player_html, "html.parser")
        stats = {}

        try:
            # Extract player name
            name_elem = soup.find("h3", class_="player-name")
            stats["name"] = name_elem.text.strip() if name_elem else None

            # Extract position
            pos_elem = soup.find("span", class_="player-position")
            stats["position"] = pos_elem.text.strip() if pos_elem else None

            # Extract college
            college_elem = soup.find("span", class_="player-college")
            stats["college"] = college_elem.text.strip() if college_elem else None

            # Extract college stats
            stats_container = soup.find("div", class_="college-stats")
            if stats_container:
                stat_rows = stats_container.find_all("tr")
                college_stats_by_year = []

                for row in stat_rows:
                    cols = row.find_all("td")
                    if len(cols) >= 4:
                        year_stat = {
                            "year": cols[0].text.strip(),
                            "receptions": self._parse_int(cols[1].text),
                            "rushes": self._parse_int(cols[2].text),
                            "pass_attempts": self._parse_int(cols[3].text),
                        }
                        college_stats_by_year.append(year_stat)

                stats["college_stats_by_year"] = college_stats_by_year

            # Extract production metrics
            production_elem = soup.find("div", class_="production-metrics")
            if production_elem:
                stats["production_metrics"] = {
                    "total_receptions": self._parse_int(
                        production_elem.find("span", class_="total-receptions").text
                    ),
                    "total_rushes": self._parse_int(
                        production_elem.find("span", class_="total-rushes").text
                    ),
                    "total_pass_attempts": self._parse_int(
                        production_elem.find("span", class_="total-passes").text
                    ),
                }

            # Extract performance ranking if available
            ranking_elem = soup.find("span", class_="performance-ranking")
            if ranking_elem:
                stats["performance_ranking"] = self._parse_float(ranking_elem.text)

            logger.debug(f"Parsed stats for {stats.get('name', 'unknown')}")
            return stats

        except Exception as e:
            logger.error(f"Failed to parse player stats: {e}")
            return {}

    def _parse_int(self, value: str) -> Optional[int]:
        """Safely parse integer from string."""
        try:
            return int(re.sub(r"[^0-9]", "", value))
        except (ValueError, AttributeError):
            return None

    def _parse_float(self, value: str) -> Optional[float]:
        """Safely parse float from string."""
        try:
            return float(re.sub(r"[^0-9.]", "", value))
        except (ValueError, AttributeError):
            return None

    def _validate_stats(self, stats: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate stats are within realistic ranges.

        Args:
            stats: Stats dictionary to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Validate name exists
        if not stats.get("name"):
            errors.append("Missing player name")

        # Validate position if present
        valid_positions = {
            "QB",
            "RB",
            "WR",
            "TE",
            "OT",
            "OG",
            "C",
            "EDGE",
            "DT",
            "LB",
            "CB",
            "S",
            "K",
            "P",
        }
        if stats.get("position") and stats["position"] not in valid_positions:
            errors.append(f"Invalid position: {stats['position']}")

        # Validate college stats if present
        if "college_stats_by_year" in stats:
            for year_stat in stats["college_stats_by_year"]:
                receptions = year_stat.get("receptions")
                rushes = year_stat.get("rushes")
                passes = year_stat.get("pass_attempts")

                # Reasonable limits for college football
                if receptions and (receptions < 0 or receptions > 200):
                    errors.append(
                        f"Suspicious receptions count: {receptions} in {year_stat.get('year')}"
                    )
                if rushes and (rushes < 0 or rushes > 400):
                    errors.append(
                        f"Suspicious rushes count: {rushes} in {year_stat.get('year')}"
                    )
                if passes and (passes < 0 or passes > 800):
                    errors.append(
                        f"Suspicious pass attempts: {passes} in {year_stat.get('year')}"
                    )

        return len(errors) == 0, errors

    def fetch_prospects(self) -> List[Dict[str, Any]]:
        """
        Fetch prospect data from Yahoo Sports.

        Returns:
            List of prospect data dictionaries with college stats
        """
        logger.info("Starting Yahoo Sports prospect data fetch")
        prospects = []

        try:
            # Fetch main prospects page
            html_content = self._fetch_url(self.BASE_URL)
            if not html_content:
                logger.warning("Failed to fetch Yahoo Sports prospects page")
                return self.cached_prospects.get("prospects", [])

            # Parse player list
            soup = BeautifulSoup(html_content, "html.parser")
            player_elements = soup.find_all("div", class_="player-card")

            logger.info(f"Found {len(player_elements)} player cards")

            for player_elem in player_elements:
                stats = self._parse_player_stats(str(player_elem))

                # Validate stats
                is_valid, errors = self._validate_stats(stats)

                if is_valid:
                    prospects.append(stats)
                    logger.debug(f"Added prospect: {stats.get('name')}")
                else:
                    logger.warning(f"Validation errors for {stats.get('name')}: {errors}")

            # Cache results
            self.cached_prospects["prospects"] = prospects
            logger.info(
                f"Successfully fetched {len(prospects)} validated prospects from Yahoo Sports"
            )
            return prospects

        except Exception as e:
            logger.error(f"Failed to fetch prospects from Yahoo Sports: {e}")
            # Return cached data if available
            return self.cached_prospects.get("prospects", [])

    def fetch_by_position(self, position: str) -> List[Dict[str, Any]]:
        """
        Fetch prospects filtered by position.

        Args:
            position: Position to filter by (QB, RB, WR, etc.)

        Returns:
            List of prospects matching position
        """
        logger.info(f"Fetching Yahoo Sports prospects for position: {position}")
        all_prospects = self.fetch_prospects()

        filtered = [
            p for p in all_prospects if p.get("position") == position.upper()
        ]
        logger.info(f"Found {len(filtered)} {position} prospects")

        return filtered

    def fetch_by_college(self, college: str) -> List[Dict[str, Any]]:
        """
        Fetch prospects filtered by college.

        Args:
            college: College name to filter by

        Returns:
            List of prospects from college
        """
        logger.info(f"Fetching Yahoo Sports prospects from college: {college}")
        all_prospects = self.fetch_prospects()

        filtered = [
            p
            for p in all_prospects
            if p.get("college", "").lower() == college.lower()
        ]
        logger.info(f"Found {len(filtered)} prospects from {college}")

        return filtered

    def health_check(self) -> bool:
        """
        Check Yahoo Sports accessibility.

        Returns:
            True if Yahoo Sports is reachable, False otherwise
        """
        try:
            response = self.session.head(self.BASE_URL, timeout=10)

            if response.status_code == 200:
                logger.info("Yahoo Sports health check passed")
                return True
            else:
                logger.warning(
                    f"Yahoo Sports returned status {response.status_code}"
                )
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Yahoo Sports health check failed: {e}")
            return False

    def close(self):
        """Close the session."""
        self.session.close()
        logger.info("Yahoo Sports connector session closed")


class MockYahooSportsConnector(YahooSportsConnector):
    """Mock Yahoo Sports connector for testing."""

    def fetch_prospects(self) -> List[Dict[str, Any]]:
        """Return mock prospect data for testing."""
        return [
            {
                "name": "Test QB",
                "position": "QB",
                "college": "Ohio State",
                "college_stats_by_year": [
                    {"year": "2025", "receptions": 0, "rushes": 45, "pass_attempts": 425},
                    {"year": "2024", "receptions": 0, "rushes": 52, "pass_attempts": 523},
                ],
                "production_metrics": {
                    "total_receptions": 0,
                    "total_rushes": 97,
                    "total_pass_attempts": 948,
                },
                "performance_ranking": 8.2,
            },
            {
                "name": "Test WR",
                "position": "WR",
                "college": "Alabama",
                "college_stats_by_year": [
                    {
                        "year": "2025",
                        "receptions": 85,
                        "rushes": 8,
                        "pass_attempts": 0,
                    },
                    {
                        "year": "2024",
                        "receptions": 102,
                        "rushes": 5,
                        "pass_attempts": 0,
                    },
                ],
                "production_metrics": {
                    "total_receptions": 187,
                    "total_rushes": 13,
                    "total_pass_attempts": 0,
                },
                "performance_ranking": 7.8,
            },
        ]

    def health_check(self) -> bool:
        """Mock health check always returns True."""
        logger.info("Mock Yahoo Sports health check passed")
        return True
