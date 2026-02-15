# College Football Reference Integration - Technical Specification

**Date:** February 15, 2026  
**Related:** [Product Strategy](./PRODUCT_STRATEGY_CFR_INTEGRATION.md)  
**Status:** Technical Design Phase

---

## Overview

This document outlines the technical implementation for adding College Football Reference (CFR) as a data source. It complements the product strategy and provides engineering-level detail.

---

## Data Source Analysis

### College Football Reference Overview

**Website:** https://www.sports-reference.com/cfb/

**Public Access:** Yes (respects robots.txt, public data)

**Key URL Patterns:**
```
Team Rosters: /cfb/schools/{team}/2026.html
Player Stats: /cfb/players/{name}-{id}.html
Position Lists: /cfb/positions/{position}/2026.html
Draft Class: /cfb/draft/2026.html (comprehensive)
```

**Data Quality:** 
- ✅ Authoritative (official NCAA stats)
- ✅ Complete (all FBS + many FCS schools)
- ✅ Consistent (normalized across years)
- ✅ Current (updated weekly during season)

### HTML Structure Example

**Team Roster Page:**
```html
<table id="roster">
  <tr>
    <td>
      <a href="/cfb/players/name-id.html">Player Name</a>
    </td>
    <td>Pos</td>
    <td>School</td>
    <td>Year</td>
    <td>...</td>
  </tr>
</table>
```

**Player Stats Page:**
```html
<h1>Player Name (Draft Class 2026)</h1>
<table id="stats">
  <tr>
    <td>2025</td>  <!-- Season -->
    <td>School</td>
    <td>Pos</td>
    <td>Games</td>
    <td>Pass Yards</td>
    <!-- Position-specific stats follow -->
  </tr>
</table>
```

---

## Scraper Architecture

### Scraper Class: `CFRScraper`

**File:** `src/data_pipeline/scrapers/cfr_scraper.py`

**Design Pattern:** Inherits from `BaseScraper` (existing)

```python
class CFRScraper(BaseScraper):
    """
    Scrapes college football stats from sports-reference.com
    
    Approach:
    1. Get 2026 draft class list
    2. For each prospect, scrape individual player page
    3. Extract college stats for 2024-2025 seasons
    4. Normalize and validate data
    5. Store in cache and database
    """
    
    BASE_URL = "https://www.sports-reference.com/cfb"
    CACHE_DIR = Path(__file__).parent.parent.parent / "data" / "cache" / "cfr"
    RATE_LIMIT_DELAY = 2.0  # seconds
    
    async def scrape_2026_draft_class(self) -> Dict[str, Any]:
        """Main entry point: Get all prospects in 2026 draft"""
        # 1. Load list of notable prospects (from draft tracker)
        # 2. Scrape each player's stats page
        # 3. Cache results
        # 4. Return structured data
        
    async def scrape_player_stats(self, player_url: str) -> Dict[str, Any]:
        """Scrape single player's college statistics"""
        # 1. Fetch player page
        # 2. Extract name, school, position, years
        # 3. Parse stats table for each season
        # 4. Extract position-specific stats
        # 5. Return normalized dict
        
    def _parse_stats_by_position(self, position: str, row: BeautifulSoup) -> Dict:
        """Position-specific stats parsing"""
        # QB: Passing yards, TDs, INTs, completion %, rating
        # RB: Rushing yards/TDs, receptions, yards per carry
        # WR: Receptions, receiving yards/TDs, yards per catch
        # TE: Receptions, receiving yards/TDs
        # OL: Games started, all-conference selections
        # DL: Tackles, sacks, TFLs, forced fumbles
        # LB: Tackles, TFLs, sacks, passes defended
        # DB: Passes defended, INTs, tackles
        
    def _match_to_prospect(self, cfr_prospect: Dict) -> Optional[str]:
        """Match CFR player to existing prospect ID"""
        # Strategy:
        # 1. Exact match: name + school + position
        # 2. Fuzzy match: name similarity > 0.85 + school + position
        # 3. Return prospect_id or None
```

