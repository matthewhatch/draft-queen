"""Stage connector implementations for pipeline orchestrator.

Adapters that wrap actual data pipeline components to integrate with
the PipelineOrchestrator framework.
"""

import logging
from typing import Any, Dict

from data_pipeline.orchestration.pipeline_orchestrator import PipelineConnector


logger = logging.getLogger(__name__)


class NFLComConnector(PipelineConnector):
    """Connector for NFL.com prospect scraper stage."""

    def __init__(self, scraper_instance=None):
        """Initialize NFL.com connector.

        Args:
            scraper_instance: Instance of NFLComScraper (optional for testing)
        """
        self.scraper = scraper_instance

    async def execute(self) -> Dict[str, Any]:
        """Execute NFL.com scraper.

        Returns:
            Dictionary with:
                - records_processed: Total prospects scraped
                - records_succeeded: Prospects successfully processed
                - records_failed: Prospects that failed
                - data: Raw scraped prospect data
                - errors: List of errors encountered
        """
        logger.info("Executing NFL.com scraper stage")

        try:
            if self.scraper is None:
                # Would call actual scraper in production
                logger.warning("NFL.com scraper not configured, using mock")
                return {
                    "records_processed": 0,
                    "records_succeeded": 0,
                    "records_failed": 0,
                    "data": {},
                    "errors": ["Scraper not configured"],
                }

            # Call actual scraper
            prospects = await self.scraper.scrape()
            processed = len(prospects)
            succeeded = sum(1 for p in prospects if p.get("valid", True))

            return {
                "records_processed": processed,
                "records_succeeded": succeeded,
                "records_failed": processed - succeeded,
                "data": {"prospects": prospects},
                "errors": [],
            }
        except Exception as e:
            logger.error(f"NFL.com scraper failed: {e}")
            raise


class YahooConnector(PipelineConnector):
    """Connector for Yahoo Sports scraper stage."""

    def __init__(self, scraper_instance=None):
        """Initialize Yahoo Sports connector.

        Args:
            scraper_instance: Instance of YahooSportsScraper (optional for testing)
        """
        self.scraper = scraper_instance

    async def execute(self) -> Dict[str, Any]:
        """Execute Yahoo Sports scraper.

        Returns:
            Dictionary with:
                - records_processed: Total prospects with college stats
                - records_succeeded: Successfully processed stats
                - records_failed: Failed stats
                - data: College statistics data
                - errors: List of errors encountered
        """
        logger.info("Executing Yahoo Sports scraper stage")

        try:
            if self.scraper is None:
                logger.warning("Yahoo Sports scraper not configured, using mock")
                return {
                    "records_processed": 0,
                    "records_succeeded": 0,
                    "records_failed": 0,
                    "data": {},
                    "errors": ["Scraper not configured"],
                }

            # Call actual scraper
            stats = await self.scraper.scrape()
            processed = len(stats)
            succeeded = sum(1 for s in stats if s.get("valid", True))

            return {
                "records_processed": processed,
                "records_succeeded": succeeded,
                "records_failed": processed - succeeded,
                "data": {"stats": stats},
                "errors": [],
            }
        except Exception as e:
            logger.error(f"Yahoo Sports scraper failed: {e}")
            raise


class ESPNConnector(PipelineConnector):
    """Connector for ESPN injury scraper stage."""

    def __init__(self, scraper_instance=None):
        """Initialize ESPN connector.

        Args:
            scraper_instance: Instance of ESPNInjuryScraper (optional for testing)
        """
        self.scraper = scraper_instance

    async def execute(self) -> Dict[str, Any]:
        """Execute ESPN injury scraper.

        Returns:
            Dictionary with:
                - records_processed: Total injury records
                - records_succeeded: Successfully processed injuries
                - records_failed: Failed injuries
                - data: Injury data with changes
                - errors: List of errors encountered
        """
        logger.info("Executing ESPN injury scraper stage")

        try:
            if self.scraper is None:
                logger.warning("ESPN scraper not configured, using mock")
                return {
                    "records_processed": 0,
                    "records_succeeded": 0,
                    "records_failed": 0,
                    "data": {},
                    "errors": ["Scraper not configured"],
                }

            # Call actual scraper
            injuries = await self.scraper.scrape()
            processed = len(injuries)
            succeeded = sum(1 for i in injuries if i.get("valid", True))

            return {
                "records_processed": processed,
                "records_succeeded": succeeded,
                "records_failed": processed - succeeded,
                "data": {"injuries": injuries},
                "errors": [],
            }
        except Exception as e:
            logger.error(f"ESPN injury scraper failed: {e}")
            raise


