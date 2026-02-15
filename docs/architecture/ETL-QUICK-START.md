# ETL Architecture: Quick Start for Team

**For:** Engineering team who needs to understand and implement the new architecture  
**Read Time:** 5 minutes  
**Then Read:** The full architecture documents in `docs/architecture/`

---

## What Changed?

**Before:** Data → Parse → Dump to Prospect table  
**After:** Data → Stage → Transform → Load → Track lineage

---

## 3 Key Concepts

### 1. Staging Tables (Raw Data, Never Modified)
```
Each external source gets a staging table:
├─ pff_staging: PFF grades, exactly as received (0-100 scale)
├─ nfl_combine_staging: NFL tests, exactly as received
├─ cfr_staging: CFR college stats, exactly as received
└─ yahoo_staging: Yahoo rankings, exactly as received

Why? Enables re-processing without re-extracting.
If transformation rule changes, re-run transform phase.
Original data frozen = replayable history.
```

### 2. Canonical Tables (Merged, Quality-Checked)
```
Single source of truth:
├─ prospect_core: DEDUPLICATED prospect identity
│  (merged from PFF + NFL + CFR + Yahoo)
│  Example: {id: uuid, pff_id: '123', nfl_combine_id: '456', ...}
├─ prospect_grades: ALL grades from all sources (multi-source)
│  (PFF grade 85, Yahoo grade 78 - both kept)
├─ prospect_measurements: RECONCILED measurements
│  (height from NFL, weight from PFF, with conflict notes)
└─ prospect_college_stats: Position-normalized college stats
   (passing yards, tackles, etc. - only relevant for position)
```

### 3. Lineage Table (Audit Trail)
```
Complete history of every field:
"Where did Alex Johnson's height=74 come from?"

Query lineage:
SELECT source_system, value, changed_at FROM data_lineage
WHERE entity_id = 'uuid-123' AND field_name = 'height_inches';

Result:
├─ source: nfl_combine, value: 74, changed_at: 2026-02-14 03:00
└─ source: pff, value: 73, changed_at: 2026-02-13 03:00 (OVERWROTE)
```

---

## Daily Pipeline Flow (6 Steps)

```
1. EXTRACT (Fetch from sources, parallel)
   PFF.com → pff_raw_data
   NFL.com → nfl_raw_data
   CFR     → cfr_raw_data
   ↓
2. STAGE (Insert raw data, immutable)
   pff_raw_data → INSERT INTO pff_staging
   nfl_raw_data → INSERT INTO nfl_combine_staging
   cfr_raw_data → INSERT INTO cfr_staging
   ↓
3. VALIDATE (Check for garbage data)
   "Is PFF grade between 0-100?" YES
   "Does NFL have height?" YES
   "Skip malformed rows" (log + count)
   ↓
4. TRANSFORM (Cleanse, normalize, match)
   PFF 0-100 grade → normalize to 5.0-10.0
   NFL height "6-2" → parse to 74 inches
   All prospects: match "Alex Johnson" across all sources
   ↓
5. LOAD (Atomic, all-or-nothing)
   INSERT prospect_core (deduplicated)
   INSERT prospect_grades (normalized)
   INSERT prospect_measurements (reconciled)
   Record lineage for every change
   ↓
6. PUBLISH (Refresh analytics)
   REFRESH MATERIALIZED VIEW prospect_quality_scores
   REFRESH MATERIALIZED VIEW position_benchmarks
   Ready for API queries
```

---

## Key Tables (What Goes Where)

### Staging (Raw Data, Exactly as Source Provides)
```sql
-- PFF Staging
pff_staging:
  pff_id (source ID)
  overall_grade (0-100, raw)
  position_grade (0-100, raw)
  film_watched_snaps (sample size)
  raw_json_data (full API response for audit)

-- NFL Combine Staging
nfl_combine_staging:
  nfl_combine_id (source ID)
  height_feet_inches ("6-2", raw format)
  weight_lbs (315)
  forty_yard_dash (4.82)
  raw_json_data (full API response)

-- CFR Staging
cfr_staging:
  cfr_player_id (source ID)
  season (2024)
  passing_yards (3500)
  passing_touchdowns (28)
  raw_html_hash (for integrity)
```

### Canonical (Merged, Normalized)
```sql
-- Prospect Core (Identity Hub)
prospect_core:
  id (UUID)
  name_first, name_last (canonical)
  position, college (canonical)
  pff_id (link to PFF)
  nfl_combine_id (link to NFL)
  cfr_player_id (link to CFR)
  yahoo_id (link to Yahoo)
  data_quality_score (0-1.0, % sources matched)

-- Prospect Grades (Multi-Source)
prospect_grades:
  prospect_id (foreign key)
  source ('pff', 'yahoo', 'espn')
  grade_raw (0-100 or 5-10, as source provides)
  grade_normalized (5.0-10.0, standardized)

-- Prospect Measurements (Reconciled)
prospect_measurements:
  prospect_id (foreign key)
  height_inches (74, from NFL)
  weight_lbs (315, from PFF)
  sources: {height: 'nfl_combine', weight: 'pff'} (tracking)
  conflict_resolution_rule ('most_recent', 'priority_order')

-- Prospect College Stats (Normalized)
prospect_college_stats:
  prospect_id (foreign key)
  season (2024)
  college ('Alabama')
  passing_yards (3500)  # Only for QBs
  tackles (120)         # Only for defense
  # Position-specific fields only populated for relevant position
```