### Matching Algorithm

**Challenge:** Same player may be named differently across sources

**Solution:** Multi-strategy matching

```python
def _match_to_prospect(self, cfr_data: Dict) -> Optional[UUID]:
    """
    Match CFR player to existing prospect
    
    Strategy (in order):
    1. Exact match: name=X AND school=Y AND position=Z
    2. Last name + position + school (handle prefix variations)
    3. Fuzzy name match (85%+) + school
    4. Fuzzy name match (80%+) + position (stricter, fewer false positives)
    5. Not found: Flag for manual review
    """
    from difflib import SequenceMatcher
    
    cfr_name = cfr_data['name'].strip().upper()
    cfr_school = cfr_data['school'].strip().upper()
    cfr_position = cfr_data['position'].strip().upper()
    
    # Try exact match first
    exact = session.query(Prospect).filter(
        Prospect.name.ilike(cfr_name),
        Prospect.college.ilike(cfr_school),
        Prospect.position == cfr_position
    ).first()
    
    if exact:
        return exact.id
    
    # Try fuzzy match (expensive, so limited scope)
    candidates = session.query(Prospect).filter(
        Prospect.college.ilike(cfr_school),
        Prospect.position == cfr_position
    ).all()
    
    for candidate in candidates:
        ratio = SequenceMatcher(None, cfr_name, candidate.name.upper()).ratio()
        if ratio > 0.85:
            return candidate.id
    
    # No match found
    return None
```

### Error Handling & Recovery

```python
class CFRScraperConfig:
    """Configuration with resilience settings"""
    
    BASE_URL = "https://www.sports-reference.com/cfb"
    CACHE_DIR = Path(__file__).parent.parent.parent / "data" / "cache" / "cfr"
    
    # Resilience
    MAX_RETRIES = 3
    RETRY_DELAY = 5  # seconds, exponential backoff
    REQUEST_TIMEOUT = 10  # seconds
    RATE_LIMIT_DELAY = 2.0  # between requests
    
    # Data validation
    MIN_GAMES_PLAYED = 1  # Accept partial seasons
    MIN_STAT_FIELDS = 3  # Minimum stats to consider valid
    
    # Matching
    EXACT_MATCH_PRIORITY = True
    FUZZY_MATCH_THRESHOLD = 0.85
    
    # Storage
    CACHE_STRATEGY = "overwrite"  # Always refresh to get latest
    RETENTION_DAYS = 90  # Keep old cached files for reference

class CFRScraperError(Exception):
    """Base exception for CFR scraper errors"""
    
class CFRScraperNetworkError(CFRScraperError):
    """Network-related errors (connection, timeout)"""
    
class CFRScraperDataError(CFRScraperError):
    """Data parsing or validation errors"""
    
class CFRScraperMatchError(CFRScraperError):
    """Prospect matching errors"""
```

### Logging & Monitoring

```python
# Structured logging
logger.info(
    "CFR scrape completed",
    extra={
        'scraped_count': 500,
        'matched_count': 475,
        'unmatched_count': 25,
        'errors': 0,
        'duration_seconds': 1234,
        'timestamp': datetime.utcnow().isoformat(),
    }
)

# Key metrics to log
- Total players processed
- Successful matches
- Unmatched (for manual review)
- Parse errors
- Network errors
- Duration
- Cache hits/misses
```

---

## Database Schema

### New Table: `prospect_college_stats`

