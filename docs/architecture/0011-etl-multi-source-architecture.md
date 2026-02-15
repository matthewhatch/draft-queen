# ADR 0011: ETL Multi-Source Data Architecture

**Date:** February 15, 2026  
**Status:** Proposed  
**Architect Decision:** Restructure as ETL tool with source-specific staging tables

---

## Context

Currently, the platform operates as a **single-source pipeline** focused on PFF grades with ad-hoc data ingestion from multiple sources:
- PFF (draft grades)
- NFL.com (combine data)
- College Football Reference (college stats - proposed)
- Yahoo Sports (draft data)
- ESPN (injury reports - future)

**Problems with Current Approach:**
1. **Monolithic loading:** All source data merged into generic tables (Prospect, ProspectStats, etc.)
2. **Data provenance loss:** Can't trace which fields came from which source
3. **Conflicting data:** No clear resolution strategy when sources disagree
4. **Difficult auditing:** Hard to debug data quality issues by source
5. **Limited flexibility:** Adding new sources requires schema changes
6. **Normalization issues:** College stats and combine data lumped together
7. **No staging layers:** Raw data mixed with business logic

**Opportunity:** Implement proper ETL architecture with:
- Source-specific **staging tables** (raw data capture)
- **Transformation rules** per data source
- **Canonical models** (normalized business entities)
- **Data lineage tracking** (audit trail showing source→transform→load)

---

## Decision

**Implement an Enterprise ETL Pipeline with Layered Architecture**

### 1. Physical Data Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    External Data Sources                     │
├─────────────────────────────────────────────────────────────┤
│   PFF.com    │  NFL.com  │   CFR   │  Yahoo  │   ESPN      │
└────┬─────────────┬──────────┬───────┬────────┬────────┘
     │             │          │       │        │
     ▼             ▼          ▼       ▼        ▼
┌─────────────────────────────────────────────────────────────┐
│              STAGING LAYER (Raw Extract)                    │
├─────────────────────────────────────────────────────────────┤
│ • pff_staging              (raw grades, unmatched)          │
│ • nfl_combine_staging      (raw combine data)               │
│ • cfr_staging              (raw college stats)              │
│ • yahoo_staging            (raw draft projections)          │
│ • espn_staging             (raw injury reports)             │
│                                                              │
│ Properties:                                                  │
│ • Immutable: never updated, only truncated/replaced          │
│ • No normalization: exact format from source                │
│ • Timestamp tracked: extraction datetime                    │
│ • Hash tracked: data integrity check                        │
└──────────────┬───────────────────────────────────────────┘
               │
     ┌─────────▼──────────┐
     │  TRANSFORMATION    │
     │     RULES          │
     └─────────┬──────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│         TRANSFORMATION LAYER (Cleansed & Integrated)        │
├─────────────────────────────────────────────────────────────┤
│ • prospect_core         (name, position, college)           │
│ • prospect_grades       (normalized grades from sources)    │
│ • prospect_measurements (combine/pro day data)              │
│ • prospect_college_stats (CFR college statistics)           │
│ • prospect_rankings     (Yahoo/ESPN rankings)               │
│ • data_lineage          (tracks source→transform)           │
│                                                              │
│ Properties:                                                  │
│ • Merged from multiple sources                              │
│ • Quality rules applied (validation, deduplication)         │
│ • Source attribution maintained (which field from where)    │
│ • Slowly changing dimensions tracked (history)              │
└──────────────┬───────────────────────────────────────────┘
               │
     ┌─────────▼──────────┐
     │   BUSINESS RULES   │
     │   & ANALYTICS      │
     └─────────┬──────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│      ANALYTICAL LAYER (Derived Insights & Models)           │
