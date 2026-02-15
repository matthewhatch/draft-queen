"""College Football Reference (CFR) Web Scraper

Fetches 2026 draft class data from College Football Reference website.
Handles all 9 position types with position-specific statistics extraction.
Implements rate limiting, caching, error handling, and retry logic.

Author: Data Engineer
Date: 2026-02-15
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from decimal import Decimal
import re

import aiohttp
from bs4 import BeautifulSoup


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class CFRPlayer:
    """Represents a player from CFR data."""
    name: str
    position: str
    school: str
    stats: Dict[str, Any]
    cfr_url: Optional[str] = None
    scraped_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        if self.scraped_at:
            data['scraped_at'] = self.scraped_at.isoformat()
        return data


class CFRScraper:
    """Web scraper for College Football Reference data."""
    
    # Position-specific stat groups
    POSITION_STAT_GROUPS = {
        "QB": [
            "passing_attempts", "passing_completions", "passing_yards", 
            "passing_touchdowns", "interceptions_thrown", 
            "rushing_attempts", "rushing_yards", "rushing_touchdowns"
        ],
        "RB": [
            "rushing_attempts", "rushing_yards", "rushing_touchdowns",
            "receiving_receptions", "receiving_yards", "receiving_touchdowns",
            "yards_per_reception"
        ],
        "WR": [
            "receiving_receptions", "receiving_yards", "receiving_touchdowns",
            "yards_per_reception", "rushing_attempts", "rushing_yards"
        ],
        "TE": [
            "receiving_receptions", "receiving_yards", "receiving_touchdowns",
            "yards_per_reception"
        ],
        "OL": [
            "games_played", "games_started", "all_conference_selections"
        ],
        "DL": [
            "tackles_solo", "tackles_assisted", "tackles_total",
            "sacks", "tackles_for_loss", "forced_fumbles"
        ],
        "EDGE": [
            "sacks", "tackles_for_loss", "tackles_solo", "tackles_total",
            "forced_fumbles", "passes_defended"
        ],
        "LB": [
            "tackles_solo", "tackles_assisted", "tackles_total",
            "sacks", "tackles_for_loss", "passes_defended",
            "interceptions_defensive", "forced_fumbles"
        ],
        "DB": [
            "passes_defended", "interceptions_defensive", "tackles_total",
            "tackles_solo", "tackles_assisted", "forced_fumbles"
        ],
    }
    
    # Valid positions
    VALID_POSITIONS = set(POSITION_STAT_GROUPS.keys())
    
    def __init__(
        self,
        base_url: str = "https://www.sports-reference.com/cfb/",
        rate_limit_delay: float = 2.5,
        cache_dir: Optional[Path] = None,
        cache_ttl_hours: int = 24,
        timeout: int = 30
    ):
        """Initialize CFR scraper.
        
        Args:
            base_url: Base URL for College Football Reference
            rate_limit_delay: Delay between requests in seconds
            cache_dir: Directory for caching responses
            cache_ttl_hours: Cache time-to-live in hours
            timeout: Request timeout in seconds
        """
        self.base_url = base_url
        self.rate_limit_delay = rate_limit_delay
        self.timeout = timeout
        self.last_request_time = 0.0
        
        # Cache configuration
        self.cache_dir = cache_dir or Path.home() / ".cache" / "cfr_scraper"
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"CFRScraper initialized - Base URL: {self.base_url}")
        logger.info(f"Cache directory: {self.cache_dir}")
    
    def _get_cache_path(self, url: str) -> Path:
        """Get cache file path for URL."""
        # Create hash of URL for filename
        url_hash = hash(url) & 0x7fffffff  # Positive hash
        return self.cache_dir / f"cache_{url_hash}.json"
    
    def _is_cache_valid(self, cache_path: Path) -> bool:
        """Check if cache file is valid (not expired)."""
        if not cache_path.exists():
            return False
        
        file_time = datetime.fromtimestamp(cache_path.stat().st_mtime)
        age = datetime.now() - file_time
        
        return age < self.cache_ttl
    
    def _load_from_cache(self, url: str) -> Optional[str]:
        """Load cached response for URL."""
        cache_path = self._get_cache_path(url)
        
        if self._is_cache_valid(cache_path):
            try:
                with open(cache_path, 'r') as f:
                    data = json.load(f)
                logger.debug(f"Loaded from cache: {url}")
                return data.get('content')
            except Exception as e:
                logger.warning(f"Failed to load cache for {url}: {e}")
        
        return None
    
    def _save_to_cache(self, url: str, content: str) -> None:
        """Save response to cache."""
        cache_path = self._get_cache_path(url)
        
        try:
            data = {
                'url': url,
                'content': content,
                'cached_at': datetime.now().isoformat()
            }
            with open(cache_path, 'w') as f:
                json.dump(data, f)
            logger.debug(f"Cached response for: {url}")
        except Exception as e:
            logger.warning(f"Failed to cache response: {e}")
    
    async def _apply_rate_limit(self) -> None:
        """Apply rate limiting between requests."""
        elapsed = asyncio.get_event_loop().time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = asyncio.get_event_loop().time()
    
    async def _fetch_url(
        self,
        url: str,
        session: aiohttp.ClientSession,
        retries: int = 3
    ) -> Optional[str]:
        """Fetch URL with retry logic and caching.
        
        Args:
            url: URL to fetch
            session: aiohttp session
            retries: Number of retries on failure
            
        Returns:
            Response content or None if failed
        """
        # Check cache first
        cached = self._load_from_cache(url)
        if cached:
            return cached
        
        # Apply rate limiting
        await self._apply_rate_limit()
        
        # Retry loop
        for attempt in range(retries):
            try:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                    headers={'User-Agent': 'Mozilla/5.0 (Data Science Research)'}
                ) as response:
                    if response.status == 200:
                        content = await response.text()
                        self._save_to_cache(url, content)
                        logger.info(f"✓ Fetched: {url}")
                        return content
                    else:
                        logger.warning(f"HTTP {response.status} for {url}")
                        
            except asyncio.TimeoutError:
                logger.warning(f"Timeout on {url} (attempt {attempt + 1}/{retries})")
            except aiohttp.ClientError as e:
                logger.warning(f"Client error fetching {url}: {e} (attempt {attempt + 1}/{retries})")
            except Exception as e:
                logger.error(f"Unexpected error fetching {url}: {e}")
            
            # Exponential backoff before retry
            if attempt < retries - 1:
                delay = 2 ** attempt
                logger.info(f"Retrying in {delay}s...")
                await asyncio.sleep(delay)
        
        logger.error(f"✗ Failed to fetch {url} after {retries} attempts")
        return None
    
    def _parse_stat_value(self, value: str) -> Optional[Decimal]:
        """Parse stat value to Decimal.
        
        Args:
            value: String representation of stat
            
        Returns:
            Decimal value or None if unparseable
        """
        if not value or value.lower() in ('—', 'n/a', 'na'):
            return None
        
        try:
            # Remove commas and convert to Decimal
            cleaned = value.strip().replace(',', '')
            if cleaned.startswith('.'):
                cleaned = '0' + cleaned
            return Decimal(cleaned)
        except Exception as e:
            logger.debug(f"Failed to parse stat value '{value}': {e}")
            return None
    
    def _extract_player_data(self, row: Any, position: str) -> Optional[Dict[str, Any]]:
        """Extract player data from table row.
        
        Args:
            row: BeautifulSoup table row element
            position: Player position
            
        Returns:
            Player data dict or None if extraction fails
        """
        try:
            cells = row.find_all(['th', 'td'])
            
            if len(cells) < 3:
                return None
            
            # Basic info (name, school, etc.)
            player_name = cells[0].get_text(strip=True)
            school = cells[1].get_text(strip=True) if len(cells) > 1 else None
            
            if not player_name or not school:
                return None
            
            # Position-specific stats based on order in table
            stats = {}
            stat_keys = self.POSITION_STAT_GROUPS.get(position, [])
            
            # Stats typically start at column 2
            for idx, stat_key in enumerate(stat_keys):
                cell_idx = 2 + idx
                if cell_idx < len(cells):
                    value = self._parse_stat_value(cells[cell_idx].get_text(strip=True))
                    if value is not None:
                        stats[stat_key] = float(value)
            
            return {
                'name': player_name,
                'school': school,
                'position': position,
                'stats': stats
            }
            
        except Exception as e:
            logger.debug(f"Error extracting player data: {e}")
            return None
    
    async def scrape_2026_draft_class(
        self,
        session: aiohttp.ClientSession,
        positions: Optional[List[str]] = None
    ) -> List[CFRPlayer]:
        """Scrape 2026 draft class from CFR.
        
        Args:
            session: aiohttp session
            positions: Specific positions to scrape (None = all)
            
        Returns:
            List of CFRPlayer objects
        """
        positions = positions or list(self.VALID_POSITIONS)
        positions = [p.upper() for p in positions if p.upper() in self.VALID_POSITIONS]
        
        players: List[CFRPlayer] = []
        
        logger.info(f"Scraping 2026 draft class for positions: {positions}")
        
        for position in positions:
            try:
                # CFR URL pattern for 2026 draft prospects by position
                # Note: This is a typical pattern; adjust based on actual CFR structure
                url = f"{self.base_url}2026/draft/players/{position.lower()}.html"
                
                content = await self._fetch_url(url, session)
                if not content:
                    logger.warning(f"No content for {position}")
                    continue
                
                # Parse HTML
                soup = BeautifulSoup(content, 'html.parser')
                table = soup.find('table', {'class': 'stats_table'})
                
                if not table:
                    logger.warning(f"No stats table found for {position}")
                    continue
                
                # Extract players from table rows
                position_players = 0
                for row in table.find_all('tr')[1:]:  # Skip header
                    player_data = self._extract_player_data(row, position)
                    if player_data:
                        player = CFRPlayer(
                            name=player_data['name'],
                            position=position,
                            school=player_data['school'],
                            stats=player_data['stats'],
                            cfr_url=url,
                            scraped_at=datetime.utcnow()
                        )
                        players.append(player)
                        position_players += 1
                
                logger.info(f"✓ Scraped {position_players} players for {position}")
                
            except Exception as e:
                logger.error(f"Error scraping {position}: {e}")
        
        logger.info(f"✓ Scraping complete: {len(players)} total players")
        return players
    
    async def scrape(
        self,
        positions: Optional[List[str]] = None
    ) -> List[CFRPlayer]:
        """Main scrape method with session management.
        
        Args:
            positions: Specific positions to scrape (None = all)
            
        Returns:
            List of CFRPlayer objects
        """
        async with aiohttp.ClientSession() as session:
            return await self.scrape_2026_draft_class(session, positions)


async def main():
    """Demo script."""
    scraper = CFRScraper()
    
    # Scrape all positions
    players = await scraper.scrape()
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"CFR 2026 Draft Class Scraping Summary")
    print(f"{'='*60}")
    print(f"Total players scraped: {len(players)}")
    
    # Group by position
    by_position = {}
    for player in players:
        if player.position not in by_position:
            by_position[player.position] = []
        by_position[player.position].append(player)
    
    print(f"\nPlayers by position:")
    for pos in sorted(by_position.keys()):
        print(f"  {pos}: {len(by_position[pos])}")
    
    # Sample player
    if players:
        sample = players[0]
        print(f"\nSample player:")
        print(f"  Name: {sample.name}")
        print(f"  Position: {sample.position}")
        print(f"  School: {sample.school}")
        print(f"  Stats: {sample.stats}")


if __name__ == "__main__":
    asyncio.run(main())
