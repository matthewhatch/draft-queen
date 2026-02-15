# ETL Architecture Overview: Architect's Perspective

**Date:** February 15, 2026  
**For:** Technical Leadership, Product Team  
**Purpose:** High-level rationale for ETL multi-source architecture

---

## The Problem We're Solving

Currently, the system works as a **monolithic loader**:
```
PFF.com → [Parse] → Prospect table
NFL.com → [Parse] → Prospect table  
CFR     → [Parse] → ProspectStats table
Yahoo   → [Parse] → [Manual review]
```

**Issues:**
1. **No audit trail:** Can't answer "where did this height value come from?"
2. **Brittle matching:** Adding new sources breaks deduplication logic
3. **No conflict resolution:** When PFF says weight=310 and NFL says 315, unclear which wins
4. **Difficult debugging:** Data quality issues hard to trace to source
5. **Non-scalable:** 5+ sources require schema changes per source

---

## The Solution: Enterprise ETL Architecture

**Transform the system into a proper data warehouse:**

```
EXTRACT      STAGE              TRANSFORM          LOAD              PUBLISH
├─ PFF    ──→ pff_staging    ──→ (merge, dedupe, ──→ prospect_core ──→ Materialized
├─ NFL    ──→ nfl_staging    ├─ validate)           → grades          Views
├─ CFR    ──→ cfr_staging    ├─ (normalize)        → measurements   ──→ API
├─ Yahoo  ──→ yahoo_staging  ├─ (resolve conflicts) → college_stats
└─ ESPN   ──→ espn_staging   └─ (track lineage)    └─ (atomic load)
```

**Key Principles:**

### 1. **Staging = Raw Data Capture (Immutable)**
- Each source gets dedicated staging table (exact format from source)
- Never modified after insert, only truncated/replaced
- Enables re-processing without re-extraction

**Example:** PFF staging preserves grade as-is (0-100 scale)
```sql
INSERT INTO pff_staging (pff_id, overall_grade) VALUES ('smith-123', 87.5);
-- Locked in. No modification.
```

### 2. **Canonical = Single Source of Truth (Quality-Checked)**
- Prospect records merged from all sources
- Conflicts resolved by explicit rules (priority order, most recent, etc.)
- All transformations documented

**Example:** If PFF says weight=310, NFL says 315
```sql
INSERT INTO prospect_measurements (prospect_id, weight_lbs, sources, conflict_resolution_rule)
VALUES ('uuid-123', 315, '{"pff": 310, "nfl": 315}', 'most_recent');
```

### 3. **Lineage = Complete Audit Trail**
- Every field change traceable to source and transformation
- Answer questions: "Where did this value come from?" in 1 SQL query
- Enables data quality scorecards per source

**Example:**
```sql
SELECT * FROM data_lineage 
WHERE entity_id = 'uuid-123' AND field_name = 'weight_lbs';

-- Result:
-- source_system=nfl_combine, value=310, changed_at=2026-02-14
-- source_system=pff, value=315, changed_at=2026-02-15 (overwrote due to 'most_recent')
```

---

## Architecture Layers

### Layer 1: Extraction (External Sources)
```
Raw data from APIs/web scraping
- PFF: JSON API responses
- NFL.com: HTML pages
- CFR: HTML pages  
- Yahoo: JSON/HTML
- ESPN: XML feeds (future)
```

### Layer 2: Staging (Raw Data At Rest)
```
Source-specific tables (never normalized)
- pff_staging: 10,000 prospects × grade columns
- nfl_combine_staging: 2,000 combine tests × test result columns
- cfr_staging: 8,000 college stats × stat columns
- yahoo_staging: prospect rankings

Key: Each schema matches source exactly (no interpretation)
```

### Layer 3: Transformation
```
Cleansing & Normalization Rules:
- PFF grade: 0-100 → 5.0-10.0 scale
- NFL height: "6-2" → 74 inches
- CFR stats: Position-specific grouping
- Matching: Fuzzy name match + college + position

Output: Transformation rules tracked in code + lineage DB
```

