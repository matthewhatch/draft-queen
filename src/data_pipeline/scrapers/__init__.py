"""
Data Pipeline Scrapers Module

Contains web scrapers for various data sources:
- pff_scraper: PFF Draft Big Board scraper (production-ready)
- Additional scrapers: NFL.com, Yahoo Sports, ESPN (in development)
"""

from .pff_scraper import PFFScraper

__all__ = ["PFFScraper"]