### Lineage (Audit Trail)
```sql
-- Data Lineage (Complete History)
data_lineage:
  entity_id (UUID of prospect)
  field_name ('height_inches', 'grade_normalized')
  value_current (74)
  value_previous (73)
  source_system ('nfl_combine', 'pff')
  source_row_id (123, references nfl_combine_staging.id)
  transformation_rule_id ('nfl_height_parse', 'pff_grade_normalize')
  transformation_logic ('parse "6-2" to 74')
  changed_at (2026-02-14 03:00)
  had_conflict (True/False)
  conflicting_sources {height: [{source: nfl, value: 74}, {source: pff, value: 73}]}
  conflict_resolution_rule ('most_recent')
```

---

## Who Does What?

### Data Engineer (US-056 to US-062)
- Builds scrapers (extract phase)
- Creates transformers (transform phase)
- Integrates into pipeline (orchestration)
- Sets up monitoring

### Backend Engineer (US-058, US-060, US-064)
- Creates database schema (staging + canonical)
- Builds API endpoints (queries canonical models)
- Handles deployment + ops

### Data Analyst (US-061)
- Creates analytical notebooks
- Queries canonical models
- Builds dashboards on lineage data

---

## Common Questions

**Q: Why not just merge everything into Prospect table?**  
A: No audit trail. Can't answer "where did this come from?" Can't reprocess. Doesn't scale.

**Q: Why separate staging from canonical?**  
A: Staging = raw data (frozen), Canonical = quality-checked (can be wrong). If canonical rules change, re-run transform without re-extracting.

**Q: What if PFF says height=73 and NFL says height=74?**  
A: Both recorded in lineage. Conflict resolution rule picks one (e.g., "most_recent" = use 74). Auditable.

**Q: Do we need lineage forever?**  
A: Keep for 90 days, then archive. Use for:
- Debugging data quality issues
- Showing audit trail to compliance
- Reprocessing with new rules

**Q: How many tables will we have?**  
A: Staging (5-10), Canonical (5-10), Lineage (1), Analytics (5-10) = ~30 tables total (manageable)

---

## Example: Adding a New Source (ESPN)

**Before ETL:** Modify Prospect schema, update deduplication logic, debug issues
**After ETL:** Follow this checklist

```
1. Create espn_staging table
   CREATE TABLE espn_staging (
       id SERIAL,
       extraction_id UUID,
       espn_id VARCHAR,
       injury_type VARCHAR,
       injury_date DATE,
       ...
   );

2. Create ESPNTransformer class
   class ESPNTransformer(BaseTransformer):
       async def validate_staging_data(self, row):
           # Validation rules
       async def transform_staging_to_canonical(self, row, prospect_id):
           # Transform logic

3. Register in ETL orchestrator
   self.transformers['espn'] = ESPNTransformer(...)

4. Deploy
   Run daily pipeline, monitor lineage
```

**No schema changes needed.** Same pattern for every source.

---

## Files You Need to Read

1. **Start here:** [ETL-ARCHITECTURE-RATIONALE.md](../docs/ETL-ARCHITECTURE-RATIONALE.md) (30 min)
   - Why we're doing this
   - Concrete example (Alex Johnson prospect)
   - Business rationale

2. **Then read:** [0011-etl-multi-source-architecture.md](../docs/architecture/0011-etl-multi-source-architecture.md) (45 min)
   - Complete technical design
   - Table schemas
   - Transformation rules
   - Pipeline flow

3. **To build it:** [ETL-IMPLEMENTATION-GUIDE.md](../docs/architecture/ETL-IMPLEMENTATION-GUIDE.md) (60 min)
   - Step-by-step code examples
   - Database migrations
   - Python transformer classes
   - Deployment checklist

4. **Quick reference:** This document (5 min)

---

## Implementation Timeline

| Phase | Duration | What | Owner |
|-------|----------|------|-------|
| 1 | 2 weeks | Database + base classes | Data Eng + Backend |
| 2 | 2 weeks | Transformers (PFF, CFR, NFL) | Data Eng |
| 3 | 1 week | Orchestrator + monitoring | Data Eng |
| 4 | Ongoing | Operations + optimization | Team |
| **Total** | **~5 weeks** | **Production ready** | **Team** |

---

## Success Looks Like

```
✅ prospect_core has 2,000+ prospects with data from 2+ sources
✅ Can query lineage: "Show me all transformations for prospect #123"
✅ Pipeline runs daily in ~2 minutes
✅ Can add Yahoo source without schema changes
✅ Data quality dashboard shows confidence by source
✅ Team understands ETL patterns (can apply to other projects)
```

---

## Questions?

1. Architecture questions → See [0011-etl-multi-source-architecture.md](../docs/architecture/0011-etl-multi-source-architecture.md)
2. Implementation questions → See [ETL-IMPLEMENTATION-GUIDE.md](../docs/architecture/ETL-IMPLEMENTATION-GUIDE.md)
3. Business questions → See [ETL-ARCHITECTURE-RATIONALE.md](../docs/ETL-ARCHITECTURE-RATIONALE.md)
4. Meeting questions → Arch sync Tuesday 2 PM

---

**Created:** February 15, 2026  
**Architecture Ready:** ✅ Yes, ready to build  
**Timeline:** 4-5 weeks to production  
**Team:** Assign Data Eng + Backend Eng  
**Next Step:** Schedule architecture review meeting