```sql
CREATE TABLE prospect_college_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prospect_id UUID NOT NULL,
    
    -- Source & Season Info
    data_source VARCHAR(100) DEFAULT 'cfr.com',
    season INTEGER NOT NULL,
    school VARCHAR(255) NOT NULL,
    class_year VARCHAR(10),  -- e.g., "2026", "Junior", "Senior"
    
    -- Game Information
    games_played INTEGER,
    games_started INTEGER,
    
    -- Shared Stats (All Positions)
    total_touches INTEGER,
    total_yards INTEGER,
    total_touchdowns INTEGER,
    
    -- Offensive Stats (QB/RB/WR/TE)
    passing_attempts INTEGER,
    passing_completions INTEGER,
    passing_yards INTEGER,
    passing_touchdowns INTEGER,
    interceptions INTEGER,
    completion_pct NUMERIC(5, 2),
    qb_rating NUMERIC(5, 2),
    
    rushing_attempts INTEGER,
    rushing_yards INTEGER,
    rushing_touchdowns INTEGER,
    
    receiving_receptions INTEGER,
    receiving_yards INTEGER,
    receiving_touchdowns INTEGER,
    yards_per_reception NUMERIC(5, 2),
    
    -- Defensive Stats (DL/LB/DB)
    tackles INTEGER,
    assisted_tackles INTEGER,
    sacks NUMERIC(5, 2),
    tackles_for_loss INTEGER,
    
    passes_defended INTEGER,
    interceptions_defensive INTEGER,
    forced_fumbles INTEGER,
    fumble_recoveries INTEGER,
    
    -- Offensive Line
    offensive_line_games_started INTEGER,
    all_conference_selections INTEGER,
    
    -- Derived Metrics
    statistical_percentile NUMERIC(5, 2),  -- vs. position peers, same year
    efficiency_rating NUMERIC(5, 2),  -- Custom metric
    
    -- Audit
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    created_by VARCHAR(100) DEFAULT 'system',
    updated_by VARCHAR(100) DEFAULT 'system',
    
    -- Constraints
    FOREIGN KEY (prospect_id) REFERENCES prospects(id) ON DELETE CASCADE,
    UNIQUE(prospect_id, season),
    CHECK(season >= 2000 AND season <= 2030)
);

CREATE INDEX idx_college_stats_prospect_id ON prospect_college_stats(prospect_id);
CREATE INDEX idx_college_stats_season ON prospect_college_stats(season);
CREATE INDEX idx_college_stats_position_season ON prospect_college_stats(season);
```

### Migration

**File:** `migrations/versions/0011_add_prospect_college_stats.py`

```python
"""Add prospect_college_stats table for CFR integration"""

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'prospect_college_stats',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('prospect_id', sa.UUID(), nullable=False),
        # ... columns ...
        sa.ForeignKeyConstraint(['prospect_id'], ['prospects.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('prospect_id', 'season', name='uq_prospect_season'),
        sa.CheckConstraint('season >= 2000 AND season <= 2030', name='ck_valid_season'),
    )
    op.create_index('idx_college_stats_prospect_id', 'prospect_college_stats', ['prospect_id'])
    op.create_index('idx_college_stats_season', 'prospect_college_stats', ['season'])

def downgrade():
    op.drop_index('idx_college_stats_season')
    op.drop_index('idx_college_stats_prospect_id')
    op.drop_table('prospect_college_stats')
```

---

## Pipeline Integration

### Execution Flow

```
Daily Pipeline (3 AM)
├── 1. PFF Scraper (existing)
│   ├── Load PFF cache
│   ├── Parse grades
│   └── Update prospect_grades
├── 2. CFR Scraper (new)
│   ├── Fetch 2026 draft class list
│   ├── For each prospect:
│   │   ├── Scrape player page
│   │   ├── Extract college stats
│   │   ├── Match to prospect_id
│   │   └── Insert/update prospect_college_stats
│   ├── Log unmatched (for manual review)
│   └── Validate data quality
├── 3. Reconciliation (existing)
│   ├── Check for conflicts
│   └── Flag anomalies
└── 4. Quality Monitoring
    ├── Check completeness
    └── Alert if > 5% data quality issues
```

### Error Recovery

