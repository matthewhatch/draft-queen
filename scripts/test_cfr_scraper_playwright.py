#!/usr/bin/env python
"""
Test script to verify Playwright-based CFR scraper works without 403 blocking.
Scrapes real QB data from College Football Reference.
"""

import asyncio
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data_sources.cfr_scraper import CFRScraper

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_cfr_scraper_playwright():
    """Test Playwright-based CFR scraper with a single position."""
    logger.info("=" * 70)
    logger.info("Testing Playwright-based CFR Scraper")
    logger.info("=" * 70)
    
    try:
        scraper = CFRScraper(rate_limit_delay=3.0)
        logger.info(f"✓ CFRScraper initialized")
        logger.info(f"  Base URL: {scraper.base_url}")
        logger.info(f"  Rate limit delay: 3.0s")
        
        logger.info("\n🔄 Scraping QB position from CFR...")
        players = await scraper.scrape(positions=['QB'])
        
        if players:
            logger.info(f"\n✓ SUCCESS: Scraped {len(players)} QB(s) from CFR")
            logger.info(f"  Playwright successfully bypassed 403 blocking!")
            
            # Show first few players
            for i, player in enumerate(players[:3], 1):
                logger.info(f"\n  Player {i}:")
                logger.info(f"    Name: {player.name}")
                logger.info(f"    School: {player.school}")
                logger.info(f"    Position: {player.position}")
                logger.info(f"    Stats: {player.stats}")
            
            if len(players) > 3:
                logger.info(f"\n  ... and {len(players) - 3} more players")
            
            logger.info("\n" + "=" * 70)
            logger.info("✓ TEST PASSED: Playwright scraper works!")
            logger.info("=" * 70)
            return True
        else:
            logger.error("\n✗ FAILED: No QB data returned from CFR")
            logger.error("  Playwright may not have bypassed the blocking")
            return False
            
    except Exception as e:
        logger.error(f"\n✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_cfr_scraper_playwright())
    sys.exit(0 if success else 1)