├─────────────────────────────────────────────────────────────┤
│ • prospect_quality_scores  (composite evaluation)           │
│ • position_benchmarks      (statistical aggregates)         │
│ • prospect_outliers        (statistical anomalies)          │
│ • predictive_features      (for ML models)                  │
│ • mvp_candidates           (multi-source decision)          │
│                                                              │
│ Properties:                                                  │
│ • Derived from canonical models                             │
│ • Business logic applied                                    │
│ • Consumable by API and analytics                           │
│ • Rebuilt nightly from source of truth                      │
└─────────────────────────────────────────────────────────────┘
```

### 2. Source-Specific Staging Tables

Each external source has a **dedicated staging table** that captures raw data exactly as received:

#### PFF Staging Table: `pff_staging`

```sql
CREATE TABLE pff_staging (
    id BIGSERIAL PRIMARY KEY,
    extraction_id UUID NOT NULL,           -- Links to pipeline run
    
    -- Raw Data (from PFF JSON response)
    pff_id VARCHAR(50) NOT NULL,
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    position VARCHAR(10),
    college VARCHAR(255),
    draft_year INTEGER,
    
    -- PFF Proprietary Grades
    overall_grade NUMERIC(5, 2),           -- 0-100 scale (raw)
    position_grade NUMERIC(5, 2),          -- Position-specific grade
    trade_grade NUMERIC(5, 2),             -- Expected trade value
    scheme_fit_grade NUMERIC(5, 2),        -- Scheme complexity score
    
    -- PFF Attributes/Measurements (from PFF, not verified)
    height_inches INTEGER,
    weight_lbs INTEGER,
    arm_length_inches NUMERIC(3, 1),
    hand_size_inches NUMERIC(3, 2),
    
    -- PFF Metadata
    film_watched_snaps INTEGER,            -- Sample size for grade
    games_analyzed INTEGER,
    grade_issued_date DATE,
    grade_is_preliminary BOOLEAN,          -- True if in-season
    
    -- Lineage & Quality
    raw_json_data JSONB,                   -- Full source payload for audit
    data_hash VARCHAR(64),                 -- SHA256 hash for integrity check
    extraction_timestamp TIMESTAMP DEFAULT now(),
    extraction_status VARCHAR(50),         -- success, partial, error
    notes TEXT,
    
    -- Constraints
    UNIQUE(pff_id, extraction_id),
    INDEX idx_extraction_id (extraction_id),
    INDEX idx_draft_year (draft_year),
    INDEX idx_position (position)
);
```

#### NFL Combine Staging Table: `nfl_combine_staging`

```sql
CREATE TABLE nfl_combine_staging (
    id BIGSERIAL PRIMARY KEY,
    extraction_id UUID NOT NULL,
    
    -- Prospect Identity (as reported by NFL)
    nfl_combine_id VARCHAR(50),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    position VARCHAR(10),
    college VARCHAR(255),
    
    -- Test Date & Location
    test_date DATE,
    location VARCHAR(100),                 -- Indianapolis, team pro day, etc.
    test_type VARCHAR(50),                 -- combine, pro_day, private
    
    -- Raw Test Results (exact as recorded)
    height_feet_inches VARCHAR(10),        -- "6-2" format (raw)
    weight_lbs NUMERIC(5, 1),
    forty_yard_dash NUMERIC(4, 3),
    ten_yard_split NUMERIC(4, 3),
    twenty_yard_split NUMERIC(4, 3),
    bench_press_reps INTEGER,
    vertical_jump_inches NUMERIC(5, 2),
    broad_jump_inches NUMERIC(5, 2),
    shuttle_run NUMERIC(4, 3),
    three_cone_drill NUMERIC(4, 3),
    sixty_yard_shuttle NUMERIC(4, 3),
    
    -- Position-Specific
    wonderlic_score INTEGER,               -- QB cognition test
    arm_length_inches NUMERIC(3, 1),
    hand_size_inches NUMERIC(3, 2),
    
    -- Data Quality
    raw_json_data JSONB,
    data_hash VARCHAR(64),
    extraction_timestamp TIMESTAMP DEFAULT now(),
    test_invalidated BOOLEAN,              -- Marked by NFL as invalid
    
    UNIQUE(nfl_combine_id, test_date, test_type),
    INDEX idx_extraction_id (extraction_id),
    INDEX idx_test_date (test_date),
    INDEX idx_position (position)
);
```

#### College Football Reference Staging: `cfr_staging`

```sql
CREATE TABLE cfr_staging (
    id BIGSERIAL PRIMARY KEY,
    extraction_id UUID NOT NULL,
    
    -- Prospect Identity (from CFR)
    cfr_player_id VARCHAR(100),
    cfr_player_url VARCHAR(500),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    
    -- College & Position
    college VARCHAR(255),
    position VARCHAR(10),
    recruit_year INTEGER,
    class_year VARCHAR(20),                -- "2026", "Junior", "Senior"
    
    -- Season-Level Stats
    season INTEGER NOT NULL,
    games_played INTEGER,
    games_started INTEGER,
    
    -- Offensive Stats (All Positions)
    passing_attempts INTEGER,
    passing_completions INTEGER,
    passing_yards INTEGER,
    passing_touchdowns INTEGER,
    passing_interceptions INTEGER,
    completion_percentage NUMERIC(5, 2),
    qb_rating NUMERIC(5, 2),
    
    rushing_attempts INTEGER,
    rushing_yards INTEGER,
    rushing_yards_per_attempt NUMERIC(5, 2),
    rushing_touchdowns INTEGER,
    
    receiving_targets INTEGER,
    receiving_receptions INTEGER,
    receiving_yards INTEGER,
    receiving_yards_per_reception NUMERIC(5, 2),
    receiving_touchdowns INTEGER,
    
    -- Defensive Stats
    tackles INTEGER,
    assisted_tackles INTEGER,
    tackles_for_loss NUMERIC(5, 1),
    sacks NUMERIC(5, 1),
    forced_fumbles INTEGER,
    fumble_recoveries INTEGER,
    passes_defended INTEGER,
    interceptions_defensive INTEGER,
    
    -- Offensive Line
    linemen_games_started INTEGER,
    all_conference_selections INTEGER,
    
    -- Data Quality
    raw_html_extracted BYTEA,              -- Original HTML for re-parsing
    data_hash VARCHAR(64),
    extraction_timestamp TIMESTAMP DEFAULT now(),
    parsing_confidence NUMERIC(3, 2),     -- OCR/parsing quality 0-1.0
    
    UNIQUE(cfr_player_id, season),
    INDEX idx_extraction_id (extraction_id),
    INDEX idx_college_season (college, season),
    INDEX idx_position (position)
);
```

#### Yahoo Sports Staging: `yahoo_staging`

```sql
CREATE TABLE yahoo_staging (
    id BIGSERIAL PRIMARY KEY,
    extraction_id UUID NOT NULL,
    
    -- Prospect Identity
    yahoo_id VARCHAR(50),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    position VARCHAR(10),
    college VARCHAR(255),
    
    -- Rankings & Projections
    overall_rank INTEGER,
    position_rank INTEGER,
    round_projection INTEGER,
    team_projection VARCHAR(100),          -- Projected team
    
    -- Analysis
    yahoo_grade NUMERIC(3, 1),             -- 5.0-10.0 scale
    strengths TEXT,
    weaknesses TEXT,
    comps VARCHAR(255),                    -- "comparable player"
    analyst_name VARCHAR(255),
    analysis_date DATE,
    
    -- Metadata
    article_url VARCHAR(500),
    raw_html BYTEA,
    raw_json_data JSONB,
    data_hash VARCHAR(64),
    extraction_timestamp TIMESTAMP DEFAULT now(),
    
    UNIQUE(yahoo_id, extraction_id),
    INDEX idx_extraction_id (extraction_id),
    INDEX idx_position (position)
);
```

### 3. Transformation Layer Canonical Models

After staging, data is **cleaned, validated, and merged** into normalized canonical tables:

#### Core Prospect (Identity Bridge)

```sql
CREATE TABLE prospect_core (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Primary Identity
    name_first VARCHAR(255) NOT NULL,
    name_last VARCHAR(255) NOT NULL,
    position VARCHAR(10) NOT NULL,
    college VARCHAR(255) NOT NULL,
    recruit_year INTEGER,
    
    -- Source Identifiers (Deduplication Keys)
    pff_id VARCHAR(50),
    nfl_combine_id VARCHAR(50),
    cfr_player_id VARCHAR(100),
    yahoo_id VARCHAR(50),
    nfl_com_id VARCHAR(50),
    
    -- Master Status
    status VARCHAR(50),                    -- active, withdrawn, injury, undecided
    is_international BOOLEAN DEFAULT false,
    
    -- Audit & Lineage
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    created_from_source VARCHAR(100),      -- First source to mention prospect
    data_quality_score NUMERIC(3, 2),      -- 0-1.0, based on source coverage
    
    UNIQUE(name_first, name_last, position, college),
    UNIQUE(pff_id),                        -- PFF is authoritative
    INDEX idx_position (position),
    INDEX idx_data_quality (data_quality_score)
);
```

#### Prospect Grades (Multi-Source Normalization)

```sql
CREATE TABLE prospect_grades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prospect_id UUID NOT NULL REFERENCES prospect_core(id),
    
    -- Source Information
    source VARCHAR(100) NOT NULL,          -- pff, espn, nfl, yahoo
    source_system_id VARCHAR(100),         -- ID in source system
    
    -- Grades (Raw)
    grade_raw NUMERIC(5, 2),               -- As reported by source (0-100 or 5-10)
    grade_raw_scale VARCHAR(20),           -- "0-100", "5.0-10.0"
    
    -- Grades (Normalized to 5.0-10.0)
    grade_normalized NUMERIC(3, 1),
    grade_normalized_method VARCHAR(100),  -- Normalization formula used
    
    -- Position-Specific
    position_rated VARCHAR(10),            -- Position at time of grading
    position_grade NUMERIC(5, 2),          -- If source provides position grade
    
    -- Confidence & Metadata
    sample_size INTEGER,                   -- Snaps analyzed, games watched, etc.
    grade_issued_date DATE,
    grade_is_preliminary BOOLEAN,          -- In-season: may change
    analyst_name VARCHAR(255),
    
    -- Lineage
    staged_from_id BIGINT,                 -- Reference to staging table row
    transformation_rules JSONB,            -- Rules applied during normalization
    data_confidence NUMERIC(3, 2),         -- 0-1.0
    
    UNIQUE(prospect_id, source, grade_issued_date),
    INDEX idx_prospect_source (prospect_id, source),
    INDEX idx_source (source),
    INDEX idx_grade_normalized (grade_normalized)
);
```

#### Prospect College Stats (Position-Normalized)

```sql
CREATE TABLE prospect_college_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prospect_id UUID NOT NULL REFERENCES prospect_core(id),
    
    -- Season & Context
    season INTEGER NOT NULL,
    college VARCHAR(255) NOT NULL,
    class_year VARCHAR(20),                -- Junior, Senior, etc.
    
    -- Participation
    games_played INTEGER,
    games_started INTEGER,
    snaps_played INTEGER,
    
    -- Shared Offensive Stats
    total_touches INTEGER,
    total_yards INTEGER,
    total_yards_per_touch NUMERIC(5, 2),
    total_touchdowns INTEGER,
    
    -- QB-Specific
    passing_attempts INTEGER,
    passing_completions INTEGER,
    passing_yards INTEGER,
    passing_touchdowns INTEGER,
    interceptions_thrown INTEGER,
    completion_percentage NUMERIC(5, 2),
    qb_rating NUMERIC(5, 2),
    
    -- Rushing (RB/WR/QB/TE)
    rushing_attempts INTEGER,
    rushing_yards INTEGER,
    rushing_yards_per_attempt NUMERIC(5, 2),
    rushing_touchdowns INTEGER,
    
    -- Receiving (WR/TE/RB/QB)
    receiving_targets INTEGER,
    receiving_receptions INTEGER,
    receiving_yards INTEGER,
    receiving_yards_per_reception NUMERIC(5, 2),
    receiving_touchdowns INTEGER,
    
    -- Defense
    tackles_solo INTEGER,
    tackles_assisted INTEGER,
    tackles_total NUMERIC(5, 1),
    tackles_for_loss NUMERIC(5, 1),
    sacks NUMERIC(5, 1),
    forced_fumbles INTEGER,
    fumble_recoveries INTEGER,
    passes_defended INTEGER,
    interceptions_defensive INTEGER,
    
    -- OL-Specific
    games_started_ol INTEGER,
    all_conference_selections INTEGER,
    
    -- Derived Metrics
    efficiency_rating NUMERIC(5, 2),       -- Position-specific efficiency
    statistical_percentile NUMERIC(5, 2),  -- vs position peers, same year
    production_tier VARCHAR(50),           -- "elite", "high", "average", "low"
    
    -- Lineage & Quality
    data_sources TEXT[],                   -- ['cfr', 'espn_box_score']
    staged_from_id BIGINT,
    transformation_timestamp TIMESTAMP,
    data_completeness NUMERIC(3, 2),       -- 0-1.0, % of expected fields
    
    UNIQUE(prospect_id, season),
    INDEX idx_prospect_season (prospect_id, season),
    INDEX idx_season (season),
    INDEX idx_position_season (season),
    INDEX idx_statistical_percentile (statistical_percentile)
);
```

#### Prospect Measurements (Multi-Source Resolution)

```sql
CREATE TABLE prospect_measurements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prospect_id UUID NOT NULL REFERENCES prospect_core(id),
    
    -- Physical Attributes (Reported)
    height_inches NUMERIC(3, 1),
    weight_lbs NUMERIC(5, 1),
    arm_length_inches NUMERIC(3, 1),
    hand_size_inches NUMERIC(3, 2),
    
    -- Test Results
    forty_yard_dash NUMERIC(4, 3),
    ten_yard_split NUMERIC(4, 3),
    twenty_yard_split NUMERIC(4, 3),
    bench_press_reps INTEGER,
    vertical_jump_inches NUMERIC(5, 2),
    broad_jump_inches NUMERIC(5, 2),
    shuttle_run NUMERIC(4, 3),
    three_cone_drill NUMERIC(4, 3),
    
    -- Test Context
    test_date DATE,
    test_type VARCHAR(50),                 -- combine, pro_day, private
    location VARCHAR(100),
    test_invalidated BOOLEAN,              -- Flag: ignore this test
    
    -- Source Attribution
    sources JSONB,                         -- {height: 'nfl_combine', weight: 'pff', ...}
    source_conflicts JSONB,                -- {weight: [{source: 'nfl', value: 310}, {source: 'pff', value: 315}]}
    resolved_by VARCHAR(100),              -- 'official_combine', 'most_recent', 'manual_review'
    
    -- Data Quality
    measurement_confidence NUMERIC(3, 2),  -- 0-1.0
    
    UNIQUE(prospect_id, test_date, test_type),
    INDEX idx_prospect_id (prospect_id),
    INDEX idx_test_date (test_date)
);
```

### 4. Data Lineage & Audit Trail

**New Table: `data_lineage`** - Tracks complete journey of every field

```sql
CREATE TABLE data_lineage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Entity Being Tracked
    entity_type VARCHAR(50) NOT NULL,      -- prospect_core, prospect_grades, etc.
    entity_id UUID NOT NULL,
    field_name VARCHAR(100) NOT NULL,      -- e.g., 'height_inches'
    
    -- Value History
    value_current TEXT,
    value_previous TEXT,
    value_is_null BOOLEAN,
    
    -- Source & Transformation
    extraction_id UUID,                    -- Reference to pipeline run
    source_table VARCHAR(100),             -- staging table it came from
    source_row_id BIGINT,                  -- Row in staging table
    source_system VARCHAR(50),             -- pff, nfl_combine, cfr, etc.
    
    -- Transformation Applied
    transformation_rule_id VARCHAR(100),   -- Reference to transformation rule
    transformation_logic TEXT,             -- SQL/python code applied
    transformation_is_automated BOOLEAN,
    
    -- Conflict Resolution (when multiple sources provide same field)
    had_conflict BOOLEAN,
    conflicting_sources JSONB,             -- {pff: value1, cfr: value2}
    conflict_resolution_rule VARCHAR(100), -- priority_order, most_recent, etc.
    
    -- Audit & Accountability
    changed_at TIMESTAMP,
    changed_by VARCHAR(100),               -- User or 'system'
    change_reason TEXT,                    -- Manual override reason, if any
    change_reviewed_by VARCHAR(100),
    
    INDEX idx_entity (entity_type, entity_id),
    INDEX idx_source_system (source_system),
    INDEX idx_changed_at (changed_at)
);
```

### 5. ETL Pipeline Orchestration

**Daily Pipeline Flow:**

```python
# src/data_pipeline/orchestration/etl_pipeline.py

