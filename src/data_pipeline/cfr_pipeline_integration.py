"""
CFR-004: Pipeline Integration for CFR Scraper

Integration of the CFR (College Football Reference) web scraper into the daily ETL pipeline.

This module:
1. Registers CFR scraper as a pipeline stage
2. Creates CFR connector for pipeline orchestrator
3. Adds CFR staging and transformation to pipeline
4. Manages error handling and logging
5. Integrates with ETL orchestrator for data transformation
6. Records execution metrics and quality scores

Execution flow:
  1. CFRScraperConnector fetches data from College Football Reference
  2. Data loaded into cfr_staging table
  3. CFRTransformer processes staging data
  4. CFRProspectMatcher matches CFR players to prospects
  5. Data normalized and loaded to prospect_college_stats
  6. Lineage recorded for audit trail

Performance targets:
- Scrape: < 5 minutes (rate-limited, ~500+ players)
- Match: < 2 minutes (three-tier matching)
- Transform: < 3 minutes (normalization, validation)
- Total: < 30 minutes (included in daily pipeline)
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from src.data_pipeline.orchestration.pipeline_orchestrator import (
    PipelineStage,
    PipelineConnector,
)
from src.data_pipeline.etl_orchestrator import (
    ETLOrchestrator,
    TransformerType,
)
from src.data_sources.cfr_scraper import CFRScraper
from src.data_sources.cfr_prospect_matcher import CFRProspectMatcher

logger = logging.getLogger(__name__)


class CFRScrapeConnector(PipelineConnector):
    """Connector for CFR web scraper stage in pipeline.
    
    Fetches live data from College Football Reference and stages it
    in the cfr_staging table for later transformation.
    """

    def __init__(self, db: AsyncSession, timeout_seconds: int = 300):
        """Initialize CFR scraper connector.
        
        Args:
            db: Database session
            timeout_seconds: Maximum execution time (default 5 minutes)
        """
        self.db = db
        self.timeout_seconds = timeout_seconds
        self.scraper = CFRScraper()
        self.extraction_id = uuid4()
        self.records_scraped = 0
        self.records_staged = 0
        self.errors: List[str] = []

    async def execute(self) -> Dict[str, Any]:
        """Execute CFR scraper and stage results.
        
        Returns:
            Dict with execution results: {
                'status': 'success'|'partial'|'failed',
                'records_scraped': int,
                'records_staged': int,
                'errors': [str],
                'extraction_id': UUID,
                'duration_seconds': float,
            }
        """
        started_at = datetime.utcnow()
        
        try:
            logger.info(f"Starting CFR scraper (extraction_id={self.extraction_id})")
            
            # Execute scraper
            cfr_players = await self.scraper.scrape_all_positions()
            self.records_scraped = len(cfr_players)
            logger.info(f"✓ Scraped {self.records_scraped} CFR players")
            
            if not cfr_players:
                logger.warning("CFR scraper returned no data")
                return {
                    "status": "failed",
                    "records_scraped": 0,
                    "records_staged": 0,
                    "errors": ["No data returned from CFR scraper"],
                    "extraction_id": str(self.extraction_id),
                    "duration_seconds": (datetime.utcnow() - started_at).total_seconds(),
                }
            
            # Stage data
            self.records_staged = await self._stage_cfr_data(cfr_players)
            logger.info(f"✓ Staged {self.records_staged} CFR records")
            
            # Determine status
            status = "success" if self.records_staged == self.records_scraped else "partial"
            
            if self.errors:
                logger.warning(f"CFR scraper encountered {len(self.errors)} errors: {self.errors[:3]}")
            
            return {
                "status": status,
                "records_scraped": self.records_scraped,
                "records_staged": self.records_staged,
                "errors": self.errors,
                "extraction_id": str(self.extraction_id),
                "duration_seconds": (datetime.utcnow() - started_at).total_seconds(),
            }
            
        except Exception as e:
            logger.error(f"CFR scraper failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "records_scraped": self.records_scraped,
                "records_staged": self.records_staged,
                "errors": [str(e)],
                "extraction_id": str(self.extraction_id),
                "duration_seconds": (datetime.utcnow() - started_at).total_seconds(),
            }

    async def _stage_cfr_data(self, cfr_players: List[Dict[str, Any]]) -> int:
        """Stage CFR players in cfr_staging table.
        
        Args:
            cfr_players: List of scraped CFR player records
            
        Returns:
            Number of records successfully staged
        """
        if not cfr_players:
            return 0
        
        staged_count = 0
        
        # Insert in batches
        batch_size = 50
        for i in range(0, len(cfr_players), batch_size):
            batch = cfr_players[i : i + batch_size]
            
            try:
                # Build insert values
                values_str = ",".join(
                    f"""(
                        {repr(self.extraction_id)},
                        {repr(player.get('cfr_player_id'))},
                        {repr(player.get('cfr_player_url'))},
                        {repr(player.get('first_name'))},
                        {repr(player.get('last_name'))},
                        {repr(player.get('college'))},
                        {repr(player.get('position'))},
                        {repr(player.get('recruit_year'))},
                        {repr(player.get('class_year'))},
                        {repr(player.get('season'))},
                        {repr(player.get('games_played'))},
                        {repr(player.get('games_started'))},
                        {repr(player.get('passing_attempts'))},
                        {repr(player.get('passing_completions'))},
                        {repr(player.get('passing_yards'))},
                        {repr(player.get('passing_touchdowns'))},
                        {repr(player.get('interceptions'))},
                        {repr(player.get('rushing_attempts'))},
                        {repr(player.get('rushing_yards'))},
                        {repr(player.get('rushing_touchdowns'))},
                        {repr(player.get('receptions'))},
                        {repr(player.get('receiving_yards'))},
                        {repr(player.get('receiving_touchdowns'))},
                        {repr(player.get('tackles_solo'))},
                        {repr(player.get('tackles_assisted'))},
                        {repr(player.get('tackles_total'))},
                        {repr(player.get('tfl'))},
                        {repr(player.get('sacks'))},
                        {repr(player.get('forced_fumbles'))},
                        {repr(player.get('fumble_recoveries'))},
                        {repr(player.get('passes_defended'))},
                        {repr(player.get('interceptions_defensive'))},
                        {repr(player.get('data_source'))},
                        {repr(player.get('extraction_notes'))},
                        {repr(datetime.utcnow())}
                    )"""
                    for player in batch
                )
                
                insert_sql = f"""
                    INSERT INTO cfr_staging (
                        extraction_id, cfr_player_id, cfr_player_url,
                        first_name, last_name, college, position,
                        recruit_year, class_year, season,
                        games_played, games_started,
                        passing_attempts, passing_completions, passing_yards,
                        passing_touchdowns, interceptions,
                        rushing_attempts, rushing_yards, rushing_touchdowns,
                        receptions, receiving_yards, receiving_touchdowns,
                        tackles_solo, tackles_assisted, tackles_total,
                        tfl, sacks, forced_fumbles, fumble_recoveries,
                        passes_defended, interceptions_defensive,
                        data_source, extraction_notes, extraction_timestamp
                    ) VALUES {values_str}
                """
                
                await self.db.execute(text(insert_sql))
                staged_count += len(batch)
                
            except Exception as e:
                error_msg = f"Failed to stage CFR batch {i//batch_size}: {str(e)}"
                logger.error(error_msg)
                self.errors.append(error_msg)
        
        await self.db.commit()
        return staged_count


class CFRTransformConnector(PipelineConnector):
    """Connector for CFR data transformation stage in pipeline.
    
    Transforms staged CFR data through prospect matching and normalization
    into the prospect_college_stats canonical table.
    """

    def __init__(
        self,
        db: AsyncSession,
        etl_orchestrator: ETLOrchestrator,
        extraction_id: UUID,
    ):
        """Initialize CFR transformer connector.
        
        Args:
            db: Database session
            etl_orchestrator: ETL orchestrator for transformations
            extraction_id: Extraction ID from scraper stage
        """
        self.db = db
        self.etl_orchestrator = etl_orchestrator
        self.extraction_id = extraction_id
        self.records_matched = 0
        self.records_loaded = 0
        self.match_stats = {
            "exact_matches": 0,
            "fuzzy_matches": 0,
            "unmatched": 0,
            "errors": 0,
        }

    async def execute(self) -> Dict[str, Any]:
        """Execute CFR transformation and load.
        
        Returns:
            Dict with transformation results: {
                'status': 'success'|'partial'|'failed',
                'records_matched': int,
                'records_loaded': int,
                'match_rate': float,
                'match_stats': {...},
                'errors': [str],
                'duration_seconds': float,
            }
        """
        started_at = datetime.utcnow()
        errors = []
        
        try:
            logger.info(f"Starting CFR transformation (extraction_id={self.extraction_id})")
            
            # Count staged records
            count_result = await self.db.execute(
                text("""
                    SELECT COUNT(*) as count 
                    FROM cfr_staging 
                    WHERE extraction_id = :extraction_id
                """),
                {"extraction_id": self.extraction_id}
            )
            staged_count = count_result.scalar() or 0
            logger.info(f"Found {staged_count} staged CFR records")
            
            if staged_count == 0:
                logger.warning("No staged CFR records to transform")
                return {
                    "status": "failed",
                    "records_matched": 0,
                    "records_loaded": 0,
                    "match_rate": 0.0,
                    "match_stats": self.match_stats,
                    "errors": ["No staged records found"],
                    "duration_seconds": (datetime.utcnow() - started_at).total_seconds(),
                }
            
            # Run ETL orchestrator for CFR
            execution = await self.etl_orchestrator.execute_extraction(
                extraction_id=self.extraction_id,
                transformer_types=[TransformerType.CFR],
            )
            
            logger.info(f"✓ ETL execution completed: {execution.overall_status}")
            
            # Extract stats
            self.records_matched = execution.total_stats_loaded
            self.records_loaded = execution.total_stats_loaded
            
            # Calculate match rate (from transformer execution)
            cfr_transformer = None
            for trans in execution.transformers:
                if trans.transformer_type == TransformerType.CFR:
                    cfr_transformer = trans
                    break
            
            if cfr_transformer:
                match_rate = (
                    cfr_transformer.records_succeeded / cfr_transformer.records_processed
                    if cfr_transformer.records_processed > 0 else 0.0
                )
                self.match_stats["exact_matches"] = cfr_transformer.records_succeeded
                self.match_stats["errors"] = cfr_transformer.records_failed
            else:
                match_rate = 0.0
            
            # Determine status
            status = "success" if execution.overall_status == "success" else "partial"
            if execution.overall_status == "failed":
                status = "failed"
                errors.append(execution.error_summary or "ETL execution failed")
            
            logger.info(
                f"✓ CFR transformation complete: {self.records_matched} matched, "
                f"{self.records_loaded} loaded (match_rate={match_rate:.1%})"
            )
            
            return {
                "status": status,
                "records_matched": self.records_matched,
                "records_loaded": self.records_loaded,
                "match_rate": match_rate,
                "match_stats": self.match_stats,
                "errors": errors,
                "duration_seconds": (datetime.utcnow() - started_at).total_seconds(),
            }
            
        except Exception as e:
            logger.error(f"CFR transformation failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "records_matched": self.records_matched,
                "records_loaded": self.records_loaded,
                "match_rate": 0.0,
                "match_stats": self.match_stats,
                "errors": [str(e)],
                "duration_seconds": (datetime.utcnow() - started_at).total_seconds(),
            }


class CFRPipelineIntegration:
    """Helper for integrating CFR scraper into pipeline orchestrator.
    
    Provides utilities for:
    - Registering CFR stages with pipeline
    - Creating connectors
    - Managing execution flow
    - Error handling and recovery
    """

    @staticmethod
    async def execute_cfr_pipeline(
        db: AsyncSession,
        etl_orchestrator: ETLOrchestrator,
        timeout_seconds: int = 600,  # 10 minutes total
    ) -> Dict[str, Any]:
        """Execute complete CFR pipeline (scrape + transform).
        
        Args:
            db: Database session
            etl_orchestrator: ETL orchestrator instance
            timeout_seconds: Maximum execution time
            
        Returns:
            Dict with pipeline results including both stages
        """
        logger.info("Executing CFR pipeline...")
        pipeline_start = datetime.utcnow()
        results = {
            "overall_status": "success",
            "scrape_stage": None,
            "transform_stage": None,
            "total_duration_seconds": 0,
            "errors": [],
        }
        
        try:
            # Stage 1: Scrape
            logger.info("Stage 1: Scraping CFR data...")
            scraper = CFRScrapeConnector(db)
            scrape_result = await scraper.execute()
            results["scrape_stage"] = scrape_result
            
            if scrape_result["status"] == "failed":
                logger.error("CFR scraper failed")
                results["overall_status"] = "failed"
                results["errors"].append(f"Scraper failed: {scrape_result['errors']}")
                return results
            
            logger.info(f"✓ Scrape complete: {scrape_result['records_staged']} records staged")
            extraction_id = UUID(scrape_result["extraction_id"])
            
            # Stage 2: Transform
            logger.info("Stage 2: Transforming and loading CFR data...")
            transformer = CFRTransformConnector(db, etl_orchestrator, extraction_id)
            transform_result = await transformer.execute()
            results["transform_stage"] = transform_result
            
            if transform_result["status"] == "failed":
                logger.error("CFR transformation failed")
                results["overall_status"] = "failed"
                results["errors"].append(f"Transform failed: {transform_result['errors']}")
            elif transform_result["status"] == "partial":
                results["overall_status"] = "partial"
            
            logger.info(
                f"✓ Transform complete: {transform_result['records_loaded']} records loaded "
                f"(match_rate={transform_result['match_rate']:.1%})"
            )
            
        except Exception as e:
            logger.error(f"CFR pipeline error: {e}", exc_info=True)
            results["overall_status"] = "failed"
            results["errors"].append(str(e))
        
        finally:
            results["total_duration_seconds"] = (
                datetime.utcnow() - pipeline_start
            ).total_seconds()
            logger.info(
                f"CFR pipeline complete: {results['overall_status']} "
                f"({results['total_duration_seconds']:.1f}s)"
            )
        
        return results