class ReconciliationConnector(PipelineConnector):
    """Connector for data reconciliation stage."""

    def __init__(self, engine_instance=None):
        """Initialize reconciliation connector.

        Args:
            engine_instance: Instance of ReconciliationEngine (optional for testing)
        """
        self.engine = engine_instance

    async def execute(self) -> Dict[str, Any]:
        """Execute data reconciliation.

        Returns:
            Dictionary with:
                - records_processed: Total records reconciled
                - records_succeeded: Successfully reconciled
                - records_failed: Failed reconciliations
                - data: Reconciled data with conflict info
                - errors: Unresolvable conflicts
        """
        logger.info("Executing reconciliation stage")

        try:
            if self.engine is None:
                logger.warning("Reconciliation engine not configured, using mock")
                return {
                    "records_processed": 0,
                    "records_succeeded": 0,
                    "records_failed": 0,
                    "data": {},
                    "errors": ["Engine not configured"],
                }

            # Call actual reconciliation engine
            result = await self.engine.reconcile()
            processed = result.get("total_records", 0)
            succeeded = result.get("reconciled", 0)

            return {
                "records_processed": processed,
                "records_succeeded": succeeded,
                "records_failed": processed - succeeded,
                "data": result,
                "errors": result.get("unresolved_conflicts", []),
            }
        except Exception as e:
            logger.error(f"Reconciliation failed: {e}")
            raise


class QualityValidationConnector(PipelineConnector):
    """Connector for quality rules validation stage."""

    def __init__(self, engine_instance=None):
        """Initialize quality validation connector.

        Args:
            engine_instance: Instance of RulesEngine (optional for testing)
        """
        self.engine = engine_instance

    async def execute(self) -> Dict[str, Any]:
        """Execute quality rules validation.

        Returns:
            Dictionary with:
                - records_processed: Total records validated
                - records_succeeded: Records passing all rules
                - records_failed: Records with violations
                - data: Validation results
                - errors: Critical rule violations
        """
        logger.info("Executing quality validation stage")

        try:
            if self.engine is None:
                logger.warning("Rules engine not configured, using mock")
                return {
                    "records_processed": 0,
                    "records_succeeded": 0,
                    "records_failed": 0,
                    "data": {},
                    "errors": ["Engine not configured"],
                }

            # Call actual rules engine
            result = await self.engine.validate_dataset()
            processed = result.get("total_records", 0)
            succeeded = result.get("valid_records", 0)

            return {
                "records_processed": processed,
                "records_succeeded": succeeded,
                "records_failed": processed - succeeded,
                "data": result,
                "errors": result.get("critical_violations", []),
            }
        except Exception as e:
            logger.error(f"Quality validation failed: {e}")
            raise


class SnapshotConnector(PipelineConnector):
    """Connector for historical snapshot stage."""

    def __init__(self, manager_instance=None):
        """Initialize snapshot connector.

        Args:
            manager_instance: Instance of SnapshotManager (optional for testing)
        """
        self.manager = manager_instance

    async def execute(self) -> Dict[str, Any]:
        """Execute snapshot creation.

        Returns:
            Dictionary with:
                - records_processed: Total prospects snapshotted
                - records_succeeded: Successfully snapshotted
                - records_failed: Failed snapshots
                - data: Snapshot metadata
                - errors: Snapshot creation errors
        """
        logger.info("Executing snapshot stage")

        try:
            if self.manager is None:
                logger.warning("Snapshot manager not configured, using mock")
                return {
                    "records_processed": 0,
                    "records_succeeded": 0,
                    "records_failed": 0,
                    "data": {},
                    "errors": ["Manager not configured"],
                }

            # Call actual snapshot manager
            result = await self.manager.create_daily_snapshot()
            processed = result.get("total_prospects", 0)
            succeeded = result.get("snapshotted", 0)

            return {
                "records_processed": processed,
                "records_succeeded": succeeded,
                "records_failed": processed - succeeded,
                "data": result,
                "errors": result.get("errors", []),
            }
        except Exception as e:
            logger.error(f"Snapshot creation failed: {e}")
            raise