class MultiSourceETLPipeline:
    """
    Enterprise ETL pipeline managing multiple data sources.
    
    Daily flow (3 AM):
    1. Extract → 2. Validate → 3. Stage → 4. Transform → 5. Load → 6. Publish
    """
    
    async def run_daily_pipeline(self) -> PipelineResult:
        """Main orchestration method"""
        
        pipeline_run_id = uuid.uuid4()
        
        # =============== EXTRACT PHASE ===============
        self.logger.info(f"[{pipeline_run_id}] Starting extraction phase")
        
        # Extract from each source concurrently
        extractions = await asyncio.gather(
            self._extract_pff(pipeline_run_id),
            self._extract_nfl_combine(pipeline_run_id),
            self._extract_cfr(pipeline_run_id),
            self._extract_yahoo(pipeline_run_id),
        )
        
        # =============== STAGE PHASE ===============
        self.logger.info(f"[{pipeline_run_id}] Starting staging phase")
        
        for source_name, raw_data in extractions:
            staging_table = self._get_staging_table(source_name)
            await staging_table.insert_raw(
                data=raw_data,
                extraction_id=pipeline_run_id,
                extraction_timestamp=datetime.utcnow(),
                data_hash=self._compute_hash(raw_data),
            )
        
        # =============== VALIDATE PHASE ===============
        self.logger.info(f"[{pipeline_run_id}] Starting validation phase")
        
        validation_results = {}
        for source in ['pff', 'nfl_combine', 'cfr', 'yahoo']:
            validation_results[source] = await self._validate_staged_data(
                source, pipeline_run_id
            )
        
        # =============== TRANSFORM PHASE ===============
        self.logger.info(f"[{pipeline_run_id}] Starting transformation phase")
        
        # Transform each source into canonical models
        canonical_data = {
            'prospects': {},      # Merged identity
            'grades': [],         # All grades (multi-source)
            'measurements': {},   # Reconciled measurements
            'college_stats': {},  # Position-normalized college stats
        }
        
        for source in ['pff', 'nfl_combine', 'cfr', 'yahoo']:
            source_canonical = await self._transform_source_to_canonical(
                source, pipeline_run_id
            )
            self._merge_into_canonical(canonical_data, source_canonical)
        
        # =============== MERGE PHASE ===============
        self.logger.info(f"[{pipeline_run_id}] Starting merge phase")
        
        # Deduplicate prospects across sources
        merged_prospects = await self._deduplicate_prospects(
            canonical_data['prospects'],
            pipeline_run_id
        )
        
        # Resolve conflicts (when sources disagree)
        resolved_data = await self._resolve_source_conflicts(
            canonical_data, pipeline_run_id
        )
        
        # =============== LOAD PHASE ===============
        self.logger.info(f"[{pipeline_run_id}] Starting load phase")
        
        async with self.db.transaction() as tx:
            # Load in order: prospects → everything else
            await self._load_prospects(resolved_data['prospects'], tx)
            await self._load_grades(resolved_data['grades'], tx)
            await self._load_measurements(resolved_data['measurements'], tx)
            await self._load_college_stats(resolved_data['college_stats'], tx)
            
            # Record lineage for every field changed
            await self._record_lineage(pipeline_run_id, resolved_data, tx)
        
        # =============== PUBLISH PHASE ===============
        self.logger.info(f"[{pipeline_run_id}] Starting publish phase")
        
        # Refresh materialized views
        await self._refresh_analytics_views()
        
        # Publish metrics
        await self._publish_pipeline_metrics(pipeline_run_id, validation_results)
        
        return PipelineResult(
            pipeline_run_id=pipeline_run_id,
            status='success',
            prospects_loaded=len(resolved_data['prospects']),
            grades_loaded=len(resolved_data['grades']),
            validation_results=validation_results,
        )