```python
class CFRPipelineStage:
    """Integration with main pipeline"""
    
    async def execute(self, session: Session) -> PipelineResult:
        """Execute CFR scraping with fallback strategy"""
        
        try:
            # Attempt fresh scrape
            scraped_data = await self.scraper.scrape_2026_draft_class()
            
            # Validate data quality
            if not self._validate_quality(scraped_data):
                logger.warning("Data quality issues detected, using cache")
                scraped_data = self._load_cache()
            
            # Match and insert
            matches, unmatched = self._match_and_insert(scraped_data, session)
            
            return PipelineResult(
                stage='cfr_scraper',
                status='success',
                records_processed=len(scraped_data),
                records_inserted=matches,
                records_skipped=unmatched,
                errors=[]
            )
            
        except Exception as e:
            logger.error(f"CFR scraper failed: {e}")
            
            # Fallback to yesterday's data
            if self._cache_exists():
                logger.info("Using cached data from previous run")
                # Load and insert cache
                
            return PipelineResult(
                stage='cfr_scraper',
                status='partial',
                error=str(e)
            )
```

---

## API Integration

### New Endpoints

**Get Prospect College Stats**
```
GET /api/prospects/:id/college-stats

Response:
{
  "prospect_id": "uuid",
  "name": "John Doe",
  "position": "QB",
  "school": "Texas A&M",
  "seasons": [
    {
      "year": 2025,
      "games_played": 13,
      "games_started": 13,
      "passing_yards": 4500,
      "passing_tds": 35,
      "interceptions": 8,
      "completion_pct": 67.5,
      "qb_rating": 8.6,
      "rushing_yards": 200,
      "rushing_tds": 3
    },
    {
      "year": 2024,
      ...
    }
  ]
}
```

**Query by College Stats**
```
GET /api/prospects/query?college_yards_min=3000&college_tds_min=25&position=QB

Response:
{
  "count": 12,
  "results": [
    {
      "prospect_id": "uuid",
      "name": "...",
      "position": "QB",
      "college_stats_summary": {
        "best_season_yards": 4500,
        "career_touchdowns": 85,
        "years_played": 3
      },
      "pff_grade": 8.1,
      "match_score": 0.95  // Grade vs production alignment
    }
  ]
}
```

### Query Optimization

```python
# Materialized View for common queries
CREATE MATERIALIZED VIEW vw_prospect_college_summary AS
SELECT
    p.id,
    p.name,
    p.position,
    p.college,
    MAX(pcs.games_played) as career_games,
    SUM(pcs.passing_yards) as career_passing_yards,
    SUM(pcs.passing_touchdowns) as career_passing_tds,
    SUM(pcs.rushing_yards) as career_rushing_yards,
    SUM(pcs.receiving_yards) as career_receiving_yards,
    SUM(pcs.tackles) as career_tackles,
    SUM(pcs.sacks) as career_sacks,
    pg.grade as pff_grade,
    pg.round_projection
FROM prospects p
LEFT JOIN prospect_college_stats pcs ON p.id = pcs.prospect_id
LEFT JOIN prospect_grades pg ON p.id = pg.prospect_id
GROUP BY p.id, p.name, p.position, p.college, pg.grade, pg.round_projection;

CREATE INDEX idx_vw_position ON vw_prospect_college_summary(position);
```

---

## Testing Strategy

### Unit Tests

**File:** `tests/unit/test_cfr_scraper.py`

```python
class TestCFRScraperBasic:
    """Test core scraper functionality"""
    
    def test_scraper_initialization(self):
        """Scraper initializes with correct config"""
        
    def test_rate_limiting(self):
        """Scraper respects rate limit delays"""
        
    def test_session_headers(self):
        """Proper User-Agent and headers set"""

class TestCFRHTMLParsing:
    """Test HTML parsing with fixtures"""
    
    def test_parse_qb_stats(self):
        """Extract QB stats from player page"""
        
    def test_parse_rb_stats(self):
        """Extract RB stats from player page"""
        
    def test_parse_wr_stats(self):
        """Extract WR stats from player page"""
        
    def test_parse_defensive_stats(self):
        """Extract defensive stats"""

class TestCFRProspectMatching:
    """Test prospect matching logic"""
    
    def test_exact_name_match(self):
        """Match exact name + school + position"""
        
    def test_fuzzy_name_match(self):
        """Match via name similarity"""
        
    def test_no_match_returns_none(self):
        """Return None for unmatched prospect"""
        
    def test_case_insensitive_match(self):
        """Matching is case-insensitive"""

class TestCFRDataValidation:
    """Test data validation"""
    
    def test_validate_stat_within_range(self):
        """Reject invalid stat values"""
        
    def test_accept_partial_data(self):
        """Accept records with missing stats"""
        
    def test_validate_year_range(self):
        """Reject invalid years"""
```