### Layer 4: Canonical Models (Business Entities)
```
Normalized, deduplicated, validated:
- prospect_core: Master prospect identity
- prospect_grades: Multi-source grades (PFF, ESPN, Yahoo)
- prospect_measurements: Physical tests (combine, pro day)
- prospect_college_stats: Position-normalized college performance

Key: Quality-checked, source-attributed, conflict-resolved
```

### Layer 5: Analytics/API
```
Materialized Views & APIs:
- prospect_quality_scores: Composite evaluation
- position_benchmarks: Statistical aggregates
- prospect_outliers: Anomalies per source
- API endpoints: Query canonical models

Key: Rebuilt nightly from canonical layer
```

---

## Why This Approach?

### For Scalability
Adding new source (e.g., ESPN injury reports):
1. Create `espn_staging` table
2. Create `ESPNTransformer` class
3. Add to orchestrator
4. Deploy

No schema changes to canonical layer. No deduplication logic changes.

### For Data Quality
- **Staging validation:** Catch malformed data early
- **Transformation testing:** Test normalization rules independently  
- **Conflict detection:** Explicit when sources disagree
- **Lineage audit:** Debug quality issues to root cause

### For Operations
- **Reprocessing:** Re-run transformation without re-extracting
- **Rollback:** Can restore previous version from lineage
- **Monitoring:** Health checks per source, per transformation
- **Documentation:** Transformation rules = code = version controlled

### For Analytics
- **Source comparison:** Which source has better data completeness?
- **Trend analysis:** Track data quality improvements over time
- **Model training:** Use lineage to identify reliable features
- **Confidence scores:** Weight confidence by source reliability

---

## Concrete Example: Prospect "Alex Johnson"

### Scenario: Adding CFR (College Stats)

**Before ETL (Current):**
```
PFF: Alex Johnson, QB, Alabama, grade=85
NFL: Alex Johnson, QB, Alabama, height=6'2", weight=210
CFR: [NEW] Alex Johnson, 2024 passing yards=3,500
Yahoo: Alex Johnson rank=#12 QB

Problem: Are these 4 records the same person? How do we know?
Manual deduplication. Brittle. Doesn't scale.
```

**After ETL:**
```
EXTRACTION
├─ PFF extracts: alex-johnson-pff-123
├─ NFL extracts: Johnson, Alex (combine ID nfl-456)
├─ CFR extracts: Alex Johnson (CFR page ID cfr-789)
└─ Yahoo extracts: A. Johnson (yahoo rank #12)

STAGING (Isolated Raw Data)
pff_staging row 1: {pff_id: 'alex-johnson-pff-123', first_name: 'Alex', ...}
nfl_combine_staging row 2: {first_name: 'Alex', last_name: 'Johnson', ...}
cfr_staging row 3: {cfr_player_url: '...', passing_yards: 3500, ...}
yahoo_staging row 4: {yahoo_id: 'a-johnson-rank-12', ...}

TRANSFORMATION
├─ PFFTransformer: Match alex-johnson-pff-123 to prospect_core
├─ NFLTransformer: Fuzzy match (Alex Johnson + Alabama) to same prospect_core
├─ CFRTransformer: Fuzzy match (Alex Johnson + Alabama) to same prospect_core
└─ YahooTransformer: Fuzzy match (A. Johnson) to same prospect_core

CANONICAL (Merged)
prospect_core record:
{
  id: uuid-123,
  name_first: 'Alex',
  name_last: 'Johnson',
  position: 'QB',
  college: 'Alabama',
  pff_id: 'alex-johnson-pff-123',
  nfl_combine_id: 'nfl-456',
  cfr_player_id: 'cfr-789',
  yahoo_id: 'a-johnson-rank-12',
  status: 'active',
  created_from_source: 'pff',
  data_quality_score: 0.95  # Matched across 4 sources
}

prospect_grades: [
  {prospect_id: uuid-123, source: 'pff', grade_normalized: 8.5, ...},
  {prospect_id: uuid-123, source: 'yahoo', grade_normalized: 7.8, ...},
]

prospect_measurements: [
  {prospect_id: uuid-123, height_inches: 74, weight_lbs: 210, 
   sources: {height: 'nfl_combine', weight: 'nfl_combine'}, ...}
]

prospect_college_stats: [
  {prospect_id: uuid-123, season: 2024, passing_yards: 3500, ...}
]

LINEAGE (Audit Trail)
{
  entity_id: uuid-123,
  field_name: 'pff_id',
  value_current: 'alex-johnson-pff-123',
  source_system: 'pff',
  changed_at: 2026-02-14 03:00:00,
  changed_by: 'system',
  transformation_rule_id: 'pff_exact_match',
}
{
  entity_id: uuid-123,
  field_name: 'nfl_combine_id',
  value_current: 'nfl-456',
  source_system: 'nfl_combine',
  changed_at: 2026-02-14 03:05:00,
  changed_by: 'system',
  transformation_rule_id: 'fuzzy_match_name_college_position',
}
```