```

### 6. Transformation Rules (Example: PFF → Canonical)

```python
# src/data_pipeline/transformations/pff_transformer.py

class PFFTransformer:
    """
    Transforms raw PFF staging data into canonical models.
    
    Handles:
    - Grade normalization (0-100 → 5.0-10.0)
    - Prospect matching (PFF ID → prospect_core ID)
    - Data validation
    - Lineage tracking
    """
    
    GRADE_NORMALIZATION_RULES = {
        'linear': lambda raw: 5.0 + (raw / 100.0 * 5.0),
        'curve': lambda raw: self._normalize_curved(raw),  # Better distribution
    }
    
    async def transform(self, staging_row: dict) -> CanonicalProspect:
        """Transform single PFF staging row"""
        
        # Step 1: Match to prospect_core
        prospect_id = await self._match_prospect(staging_row)
        if not prospect_id:
            prospect_id = await self._create_new_prospect(staging_row)
        
        # Step 2: Create grade record
        grade = ProspectGrade(
            prospect_id=prospect_id,
            source='pff',
            source_system_id=staging_row['pff_id'],
            grade_raw=staging_row['overall_grade'],
            grade_raw_scale='0-100',
            grade_normalized=self.GRADE_NORMALIZATION_RULES['curve'](
                staging_row['overall_grade']
            ),
            sample_size=staging_row['film_watched_snaps'],
            grade_issued_date=staging_row['grade_issued_date'],
            transformation_rules={
                'normalization_method': 'curve',
                'outlier_check': True,
            },
        )
        
        # Step 3: Lineage tracking
        await self._record_grade_lineage(grade, staging_row)
        
        return CanonicalProspect(
            prospect_id=prospect_id,
            grades=[grade],
        )