class PFFConnector(PipelineConnector):
    """Connector for PFF.com Draft Big Board scraper stage."""

    def __init__(self, scraper_instance=None):
        """Initialize PFF connector.

        Args:
            scraper_instance: Instance of PFFScraper (optional for testing)
        """
        self.scraper = scraper_instance

    async def execute(self) -> Dict[str, Any]:
        """Execute PFF.com scraper.

        Returns:
            Dictionary with:
                - records_processed: Total prospects scraped
                - records_succeeded: Prospects successfully processed
                - records_failed: Prospects that failed
                - data: Raw scraped prospect data
                - errors: List of errors encountered
        """
        logger.info("Executing PFF.com scraper stage")

        try:
            if self.scraper is None:
                logger.warning("PFF scraper not configured, using mock")
                return {
                    "records_processed": 0,
                    "records_succeeded": 0,
                    "records_failed": 0,
                    "data": {},
                    "errors": ["Scraper not configured"],
                }

            # Call actual scraper - scrape all pages
            prospects = await self.scraper.scrape_all_pages(max_pages=10)
            processed = len(prospects)
            succeeded = sum(1 for p in prospects if p.get("name"))

            logger.info(f"PFF scraper completed: {processed} prospects extracted")

            return {
                "records_processed": processed,
                "records_succeeded": succeeded,
                "records_failed": processed - succeeded,
                "data": {"prospects": prospects},
                "errors": [],
            }
        except Exception as e:
            logger.error(f"PFF scraper failed: {e}")
            raise


class PFFGradeLoadConnector(PipelineConnector):
    """Connector for PFF grade integration stage.
    
    Takes output from PFF scraper and loads grades into the database
    using fuzzy matching to link to existing prospects.
    """

    def __init__(self, pff_prospects: list[dict] = None):
        """Initialize PFF grade load connector.

        Args:
            pff_prospects: List of raw PFF prospect dicts from scraper (optional)
        """
        self.pff_prospects = pff_prospects or []

    def set_pff_prospects(self, pff_prospects: list[dict]):
        """Set PFF prospects data (called by orchestrator after PFF scrape stage).
        
        Args:
            pff_prospects: List of raw PFF prospect dicts from scraper
        """
        self.pff_prospects = pff_prospects

    async def execute(self) -> Dict[str, Any]:
        """Execute PFF grade loading stage.

        Returns:
            Dictionary with:
                - records_processed: Total PFF prospects
                - records_succeeded: Matched and loaded
                - records_failed: Unmatched or errored
                - data: Loading statistics
                - errors: List of errors encountered
        """
        logger.info("Executing PFF grade loading stage")

        try:
            from backend.database.connection import DatabaseManager
            from data_pipeline.loaders.pff_grade_loader import PFFGradeLoader

            if not self.pff_prospects:
                logger.warning("No PFF prospects provided for grade loading")
                return {
                    "records_processed": 0,
                    "records_succeeded": 0,
                    "records_failed": 0,
                    "data": {},
                    "errors": ["No PFF data available"],
                }

            with DatabaseManager().get_session() as session:
                loader = PFFGradeLoader(session)
                stats = loader.load(self.pff_prospects)

            logger.info(
                f"PFF grade loading completed: "
                f"matched={stats['matched']}, inserted={stats['inserted']}, "
                f"updated={stats['updated']}, unmatched={stats['unmatched']}"
            )

            return {
                "records_processed": stats["total"],
                "records_succeeded": stats["inserted"] + stats["updated"],
                "records_failed": stats["unmatched"] + stats["errors"],
                "data": {"stats": stats},
                "errors": [] if stats["errors"] == 0 else [f"{stats['errors']} errors during load"],
            }
        except Exception as e:
            logger.error(f"PFF grade loading failed: {e}")
            raise
