#!/usr/bin/env python
"""Quick E2E Test with Cached PFF Data + Mock CFR Data

Faster E2E test that:
- Uses cached PFF data (no browser needed)
- Uses mock CFR data (website is blocking)
- Runs full ETL pipeline
- Verifies results
"""

import asyncio
import sys
from uuid import uuid4
from datetime import datetime
from decimal import Decimal
import logging
import time

# Add src to path
sys.path.insert(0, '/home/parrot/code/draft-queen/src')

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class QuickE2ETest:
    """Quick E2E test using cached/mock data."""
    
    def __init__(self, db_url: str = "postgresql+asyncpg://parrot:draft_queen_dev@localhost/nfl_draft"):
        self.db_url = db_url
        self.engine = None
        self.extraction_id = None
        self.results = {}
        
    async def setup(self):
        self.engine = create_async_engine(self.db_url, echo=False)
        logger.info("✓ Connected to database")
    
    async def teardown(self):
        if self.engine:
            await self.engine.dispose()
    
    def get_pff_cached_data(self) -> list:
        """Load cached PFF data from file."""
        import json
        from pathlib import Path
        
        cache_dir = Path.home() / ".cache" / "pff_scraper"
        
        # Look for cached pages
        pff_data = []
        for cache_file in sorted(cache_dir.glob("*.json")):
            try:
                with open(cache_file) as f:
                    data = json.load(f)
                    if 'prospects' in data:
                        pff_data.extend(data['prospects'])
                        logger.debug(f"Loaded {len(data['prospects'])} prospects from {cache_file.name}")
            except Exception as e:
                logger.warning(f"Could not load {cache_file}: {e}")
        
        logger.info(f"✓ Loaded {len(pff_data)} PFF prospects from cache")
        return pff_data[:20]  # Use first 20 for testing
    
    def get_mock_cfr_data(self) -> list:
        """Get mock CFR data."""
        from data_sources.cfr_scraper import CFRPlayer
        
        return [
            CFRPlayer(
                name='Saquon Barkley Jr', position='RB', school='Penn State',
                stats={'rushing_attempts': 300, 'rushing_yards': 1500, 'rushing_touchdowns': 15,
                       'receiving_receptions': 45, 'receiving_yards': 350, 'receiving_touchdowns': 2}
            ),
            CFRPlayer(
                name='Marvin Harrison III', position='WR', school='Ohio State',
                stats={'receiving_receptions': 110, 'receiving_yards': 1600, 'receiving_touchdowns': 14,
                       'rushing_attempts': 2, 'rushing_yards': 10, 'rushing_touchdowns': 0}
            ),
            CFRPlayer(
                name='Travis Hunter', position='EDGE', school='Colorado',
                stats={'sacks': 15, 'tackles_for_loss': 25, 'tackles_solo': 80, 'tackles_total': 120,
                       'forced_fumbles': 3, 'passes_defended': 2}
            ),
        ]
    
    async def insert_pff_data(self, session: AsyncSession, pff_data: list):
        """Insert PFF data into staging."""
        try:
            count = 0
            for prospect in pff_data:
                try:
                    await session.execute(
                        text("""
                            INSERT INTO pff_staging 
                            (extraction_id, pff_id, first_name, last_name, position, college, overall_grade, draft_year)
                            VALUES (:extraction_id, :pff_id, :first_name, :last_name, :position, :college, :overall_grade, :draft_year)
                        """),
                        {
                            'extraction_id': str(self.extraction_id),
                            'pff_id': f"pff_{uuid4().hex[:12]}",
                            'first_name': prospect.get('first_name', 'Unknown'),
                            'last_name': prospect.get('last_name', 'Unknown'),
                            'position': prospect.get('position', 'Unknown'),
                            'college': prospect.get('college', 'Unknown'),
                            'overall_grade': Decimal(str(prospect.get('grade', 0))),
                            'draft_year': 2026
                        }
                    )
                    count += 1
                except Exception as e:
                    logger.debug(f"Could not insert prospect: {e}")
            
            await session.commit()
            logger.info(f"✓ Inserted {count} PFF records")
            self.results['pff_inserted'] = count
        except Exception as e:
            logger.error(f"Failed to insert PFF data: {e}")
            raise
    
    async def insert_cfr_data(self, session: AsyncSession, cfr_data: list):
        """Insert CFR data into staging."""
        try:
            count = 0
            for player in cfr_data:
                try:
                    await session.execute(
                        text("""
                            INSERT INTO cfr_staging 
                            (extraction_id, cfr_player_id, first_name, last_name, position, college, season,
                             rushing_attempts, rushing_yards, rushing_touchdowns, receiving_receptions, 
                             receiving_yards, receiving_touchdowns)
                            VALUES (:extraction_id, :cfr_player_id, :first_name, :last_name, :position, 
                                    :college, :season, :rushing_attempts, :rushing_yards, :rushing_touchdowns,
                                    :receiving_receptions, :receiving_yards, :receiving_touchdowns)
                        """),
                        {
                            'extraction_id': str(self.extraction_id),
                            'cfr_player_id': f"cfr_{uuid4().hex[:12]}",
                            'first_name': player.name.split()[0],
                            'last_name': ' '.join(player.name.split()[1:]) or 'Unknown',
                            'position': player.position,
                            'college': player.school,
                            'season': 2025,
                            'rushing_attempts': Decimal(str(player.stats.get('rushing_attempts', 0))),
                            'rushing_yards': Decimal(str(player.stats.get('rushing_yards', 0))),
                            'rushing_touchdowns': Decimal(str(player.stats.get('rushing_touchdowns', 0))),
                            'receiving_receptions': Decimal(str(player.stats.get('receiving_receptions', 0))),
                            'receiving_yards': Decimal(str(player.stats.get('receiving_yards', 0))),
                            'receiving_touchdowns': Decimal(str(player.stats.get('receiving_touchdowns', 0)))
                        }
                    )
                    count += 1
                except Exception as e:
                    logger.debug(f"Could not insert player: {e}")
            
            await session.commit()
            logger.info(f"✓ Inserted {count} CFR records")
            self.results['cfr_inserted'] = count
        except Exception as e:
            logger.error(f"Failed to insert CFR data: {e}")
            raise
    
    async def run_orchestrator(self, session: AsyncSession):
        """Run ETL orchestrator."""
        try:
            logger.info("🔄 Running ETL orchestrator...")
            from data_pipeline.etl_orchestrator import ETLOrchestrator
            
            orchestrator = ETLOrchestrator(db=self.engine)
            result = await orchestrator.execute_extraction(extraction_id=self.extraction_id)
            
            self.results['pipeline_status'] = result.status.value if result.status else 'unknown'
            self.results['pipeline_duration'] = (result.ended_at - result.started_at).total_seconds() if result.ended_at else 0
            logger.info(f"✓ Pipeline completed: {self.results['pipeline_status']}")
        except Exception as e:
            logger.error(f"Failed to run orchestrator: {e}")
            raise
    
    async def verify_results(self, session: AsyncSession):
        """Verify database results."""
        try:
            logger.info("✓ Verifying database results...")
            
            # Check prospect_core
            result = await session.execute(text("SELECT COUNT(*) FROM prospect_core"))
            self.results['prospect_core'] = result.scalar() or 0
            
            # Check prospect_grades
            result = await session.execute(text("SELECT COUNT(*) FROM prospect_grades"))
            self.results['prospect_grades'] = result.scalar() or 0
            
            # Check prospect_college_stats
            result = await session.execute(text("SELECT COUNT(*) FROM prospect_college_stats"))
            self.results['prospect_college_stats'] = result.scalar() or 0
            
            logger.info(f"  - prospect_core: {self.results['prospect_core']}")
            logger.info(f"  - prospect_grades: {self.results['prospect_grades']}")
            logger.info(f"  - prospect_college_stats: {self.results['prospect_college_stats']}")
        except Exception as e:
            logger.warning(f"Could not verify all results: {e}")
    
    async def run(self):
        """Run complete test."""
        start = time.time()
        
        try:
            print("\n" + "="*70)
            print("QUICK E2E TEST - REAL PFF + MOCK CFR DATA".center(70))
            print("="*70 + "\n")
            
            await self.setup()
            self.extraction_id = uuid4()
            
            async with AsyncSession(self.engine) as session:
                # Phase 1: Load data
                logger.info("\n📡 PHASE 1: Loading Data")
                print("-"*70)
                pff_data = self.get_pff_cached_data()
                cfr_data = self.get_mock_cfr_data()
                
                # Phase 2: Insert into staging
                logger.info("\n📝 PHASE 2: Inserting into Staging")
                print("-"*70)
                await self.insert_pff_data(session, pff_data)
                await self.insert_cfr_data(session, cfr_data)
                
                # Phase 3: Run orchestrator
                logger.info("\n⚙️  PHASE 3: ETL Orchestrator")
                print("-"*70)
                await self.run_orchestrator(session)
                
                # Phase 4: Verify
                logger.info("\n✅ PHASE 4: Verification")
                print("-"*70)
                await self.verify_results(session)
            
            # Print summary
            elapsed = time.time() - start
            print("\n" + "="*70)
            print("TEST SUMMARY".center(70))
            print("="*70)
            print(f"\nExecution ID: {self.extraction_id}")
            print(f"Duration: {elapsed:.2f}s")
            print(f"\nData Inserted:")
            print(f"  - PFF: {self.results.get('pff_inserted', 0)}")
            print(f"  - CFR: {self.results.get('cfr_inserted', 0)}")
            print(f"\nPipeline:")
            print(f"  - Status: {self.results.get('pipeline_status', 'unknown')}")
            print(f"  - Duration: {self.results.get('pipeline_duration', 0):.2f}s")
            print(f"\nDatabase Results:")
            print(f"  - prospect_core: {self.results.get('prospect_core', 0)}")
            print(f"  - prospect_grades: {self.results.get('prospect_grades', 0)}")
            print(f"  - prospect_college_stats: {self.results.get('prospect_college_stats', 0)}")
            
            # Verdict
            success = (self.results.get('pff_inserted', 0) > 0 and 
                      self.results.get('pipeline_status') == 'success')
            
            if success:
                print(f"\n{'✅ E2E TEST PASSED'.center(70)}")
            else:
                print(f"\n{'⚠️  E2E TEST COMPLETED WITH ISSUES'.center(70)}")
            print("="*70 + "\n")
            
            return 0 if success else 1
            
        except Exception as e:
            logger.error(f"\n❌ TEST FAILED: {e}")
            print("="*70 + "\n")
            return 1
        finally:
            await self.teardown()


async def main():
    test = QuickE2ETest()
    return await test.run()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