```

---

## Consequences

### Positive

1. **Clear Data Provenance:** Every field traces back to source, transformation rules, and decision logic
2. **Source Independence:** Adding new source doesn't require schema changes; just new staging table + transformer
3. **Auditability:** Complete audit trail shows what changed, when, why, and by whom
4. **Conflict Resolution:** When sources disagree (e.g., different heights), decision rules are explicit
5. **Data Quality:** Staging layer isolates bad data; canonical layer quality-checked
6. **Operational Flexibility:** Can reprocess data through different transformation rules without re-extracting
7. **Analytics Foundation:** Lineage data enables "data quality scorecards" per source
8. **Debugging:** Easy to find root cause: "weight came from PFF, which came from X PDF"

### Negative

1. **Storage Overhead:** Staging + canonical + lineage = ~3x raw data volume
2. **Transformation Complexity:** Multiple transformations, merge logic adds code complexity
3. **Pipeline Latency:** More transformation steps = slower daily pipeline (mitigate with parallel processing)
4. **Operational Load:** More tables to monitor, more potential failure points
5. **Skill Requirements:** Team needs SQL + ETL expertise (not just CRUD)

### Mitigation Strategies

- Use PostgreSQL partitioning to manage storage (archive old staging after 90 days)
- Build transformation framework to standardize rules (reduce bespoke code)
- Implement parallel extraction to minimize pipeline duration
- Deploy comprehensive monitoring (staging data quality, transformation errors)
- Document transformation rules as code + wiki

---

## Architecture Patterns Used

### 1. **Staging Area Pattern**
Raw data lands unchanged → Transformation rules applied in controlled way

### 2. **Slowly Changing Dimensions (SCD Type 2)**
Track prospect attributes over time (height changes, grades issued)

```sql
SELECT p.name, s.season, cs.passing_yards 
FROM prospect_core p
JOIN prospect_college_stats cs ON p.id = cs.prospect_id
WHERE p.id = '...' AND cs.season BETWEEN 2024 AND 2025;
```

### 3. **Data Vault Architecture (Simplified)**
- **Hubs:** prospect_core (identity center)
- **Links:** data_lineage (relationships)
- **Sats:** prospect_grades, prospect_measurements (attributes)

### 4. **Change Data Capture (CDC)**
Lineage table functions as CDC log → enables incremental reprocessing

---

## Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
- [ ] Create staging tables (pff, nfl, cfr, yahoo)
- [ ] Create canonical tables (prospect_core, prospect_grades, etc.)
- [ ] Create data_lineage audit table
- [ ] Build basic transformers (PFF, NFL Combine)

### Phase 2: Integration (Week 3-4)
- [ ] Build CFR transformer (college stats)
- [ ] Build conflict resolution logic (multi-source reconciliation)
- [ ] Build deduplication logic (prospect matching)
- [ ] Implement parallel extraction

### Phase 3: Operations (Week 5+)
- [ ] Deploy ETL orchestrator (APScheduler)
- [ ] Build data quality monitoring (staging layer validation)
- [ ] Create operational dashboards (lineage, conflicts, errors)
- [ ] Document transformation rules + runbooks

---

## Alternative Approaches Considered

### 1. No Staging Layer (Current State)
- **Pros:** Simpler, fewer tables
- **Cons:** Can't debug, can't reprocess, data loss on failures
- **Rejected:** Unacceptable for enterprise data quality

### 2. Single Universal Staging Table
- **Pros:** Fewer tables
- **Cons:** Mixing incompatible schemas (PFF grades != combine tests)
- **Rejected:** Too much complexity in transform layer

### 3. Event-Driven (Kafka/Event Streams)
- **Pros:** Real-time, scalable
- **Cons:** Sources don't provide events; still batch polling
- **Rejected:** Over-engineering for current data refresh frequency (daily)

---

## Related Decisions

- **ADR-0002:** Event-Driven Pipeline (historical context)
- **ADR-0003:** API Design (how data is queried)
- **ADR-0004:** Caching Strategy (materialized views)
- **ADR-0010:** PFF Data Source (first data source)

---

## Questions for Review

1. **Storage:** Will 3x storage overhead become issue? Should we archive staging older than 90 days?
2. **Team:** Do we need to hire data engineer with ETL expertise, or can backend team learn?
3. **Rollout:** Should we implement this for all sources at once, or start with CFR + PFF?
4. **Monitoring:** What's acceptable error rate for data quality? Who monitors?
5. **Compliance:** Any audit/regulatory requirements for data lineage in sports context?