### Integration Tests

**File:** `tests/integration/test_cfr_pipeline.py`

```python
class TestCFRPipelineIntegration:
    """Test end-to-end pipeline"""
    
    def test_pipeline_execution(self):
        """Full pipeline runs successfully"""
        
    def test_data_inserted_to_database(self):
        """Scraped data inserted into DB"""
        
    def test_prospect_matching_accuracy(self):
        """95%+ prospects matched correctly"""
        
    def test_no_duplicates_created(self):
        """No duplicate records"""
        
    def test_idempotent_execution(self):
        """Run twice, get same result"""
```

### Fixtures

**File:** `tests/fixtures/cfr_player_page.html`

Sample HTML page for testing parsing logic (cached example)

---

## Performance Considerations

### Scraping Performance

| Task | Est. Time | Optimization |
|------|-----------|---|
| List 2026 draft class | 10s | Cache list, reuse weekly |
| Scrape 500 player pages | 1000s (2s × 500) | Async requests (10 concurrent) |
| Parse all stats | 50s | Parallel processing |
| Match to prospects | 30s | Indexed lookup |
| Insert to DB | 20s | Batch insert (100 at a time) |
| **Total** | **~20 mins** | With optimizations |

### Database Performance

- Insert: Batch 100 records per transaction
- Index on `prospect_id` + `season` for lookups
- Materialized view for analytics queries
- Cache API responses (Redis, 1hr TTL)

---

## Data Quality Metrics

### Monitoring

```python
# Post-scrape validation
validation_metrics = {
    'total_scraped': 500,
    'successfully_matched': 475,  # 95%
    'unmatched': 25,  # 5%
    'parse_errors': 2,
    'duplicate_detection': 0,
    'data_quality_score': 0.98,  # 98% fields non-null
}

# Alert if:
if matched_count / total < 0.90:  # < 90% match rate
    alert("CFR: Low prospect matching rate")
    
if parse_error_rate > 0.05:  # > 5% parse errors
    alert("CFR: High parse error rate, check HTML structure")
    
if data_quality_score < 0.95:  # < 95% completeness
    alert("CFR: Low data completeness")
```

---

## Future Enhancements

1. **Advanced Analytics:**
   - Percentile rankings (position-specific)
   - Efficiency metrics (yards per play, TD rate)
   - Predictive models (college stats → NFL draft position)

2. **UI Integration:**
   - Display college stats in prospect profile
   - Grade vs. production comparison dashboard
   - Position benchmarks view

3. **Historical Archive:**
   - Previous years (2023, 2024) for trend analysis
   - Correlate college stats with actual draft outcomes (2025+)

4. **Advanced Matching:**
   - ML-based name matching (when more data available)
   - Cross-reference with manual review queue

---

## Rollback Plan

If CFR scraper causes issues:

1. **Immediate:** Disable CFR stage in pipeline orchestration
2. **Short-term:** Keep prospect_college_stats data (don't drop table)
3. **Investigate:** Check logs for parse errors or matching issues
4. **Fix & Redeploy:** Once root cause fixed, re-enable
5. **Full Rollback:** Drop prospect_college_stats table only if unrecoverable

**Estimated Recovery:** 30 minutes (disable + verify other stages)

---

## Deployment Checklist

- [ ] CFR scraper code reviewed and approved
- [ ] Unit tests: 100% pass
- [ ] Integration tests: 100% pass
- [ ] Database migration tested on staging
- [ ] API endpoints documented
- [ ] Monitoring alerts configured
- [ ] Rollback plan documented
- [ ] Team trained on new endpoints
- [ ] Documentation updated
- [ ] Deployment to production scheduled (off-peak)

