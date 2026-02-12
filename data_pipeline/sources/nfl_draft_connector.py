"""NFL Draft data scraper using public APIs."""

import requests
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class NFLDraftConnector:
    """Fetches prospect data from NFL Draft data APIs."""
    
    # Using NFL Draft Wire mock data for now
    # In production, would use real APIs
    
    MOCK_PROSPECTS = [
        {"name": "Saquon Barkley II", "position": "RB", "college": "Penn State", "height": 5.95, "weight": 216, "draft_grade": 9.2},
        {"name": "Travis Hunter", "position": "WR", "college": "Colorado", "height": 6.10, "weight": 210, "draft_grade": 9.1},
        {"name": "Cam Ward", "position": "QB", "college": "Miami", "height": 6.20, "weight": 215, "draft_grade": 8.9},
        {"name": "Malachi Nelson", "position": "QB", "college": "Oklahoma", "height": 6.15, "weight": 210, "draft_grade": 8.5},
        {"name": "Jorrick Jones", "position": "DL", "college": "Texas A&M", "height": 6.35, "weight": 295, "draft_grade": 8.7},
        {"name": "Latu Carter", "position": "LB", "college": "Penn State", "height": 6.20, "weight": 245, "draft_grade": 8.6},
        {"name": "Ezekiel Noa-Gonser", "position": "DL", "college": "Oklahoma State", "height": 6.10, "weight": 280, "draft_grade": 7.9},
        {"name": "Jarek Broussard", "position": "RB", "college": "Oklahoma", "height": 5.80, "weight": 205, "draft_grade": 7.8},
        {"name": "Keon Stowers", "position": "OL", "college": "Louisville", "height": 6.25, "weight": 310, "draft_grade": 8.1},
        {"name": "Isaac Ukwu", "position": "DL", "college": "Iowa State", "height": 6.30, "weight": 285, "draft_grade": 7.7},
    ]
    
    def __init__(self):
        """Initialize NFL Draft connector."""
        self.session = requests.Session()
        logger.info("NFL Draft connector initialized")
    
    def fetch_prospects(self) -> List[Dict[str, Any]]:
        """
        Fetch prospect data from NFL Draft sources.
        
        Returns:
            List of prospect data dictionaries
        """
        logger.info("Fetching NFL Draft prospect data")
        
        try:
            # Try to fetch from ESPN API first
            prospects = self._fetch_from_espn()
            if prospects:
                logger.info(f"Fetched {len(prospects)} prospects from ESPN API")
                return prospects
        except Exception as e:
            logger.warning(f"ESPN API failed: {e}. Falling back to mock data.")
        
        # Fallback to mock data
        logger.info(f"Using {len(self.MOCK_PROSPECTS)} mock prospects")
        return self.MOCK_PROSPECTS
    
    def _fetch_from_espn(self) -> List[Dict[str, Any]]:
        """Try to fetch from ESPN API (if available)."""
        url = "https://site.api.espn.com/nfl/site/v2/draft"
        response = self.session.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        prospects = []
        if "draft" in data and "players" in data["draft"]:
            for player in data["draft"]["players"][:50]:  # Limit to 50
                prospect = {
                    "name": player.get("name"),
                    "position": player.get("position"),
                    "college": player.get("college"),
                    "height": player.get("height"),
                    "weight": player.get("weight"),
                    "draft_grade": player.get("grade", 7.5),
                }
                if prospect["name"]:
                    prospects.append(prospect)
        
        return prospects
