"""ESPN injury data scraper for NFL prospects."""

import requests
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from config import settings
from data_pipeline.validators.prospect_matcher import ProspectMatcher

logger = logging.getLogger(__name__)


class ESPNInjuryConnector:
    """Fetches injury data from ESPN."""

    # ESPN injury reports URL (no trailing slash - with trailing slash returns 404)
    BASE_URL = "https://www.espn.com/nfl/injuries"
    RATE_LIMIT_DELAY = 3.0  # Seconds between requests (more conservative)

    # Injury severity levels
    SEVERITY_LEVELS = {"out": 3, "day_to_day": 2, "questionable": 1, "probable": 1}

    # Common injury types (normalized)
    INJURY_TYPES = {
        "knee": "Knee",
        "ankle": "Ankle",
        "shoulder": "Shoulder",
        "hamstring": "Hamstring",
        "groin": "Groin",
        "back": "Back",
        "foot": "Foot",
        "arm": "Arm",
        "wrist": "Wrist",
        "concussion": "Concussion",
        "turf toe": "Turf Toe",
        "torn": "Torn",
        "sprain": "Sprain",
        "strain": "Strain",
        "fracture": "Fracture",
        "dislocation": "Dislocation",
        "torn acl": "Torn ACL",
        "torn mcl": "Torn MCL",
    }

    def __init__(self):
        """Initialize ESPN injury connector."""
        self.session = self._create_session()
        self.cached_injuries = {}
        self.last_request_time = 0
        self.last_update = None

    def _create_session(self) -> requests.Session:
        """Create requests session with retry strategy."""
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=2,
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

        logger.info("ESPN session created with retry strategy")
        return session

    def _apply_rate_limit(self):
        """Respect rate limiting - 3s delays between requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.RATE_LIMIT_DELAY:
            sleep_time = self.RATE_LIMIT_DELAY - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.1f}s")
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    def _fetch_url(self, url: str) -> Optional[str]:
        """
        Fetch URL content with rate limiting.

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

    def _normalize_injury_type(self, injury_str: str) -> str:
        """
        Normalize injury type string to standard format.

        Args:
            injury_str: Raw injury string from ESPN

        Returns:
            Normalized injury type
        """
        injury_lower = injury_str.lower().strip()

        # Check for multi-word injuries first (longest matches first)
        multi_word_injuries = ["torn acl", "torn mcl", "turf toe"]
        for injury in multi_word_injuries:
            if injury in injury_lower:
                return injury.title()

        # Then check single keywords
        for key, normalized in self.INJURY_TYPES.items():
            if key in injury_lower:
                return normalized

        # If no match, return capitalized original
        return injury_str.strip().title()

    def _extract_severity(self, status_str: str) -> Tuple[str, int]:
        """
        Extract injury severity from status string.

        Args:
            status_str: Status string from ESPN

        Returns:
            Tuple of (severity_label, severity_score)
        """
        status_lower = status_str.lower().strip()

        # Check for severity keywords
        if "out" in status_lower:
            return "Out", self.SEVERITY_LEVELS.get("out", 3)
        elif "day" in status_lower and "day" in status_lower:
            return "Day-to-Day", self.SEVERITY_LEVELS.get("day_to_day", 2)
        elif "questionable" in status_lower:
            return "Questionable", self.SEVERITY_LEVELS.get("questionable", 1)
        elif "probable" in status_lower:
            return "Probable", self.SEVERITY_LEVELS.get("probable", 1)
        else:
            return status_str.title(), 1

    def _parse_return_date(self, return_str: Optional[str]) -> Optional[datetime]:
        """
        Parse expected return date from string.

        Args:
            return_str: Return date string from ESPN

        Returns:
            Parsed datetime or None
        """
        if not return_str:
            return None

        try:
            # Try common date formats
            for fmt in ["%B %d, %Y", "%m/%d/%Y", "%Y-%m-%d", "%b %d"]:
                try:
                    return datetime.strptime(return_str.strip(), fmt)
                except ValueError:
                    continue

            logger.debug(f"Could not parse return date: {return_str}")
            return None

        except Exception as e:
            logger.warning(f"Error parsing return date '{return_str}': {e}")
            return None

    def _parse_injury_row(self, row_html: str) -> Optional[Dict[str, Any]]:
        """
        Parse individual injury row from HTML.

        Args:
            row_html: HTML snippet containing injury info

        Returns:
            Dictionary with injury data or None if parsing fails
        """
        try:
            soup = BeautifulSoup(row_html, "html.parser")

            # Extract player name
            name_elem = soup.find("td", class_="player-name")
            if not name_elem:
                return None

            player_name = name_elem.text.strip()

            # Extract position
            pos_elem = soup.find("td", class_="player-position")
            position = pos_elem.text.strip() if pos_elem else None

            # Extract team
            team_elem = soup.find("td", class_="player-team")
            team = team_elem.text.strip() if team_elem else None

            # Extract injury type
            injury_elem = soup.find("td", class_="injury-type")
            injury_type = (
                self._normalize_injury_type(injury_elem.text)
                if injury_elem
                else "Unknown"
            )

            # Extract status
            status_elem = soup.find("td", class_="injury-status")
            if status_elem:
                status_str = status_elem.text.strip()
                severity_label, severity_score = self._extract_severity(status_str)
            else:
                severity_label, severity_score = "Unknown", 0

            # Extract expected return date
            return_elem = soup.find("td", class_="return-date")
            return_date = (
                self._parse_return_date(return_elem.text) if return_elem else None
            )

            injury_data = {
                "player_name": player_name,
                "position": position,
                "team": team,
                "injury_type": injury_type,
                "severity_label": severity_label,
                "severity_score": severity_score,
                "expected_return_date": return_date,
                "reported_date": datetime.now(),
            }

            logger.debug(f"Parsed injury for {player_name}: {injury_type} ({severity_label})")
            return injury_data

        except Exception as e:
            logger.error(f"Failed to parse injury row: {e}")
            return None

    def fetch_injuries(self) -> List[Dict[str, Any]]:
        """
        Fetch current injury reports from ESPN.

        Returns:
            List of injury data dictionaries
        """
        logger.info("Starting ESPN injury data fetch")
        injuries = []

        try:
            # Fetch injuries page
            html_content = self._fetch_url(self.BASE_URL)
            if not html_content:
                logger.warning("Failed to fetch ESPN injuries page")
                return self.cached_injuries.get("injuries", [])

            # Parse injury table
            soup = BeautifulSoup(html_content, "html.parser")
            injury_rows = soup.find_all("tr", class_="injury-row")

            logger.info(f"Found {len(injury_rows)} injury records")

            for row in injury_rows:
                injury = self._parse_injury_row(str(row))
                if injury:
                    injuries.append(injury)

            # Cache results
            self.cached_injuries["injuries"] = injuries
            self.last_update = datetime.now()

            logger.info(
                f"Successfully fetched {len(injuries)} injury records from ESPN"
            )
            return injuries

        except Exception as e:
            logger.error(f"Failed to fetch injuries from ESPN: {e}")
            # Return cached data if available
            return self.cached_injuries.get("injuries", [])

    def fetch_injuries_by_position(self, position: str) -> List[Dict[str, Any]]:
        """
        Fetch injuries filtered by position.

        Args:
            position: Position to filter by (QB, RB, WR, etc.)

        Returns:
            List of injuries for position
        """
        logger.info(f"Fetching ESPN injuries for position: {position}")
        all_injuries = self.fetch_injuries()

        filtered = [
            i for i in all_injuries if i.get("position") == position.upper()
        ]
        logger.info(f"Found {len(filtered)} injured {position} prospects")

        return filtered

    def fetch_injuries_by_team(self, team: str) -> List[Dict[str, Any]]:
        """
        Fetch injuries filtered by team.

        Args:
            team: Team abbreviation to filter by

        Returns:
            List of injuries for team
        """
        logger.info(f"Fetching ESPN injuries for team: {team}")
        all_injuries = self.fetch_injuries()

        filtered = [i for i in all_injuries if i.get("team") == team.upper()]
        logger.info(f"Found {len(filtered)} injured {team} players")

        return filtered

    def fetch_critical_injuries(
        self, severity_threshold: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Fetch only critical/major injuries.

        Args:
            severity_threshold: Minimum severity score (1-3)

        Returns:
            List of critical injuries
        """
        logger.info(f"Fetching critical injuries (severity >= {severity_threshold})")
        all_injuries = self.fetch_injuries()

        critical = [
            i
            for i in all_injuries
            if i.get("severity_score", 0) >= severity_threshold
        ]
        logger.info(f"Found {len(critical)} critical injuries")

        return critical

    def link_to_prospect(
        self, injury: Dict[str, Any], existing_prospects: List[Dict]
    ) -> Optional[Dict[str, Any]]:
        """
        Link injury to prospect record using fuzzy matching.

        Args:
            injury: Injury dictionary with player_name
            existing_prospects: List of existing prospect records

        Returns:
            Match result with prospect_id or None if no match
        """
        match = ProspectMatcher.find_best_match(
            injury.get("player_name", ""), existing_prospects, threshold=80
        )

        if match:
            injury["prospect_id"] = match.prospect_id
            injury["prospect_name"] = match.prospect_name
            injury["match_confidence"] = match.confidence
            logger.debug(
                f"Linked injury for '{injury['player_name']}' to prospect "
                f"'{match.prospect_name}' ({match.confidence} confidence)"
            )
            return injury
        else:
            logger.warning(
                f"Could not link injury for '{injury.get('player_name')}' to any prospect"
            )
            return None

    def health_check(self) -> bool:
        """
        Check ESPN accessibility.

        Returns:
            True if ESPN is reachable, False otherwise
        """
        try:
            response = self.session.head(self.BASE_URL, timeout=10)

            if response.status_code == 200:
                logger.info("ESPN health check passed")
                return True
            else:
                logger.warning(f"ESPN returned status {response.status_code}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"ESPN health check failed: {e}")
            return False

    def get_update_age(self) -> Optional[timedelta]:
        """
        Get age of last update.

        Returns:
            Timedelta since last update or None if never updated
        """
        if self.last_update is None:
            return None

        return datetime.now() - self.last_update

    def close(self):
        """Close the session."""
        self.session.close()
        logger.info("ESPN connector session closed")


class MockESPNInjuryConnector(ESPNInjuryConnector):
    """Mock ESPN connector for testing."""

    def fetch_injuries(self) -> List[Dict[str, Any]]:
        """Return mock injury data for testing."""
        return [
            {
                "player_name": "Test QB",
                "position": "QB",
                "team": "NE",
                "injury_type": "Shoulder",
                "severity_label": "Day-to-Day",
                "severity_score": 2,
                "expected_return_date": datetime.now() + timedelta(days=7),
                "reported_date": datetime.now(),
            },
            {
                "player_name": "Test WR",
                "position": "WR",
                "team": "KC",
                "injury_type": "Hamstring",
                "severity_label": "Out",
                "severity_score": 3,
                "expected_return_date": datetime.now() + timedelta(days=21),
                "reported_date": datetime.now(),
            },
            {
                "player_name": "Test RB",
                "position": "RB",
                "team": "SF",
                "injury_type": "Knee",
                "severity_label": "Questionable",
                "severity_score": 1,
                "expected_return_date": datetime.now() + timedelta(days=3),
                "reported_date": datetime.now(),
            },
        ]

    def health_check(self) -> bool:
        """Mock health check always returns True."""
        logger.info("Mock ESPN health check passed")
        return True