**Result:**
- ✅ Alex Johnson deduplicated across 4 sources
- ✅ Complete audit trail (who said what, when, how matched)
- ✅ Can answer: "Is this reliable data?" → Check data_quality_score & lineage
- ✅ Can reprocess CFR without re-extracting PFF/NFL

---

## Storage & Performance Trade-offs

### Storage Overhead
- Staging tables: ~100 MB (7-day retention)
- Canonical tables: ~50 MB  
- Lineage table: ~200 MB (complete history)
- **Total:** ~3x raw data size

**Mitigation:** Partition staging table by date, archive after 90 days

### Pipeline Latency
- Extraction: ~30 seconds (parallel)
- Staging: ~10 seconds
- Transformation: ~45 seconds (batch processing)
- Load: ~20 seconds (atomic transaction)
- **Total:** ~2 minutes (vs. 30 seconds for monolithic loader)

**Acceptable for daily batch. Not for real-time.**

### Query Performance
- Canonical tables: Fast (indexed, normalized)
- Lineage queries: Slower (large table, but OLAP queries)
- **Solution:** Separate analytical database if needed (future)

---

## Implementation Roadmap

### Phase 1: Foundation (2 weeks)
- Create staging tables (pff, nfl, cfr, yahoo)
- Create canonical tables (prospect_core, grades, measurements, stats)
- Create lineage audit table
- Build base transformer framework

### Phase 2: Source Transformers (2 weeks)
- Implement PFF transformer (grades)
- Implement CFR transformer (college stats)
- Implement NFL transformer (measurements)
- Conflict resolution logic

### Phase 3: Operations (1-2 weeks)
- ETL orchestrator (APScheduler)
- Data quality monitoring
- Operational dashboards
- Runbooks & documentation

### Phase 4: Optimization (Ongoing)
- Performance tuning (partitioning, indexing)
- Additional sources (ESPN, other)
- Advanced analytics (ML features)

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| **Increased storage** | Partition staging table, archive after 90 days |
| **Pipeline latency** | Parallel extraction, optimize transformations |
| **Transformation bugs** | Comprehensive unit tests, staging/prod validation |
| **Data quality regressions** | Lineage tracking, data quality scorecard alerts |
| **Team skill gap** | ETL training, well-documented code, mentoring |

---

## Success Metrics

1. **Data Quality:** >95% successful deduplication across sources
2. **Auditability:** 100% lineage coverage (every field traceable)
3. **Scalability:** Can add new source in <1 day
4. **Performance:** Pipeline completes <5 minutes
5. **Reliability:** Pipeline success rate >99% (retries)
6. **Operations:** <1 hour MTTR for data quality issues

---

## Related Decisions

- **ADR-0002:** Event-Driven Pipeline (predecessor architecture)
- **ADR-0003:** API Design (how data is consumed)
- **ADR-0004:** Caching Strategy (materialized views)
- **ADR-0010:** PFF Data Source (first source implemented)

---

## Questions for Leadership

1. **Timeline:** Can we dedicate 4-5 weeks for this foundation (vs. quick-and-dirty approach)?
2. **Team:** Do we need to hire ETL specialist or train existing team?
3. **Storage:** Is 3x data storage acceptable? Or should we add data lake layer?
4. **Compliance:** Any regulatory audit requirements for data lineage?
5. **Future:** Should we plan for real-time CDC instead of daily batch?
