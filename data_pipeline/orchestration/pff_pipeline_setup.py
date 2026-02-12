"""
PFF Data Pipeline Integration

Integrates the PFF.com scraper into the main ETL pipeline orchestrator.
Sets up daily scheduling and error handling.
"""

import asyncio
import logging
from datetime import datetime

from data_pipeline.scrapers.pff_scraper import PFFScraper
from data_pipeline.orchestration.pipeline_orchestrator import (
    PipelineOrchestrator,
    PipelineStage,
    FailureMode,
)
from data_pipeline.orchestration.stage_connectors import (
    PFFConnector,
    PFFGradeLoadConnector,
    NFLComConnector,
    YahooConnector,
    ESPNConnector,
    ReconciliationConnector,
    QualityValidationConnector,
    SnapshotConnector,
)


logger = logging.getLogger(__name__)


class PFFPipelineSetup:
    """Sets up PFF scraper integration in the main pipeline."""

    @staticmethod
    def create_orchestrator(pff_scraper: PFFScraper) -> PipelineOrchestrator:
        """Create and configure pipeline orchestrator with PFF scraper.
        
        Args:
            pff_scraper: Instance of PFFScraper
            
        Returns:
            Configured PipelineOrchestrator ready for execution
        """
        logger.info("Setting up PFF pipeline orchestrator...")

        # Create orchestrator with partial success mode
        orchestrator = PipelineOrchestrator(
            failure_mode=FailureMode.PARTIAL_SUCCESS,
            max_retries=2,
            retry_delay_seconds=5,
            timeout_seconds=3600,
        )

        # Register PFF scraper stage (execute early, after NFL but before reconciliation)
        pff_connector = PFFConnector(scraper_instance=pff_scraper)
        orchestrator.register_stage(
            stage=PipelineStage.PFF_SCRAPE,
            connector=pff_connector,
            order=2,  # After NFL.com (order 1), before Yahoo (order 3)
        )

        # Register PFF grade loading stage (after PFF scraper, before reconciliation)
        pff_grade_connector = PFFGradeLoadConnector()
        orchestrator.register_stage(
            stage=PipelineStage.PFF_GRADE_LOAD,
            connector=pff_grade_connector,
            order=45,  # After PFF_SCRAPE (order 2), before RECONCILIATION
        )
        )

        logger.info("✓ PFF scraper registered in pipeline")
        logger.info("✓ PFF grade loading registered in pipeline")
        return orchestrator

    @staticmethod
    async def execute_pff_only(pff_scraper: PFFScraper) -> dict:
        """Execute just the PFF scraper stage (for testing).
        
        Args:
            pff_scraper: Instance of PFFScraper
            
        Returns:
            Execution results
        """
        logger.info("Executing PFF scraper only (test mode)...")
        
        connector = PFFConnector(scraper_instance=pff_scraper)
        result = await connector.execute()
        
        logger.info(f"✓ PFF scraper completed")
        logger.info(f"  - Prospects processed: {result['records_processed']}")
        logger.info(f"  - Prospects succeeded: {result['records_succeeded']}")
        logger.info(f"  - Prospects failed: {result['records_failed']}")
        
        return result


async def main():
    """Main entry point for PFF pipeline setup and testing."""
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger.info("=== PFF Pipeline Integration ===")
    logger.info(f"Starting at {datetime.utcnow().isoformat()}")

    # Create scraper instance
    logger.info("Initializing PFF scraper...")
    scraper = PFFScraper(season=2026, headless=True, cache_enabled=True)

    # Test scraper independently first
    logger.info("\n--- Testing PFF scraper independently ---")
    try:
        result = await PFFPipelineSetup.execute_pff_only(scraper)
        logger.info(f"✓ PFF scraper test successful: {result['records_processed']} prospects")
    except Exception as e:
        logger.error(f"✗ PFF scraper test failed: {e}")
        return

    # Create full orchestrator with PFF integrated
    logger.info("\n--- Setting up full pipeline orchestrator ---")
    orchestrator = PFFPipelineSetup.create_orchestrator(scraper)

    logger.info("\n=== PFF Pipeline Integration Complete ===")
    logger.info("Orchestrator ready for daily execution")


if __name__ == "__main__":
    asyncio.run(main())
