#!/usr/bin/env python
"""End-to-End ETL Pipeline Test Script

This script performs comprehensive E2E testing of the ETL orchestrator with:
1. Sample PFF data insertion
2. Sample CFR data insertion
3. Full orchestrator pipeline execution
4. Data quality validation
5. Results verification

Usage:
    PYTHONPATH=/home/parrot/code/draft-queen/src python scripts/test_e2e_etl.py

Requirements:
    - PostgreSQL database with draft_queen schema
    - All migrations applied (ETL-001 through ETL-009)
    - Poetry environment activated
"""

import asyncio
import sys
from uuid import uuid4
from datetime import datetime
from decimal import Decimal
import logging

# Add src to path for imports
sys.path.insert(0, '/home/parrot/code/draft-queen/src')

from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class E2ETestRunner:
    """End-to-end ETL pipeline test runner."""
    
    def __init__(self, db_url: str = "postgresql+asyncpg://parrot:draft_queen_dev@localhost/nfl_draft"):
        """Initialize test runner.
        
        Args:
            db_url: Database connection URL
        """
        self.db_url = db_url
        self.engine = None
        self.extraction_id = None
        self.test_results = {}
        
    async def setup(self):
        """Setup database connection."""
        try:
            self.engine = create_async_engine(self.db_url, echo=False)
            logger.info(f"Connected to database: {self.db_url}")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    async def teardown(self):
        """Cleanup database connection."""
        if self.engine:
            await self.engine.dispose()
    
    async def clear_test_data(self, session: AsyncSession):
        """Clear previous test data from staging tables."""
        try:
            await session.execute(text("DELETE FROM pff_staging WHERE extraction_id = :id"), {"id": str(self.extraction_id) if self.extraction_id else ""})
            await session.execute(text("DELETE FROM cfr_staging WHERE extraction_id = :id"), {"id": str(self.extraction_id) if self.extraction_id else ""})
            await session.commit()
            logger.info("✓ Cleared previous test data")
        except Exception as e:
            logger.warning(f"Could not clear test data: {e}")
    
    async def insert_test_pff_data(self, session: AsyncSession):
        """Insert sample PFF data into pff_staging."""
        try:
            # Sample PFF prospects
            test_data = [
                {
                    'extraction_id': str(self.extraction_id),
                    'pff_id': f'pff_test_001',
                    'first_name': 'John',
                    'last_name': 'Smith',
                    'position': 'QB',
                    'college': 'Alabama',
                    'overall_grade': 87.5,
                    'draft_year': 2024,
                },
                {
                    'extraction_id': str(self.extraction_id),
                    'pff_id': f'pff_test_002',
                    'first_name': 'Mike',
                    'last_name': 'Johnson',
                    'position': 'WR',
                    'college': 'Ohio State',
                    'overall_grade': 78.3,
                    'draft_year': 2024,
                },
                {
                    'extraction_id': str(self.extraction_id),
                    'pff_id': f'pff_test_003',
                    'first_name': 'David',
                    'last_name': 'Williams',
                    'position': 'RB',
                    'college': 'Georgia',
                    'overall_grade': 82.1,
                    'draft_year': 2024,
                },
            ]
            
            for row in test_data:
                await session.execute(
                    text("""
                        INSERT INTO pff_staging 
                        (extraction_id, pff_id, first_name, last_name, position, college, overall_grade, draft_year)
                        VALUES (:extraction_id, :pff_id, :first_name, :last_name, :position, :college, :overall_grade, :draft_year)
                    """),
                    row
                )
            
            await session.commit()
            logger.info(f"✓ Inserted {len(test_data)} PFF test records")
            self.test_results['pff_records_inserted'] = len(test_data)
            
        except Exception as e:
            logger.error(f"Failed to insert PFF test data: {e}")
            raise
    
    async def insert_test_cfr_data(self, session: AsyncSession):
        """Insert sample CFR data into cfr_staging."""
        try:
            import time
            unique_suffix = str(int(time.time() * 1000))
            
            # Sample CFR prospects
            test_data = [
                {
                    'extraction_id': str(self.extraction_id),
                    'cfr_player_id': f'cfr_test_001_{unique_suffix}',
                    'first_name': 'Tom',
                    'last_name': 'Jones',
                    'position': 'RB',
                    'college': 'Georgia',
                    'season': 2023,
                    'rushing_attempts': 250,
                    'rushing_yards': 1200,
                    'rushing_touchdowns': 12,
                    'receiving_targets': 45,
                    'receiving_receptions': 38,
                    'receiving_yards': 320,
                    'receiving_touchdowns': 2,
                },
                {
                    'extraction_id': str(self.extraction_id),
                    'cfr_player_id': f'cfr_test_002_{unique_suffix}',
                    'first_name': 'James',
                    'last_name': 'Brown',
                    'position': 'WR',
                    'college': 'Alabama',
                    'season': 2023,
                    'receiving_targets': 120,
                    'receiving_receptions': 95,
                    'receiving_yards': 1450,
                    'receiving_touchdowns': 14,
                    'rushing_attempts': 5,
                    'rushing_yards': 25,
                    'rushing_touchdowns': 0,
                },
            ]
            
            for row in test_data:
                await session.execute(
                    text("""
                        INSERT INTO cfr_staging 
                        (extraction_id, cfr_player_id, first_name, last_name, position, college, season,
                         rushing_attempts, rushing_yards, rushing_touchdowns,
                         receiving_targets, receiving_receptions, receiving_yards, receiving_touchdowns)
                        VALUES (:extraction_id, :cfr_player_id, :first_name, :last_name, :position, :college, :season,
                                :rushing_attempts, :rushing_yards, :rushing_touchdowns,
                                :receiving_targets, :receiving_receptions, :receiving_yards, :receiving_touchdowns)
                    """),
                    row
                )
            
            await session.commit()
            logger.info(f"✓ Inserted {len(test_data)} CFR test records")
            self.test_results['cfr_records_inserted'] = len(test_data)
            
        except Exception as e:
            logger.error(f"Failed to insert CFR test data: {e}")
            raise
    
    async def run_orchestrator(self, session: AsyncSession):
        """Run the ETL orchestrator pipeline."""
        try:
            # Import orchestrator and transformers
            logger.info("Importing ETL orchestrator...")
            from data_pipeline.etl_orchestrator import ETLOrchestrator, TransformerType
            logger.info("Importing transformers...")
            from data_pipeline.transformations.pff_transformer import PFFTransformer
            from data_pipeline.transformations.cfr_transformer import CFRTransformer
            logger.info("Importing validator...")
            from data_pipeline.validation.data_quality_validator import DataQualityValidator
            logger.info("All imports successful!")
            
            logger.info(f"\n{'='*60}")
            logger.info(f"Starting ETL Pipeline Execution")
            logger.info(f"Extraction ID: {self.extraction_id}")
            logger.info(f"{'='*60}\n")
            
            # Initialize transformers
            pff_transformer = PFFTransformer(session, self.extraction_id)
            cfr_transformer = CFRTransformer(session, self.extraction_id)
            logger.info("✓ Created transformers (PFF, CFR)")
            
            # Initialize validator
            validator = DataQualityValidator(session)
            logger.info("✓ Created data quality validator")
            
            # Initialize orchestrator with transformers
            transformers = {
                TransformerType.PFF: pff_transformer,
                TransformerType.CFR: cfr_transformer,
            }
            orchestrator = ETLOrchestrator(
                db=session,
                transformers=transformers,
                validator=validator,
                max_records_per_batch=1000,
                timeout_seconds=1800
            )
            logger.info("✓ Initialized ETL orchestrator")
            
            # Execute pipeline
            logger.info("\nExecuting ETL pipeline...\n")
            
            execution = await orchestrator.execute_extraction(
                extraction_id=self.extraction_id,
                transformer_types=[TransformerType.PFF, TransformerType.CFR]
            )
            
            # Store results
            self.test_results['execution_status'] = execution.overall_status
            self.test_results['duration_seconds'] = execution.duration_seconds
            self.test_results['prospects_loaded'] = execution.total_prospects_loaded
            self.test_results['grades_loaded'] = execution.total_grades_loaded
            self.test_results['stats_loaded'] = execution.total_stats_loaded
            self.test_results['quality_score'] = execution.quality_score
            
            return execution
            
        except Exception as e:
            logger.error(f"Orchestrator execution failed: {e}")
            raise
    
    async def verify_results(self, session: AsyncSession):
        """Verify ETL results in database."""
        try:
            logger.info(f"\n{'='*60}")
            logger.info("Verifying Results in Database")
            logger.info(f"{'='*60}\n")
            
            # Check prospect_core
            result = await session.execute(text("SELECT COUNT(*) as cnt FROM prospect_core"))
            prospect_count = result.scalar()
            logger.info(f"✓ prospect_core records: {prospect_count}")
            self.test_results['prospect_core_count'] = prospect_count
            
            # Check prospect_grades
            result = await session.execute(text("SELECT COUNT(*) as cnt FROM prospect_grades"))
            grades_count = result.scalar()
            logger.info(f"✓ prospect_grades records: {grades_count}")
            self.test_results['prospect_grades_count'] = grades_count
            
            # Check prospect_college_stats
            result = await session.execute(text("SELECT COUNT(*) as cnt FROM prospect_college_stats"))
            stats_count = result.scalar()
            logger.info(f"✓ prospect_college_stats records: {stats_count}")
            self.test_results['prospect_college_stats_count'] = stats_count
            
            # Check data_lineage
            result = await session.execute(text("SELECT COUNT(*) as cnt FROM data_lineage WHERE extraction_id = :id"), 
                                          {"id": str(self.extraction_id)})
            lineage_count = result.scalar() or 0
            logger.info(f"✓ data_lineage records (this extraction): {lineage_count}")
            self.test_results['lineage_count'] = lineage_count
            
            # Check etl_pipeline_runs (if table exists with the right schema)
            try:
                result = await session.execute(
                    text("""
                        SELECT extract_phase_status, total_staged_records, 
                               total_transformed_records, total_validated_records 
                        FROM etl_pipeline_runs WHERE extraction_id = :id
                    """),
                    {"id": str(self.extraction_id)}
                )
                run_info = result.first()
                if run_info:
                    logger.info(f"✓ ETL pipeline run extracted phase: {run_info[0]}")
                    logger.info(f"  - Records staged: {run_info[1]}")
                    logger.info(f"  - Records transformed: {run_info[2]}")
                    logger.info(f"  - Records validated: {run_info[3]}")
                    self.test_results['extract_phase_status'] = run_info[0]
                    self.test_results['records_staged'] = run_info[1]
                    self.test_results['records_transformed'] = run_info[2]
                    self.test_results['records_validated'] = run_info[3]
            except Exception as e:
                logger.warning(f"Could not query etl_pipeline_runs: {e}")
            
            # Check for duplicates
            result = await session.execute(
                text("""
                    SELECT COUNT(*) as cnt FROM prospect_core 
                    GROUP BY LOWER(name_first), LOWER(name_last), position, college 
                    HAVING COUNT(*) > 1
                """)
            )
            duplicate_groups = len(result.fetchall())
            logger.info(f"✓ Duplicate prospect groups: {duplicate_groups}")
            self.test_results['duplicate_groups'] = duplicate_groups
            
            # Sample data from prospect_grades
            logger.info("\nSample prospect_grades:")
            result = await session.execute(
                text("SELECT grade_normalized, source FROM prospect_grades LIMIT 3")
            )
            for row in result.fetchall():
                logger.info(f"  - Grade: {row[0]}, Source: {row[1]}")
            
            # Sample data from prospect_college_stats
            logger.info("\nSample prospect_college_stats:")
            result = await session.execute(
                text("SELECT season, rushing_yards, receiving_yards FROM prospect_college_stats LIMIT 2")
            )
            for row in result.fetchall():
                logger.info(f"  - Season: {row[0]}, Rush Yards: {row[1]}, Rec Yards: {row[2]}")
            
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            raise
    
    async def print_summary(self):
        """Print comprehensive test summary."""
        logger.info(f"\n{'='*60}")
        logger.info("E2E TEST SUMMARY")
        logger.info(f"{'='*60}\n")
        
        logger.info(f"Extraction ID: {self.extraction_id}")
        logger.info(f"Timestamp: {datetime.now().isoformat()}")
        logger.info(f"\nInput Data:")
        logger.info(f"  - PFF records inserted: {self.test_results.get('pff_records_inserted', 0)}")
        logger.info(f"  - CFR records inserted: {self.test_results.get('cfr_records_inserted', 0)}")
        logger.info(f"\nPipeline Results:")
        logger.info(f"  - Overall Status: {self.test_results.get('execution_status', 'N/A')}")
        logger.info(f"  - Duration: {self.test_results.get('duration_seconds', 0):.2f}s")
        logger.info(f"  - Quality Score: {self.test_results.get('quality_score', 0):.1f}%")
        logger.info(f"\nDatabase Verification:")
        logger.info(f"  - prospect_core records: {self.test_results.get('prospect_core_count', 0)}")
        logger.info(f"  - prospect_grades records: {self.test_results.get('prospect_grades_count', 0)}")
        logger.info(f"  - prospect_college_stats records: {self.test_results.get('prospect_college_stats_count', 0)}")
        logger.info(f"  - data_lineage records: {self.test_results.get('lineage_count', 0)}")
        logger.info(f"  - Duplicate groups: {self.test_results.get('duplicate_groups', 0)}")
        logger.info(f"\nPipeline Run Status:")
        logger.info(f"  - Status: {self.test_results.get('pipeline_status', 'N/A')}")
        logger.info(f"  - Staged: {self.test_results.get('records_staged', 0)}")
        logger.info(f"  - Transformed: {self.test_results.get('records_transformed', 0)}")
        logger.info(f"  - Loaded: {self.test_results.get('records_loaded', 0)}")
        
        # Final verdict
        # Check: Orchestrator succeeded, prospects and grades were loaded
        success = (
            self.test_results.get('execution_status') == 'success' and
            self.test_results.get('prospect_core_count', 0) > 0 and
            self.test_results.get('prospect_grades_count', 0) > 0
        )
        
        logger.info(f"\n{'='*60}")
        if success:
            logger.info("✅ E2E TEST PASSED - All checks successful!")
        else:
            logger.info("❌ E2E TEST FAILED - Check errors above")
        logger.info(f"{'='*60}\n")
        
        return success
    
    async def run(self):
        """Run complete E2E test suite."""
        try:
            await self.setup()
            
            # Create extraction_id first
            self.extraction_id = uuid4()
            
            async with AsyncSession(self.engine) as session:
                # Prepare data
                logger.info("Step 1: Preparing Test Data\n")
                await self.clear_test_data(session)
                await self.insert_test_pff_data(session)
                await self.insert_test_cfr_data(session)
                
                # Run orchestrator
                logger.info("\nStep 2: Running ETL Orchestrator\n")
                execution = await self.run_orchestrator(session)
                
                # Print execution details
                logger.info(f"\nPhase Execution Details:")
                for phase in execution.phases:
                    status_icon = "✓" if phase.status == "success" else "✗"
                    logger.info(f"  {status_icon} {phase.phase.value.upper()}: {phase.status} ({phase.duration_seconds:.2f}s)")
                    if phase.error_message:
                        logger.info(f"     ERROR: {phase.error_message}")
            
            # Create a FRESH session for verification to avoid transaction state issues
            async with AsyncSession(self.engine) as verify_session:
                # Verify results
                logger.info("\nStep 3: Verifying Results\n")
                await self.verify_results(verify_session)
                
                # Print summary
                success = await self.print_summary()
                
                return success
                
        except Exception as e:
            logger.error(f"\n❌ E2E TEST FAILED: {e}")
            return False
        finally:
            await self.teardown()


async def main():
    """Main entry point."""
    runner = E2ETestRunner()
    success = await runner.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
