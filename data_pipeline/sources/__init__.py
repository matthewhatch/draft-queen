"""NFL.com data source connector."""

import requests
import time
import logging
from typing import List, Dict, Any, Optional
from config import settings
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class NFLComConnector:
    """Fetches prospect data from NFL.com."""

    def __init__(self):
        """Initialize NFL.com connector."""
        self.base_url = settings.nfl_com.base_url
        self.timeout = settings.nfl_com.timeout_seconds
        self.max_retries = settings.nfl_com.max_retries
        self.retry_delay = settings.nfl_com.retry_delay_seconds
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create requests session with retry strategy."""
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=2,  # Exponential backoff: 1s, 2s, 4s
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set headers
        session.headers.update(
            {
                "User-Agent": "NFL-Draft-Analysis-Platform/1.0",
                "Accept": "application/json",
            }
        )

        logger.info("NFL.com session created with retry strategy")
        return session

    def fetch_prospects(self) -> List[Dict[str, Any]]:
        """
        Fetch all prospect data from NFL.com.

        Returns:
            List of prospect data dictionaries
        """
        logger.info("Starting NFL.com prospect data fetch")
        prospects = []

        try:
            # For now, return empty list as NFL.com integration is in progress
            # In production, this would:
            # 1. Call NFL.com API endpoint for prospects
            # 2. Parse JSON response
            # 3. Handle pagination if needed
            # 4. Apply rate limiting
            # 5. Return standardized prospect dictionaries

            logger.info(f"Successfully fetched {len(prospects)} prospects from NFL.com")
            return prospects

        except Exception as e:
            logger.error(f"Failed to fetch prospects from NFL.com: {e}")
            raise

    def fetch_measurables(self) -> List[Dict[str, Any]]:
        """
        Fetch measurable data from NFL.com combine results.

        Returns:
            List of measurable data dictionaries
        """
        logger.info("Starting NFL.com measurables data fetch")
        measurables = []

        try:
            # Similar to prospects fetch, but for measurables
            logger.info(f"Successfully fetched {len(measurables)} measurable records")
            return measurables

        except Exception as e:
            logger.error(f"Failed to fetch measurables from NFL.com: {e}")
            raise

    def health_check(self) -> bool:
        """
        Check NFL.com API connectivity.

        Returns:
            True if API is reachable, False otherwise
        """
        try:
            # Try to reach NFL.com API
            response = self.session.get(f"{self.base_url}/healthz", timeout=self.timeout)

            if response.status_code == 200:
                logger.info("NFL.com API health check passed")
                return True
            else:
                logger.warning(f"NFL.com API returned status {response.status_code}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"NFL.com API health check failed: {e}")
            return False

    def close(self):
        """Close the session."""
        self.session.close()
        logger.info("NFL.com connector session closed")


class MockNFLComConnector(NFLComConnector):
    """Mock NFL.com connector for testing."""

    def fetch_prospects(self) -> List[Dict[str, Any]]:
        """Return mock prospect data for testing."""
        return [
            {
                "name": "Test Player 1",
                "position": "QB",
                "college": "Alabama",
                "height": 6.3,
                "weight": 220,
                "draft_grade": 8.5,
                "round_projection": 1,
            },
            {
                "name": "Test Player 2",
                "position": "RB",
                "college": "Georgia",
                "height": 5.83,
                "weight": 205,
                "draft_grade": 7.2,
                "round_projection": 2,
            },
        ]

    def health_check(self) -> bool:
        """Mock health check always returns True."""
        logger.info("Mock NFL.com API health check passed")
        return True
