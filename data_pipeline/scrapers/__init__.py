"""
Data Pipeline Scrapers Module

Contains web scrapers for various data sources:
- pff_scraper_poc: PFF Draft Big Board scraper (Proof of Concept)
- Additional scrapers: NFL.com, Yahoo Sports, ESPN (in development)
"""

from .pff_scraper_poc import PFFScraperPoC

__all__ = ["PFFScraperPoC"]
