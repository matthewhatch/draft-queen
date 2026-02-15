# ETL Architecture: Visual Reference

**Purpose:** High-level diagrams showing data flow, schema relationships, and transformation logic

---

## 1. Complete Data Flow Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│                        EXTERNAL DATA SOURCES                               │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  PFF.com    │  NFL.com   │  CFR.com   │  Yahoo   │  ESPN    │  Future    │
│  (Grades)   │ (Combine)  │ (College)  │(Rankings)│(Injuries)│  (?)       │
└────┬─────────┬──────────┬────────────┬────────┬────────┬──────────┘
     │         │          │            │        │        │
     ▼         ▼          ▼            ▼        ▼        ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                    EXTRACTION LAYER (Async Parallel)                       │
├────────────────────────────────────────────────────────────────────────────┤
│  • Fetch latest data from each source                                      │
│  • Handle rate limiting, retries, timeouts                                 │
│  • Cache results for debugging                                             │
│  Duration: ~30 seconds (parallel)                                          │
└────┬─────────┬──────────┬────────────┬────────┬────────────────┘
     │         │          │            │        │
     ▼         ▼          ▼            ▼        ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                    STAGING LAYER (Raw Data, Immutable)                    │
├────────────────────────────────────────────────────────────────────────────┤
│  pff_staging:        │  nfl_combine_staging:  │  cfr_staging:            │
│  • grade 0-100       │  • height "6-2"        │  • passing_yards         │
│  • position_grade    │  • weight 310          │  • games_played          │
│  • snaps_analyzed    │  • forty_time 4.82     │  • season 2024           │
│                      │  • etc.                │  • etc.                  │
│                      │                        │                          │
│  yahoo_staging:      │  espn_staging:                                    │
│  • ranking #12       │  • injury_type ACL                                │
│  • analyst_grade     │  • recovery_date                                  │
│  • etc.              │  • etc.                                           │
│                      │                                                    │
│  IMMUTABLE: Never updated. Data hash tracked. Full JSON/HTML preserved.   │
└────┬─────────┬──────────┬────────────┬────────┬─────────────────┘
     │         │          │            │        │
     │ extraction_id, timestamp, hash
     │
     ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                 VALIDATION LAYER (Quality Checks)                          │
├────────────────────────────────────────────────────────────────────────────┤
│  • PFF: grade must be 0-100 ✓                                              │
│  • NFL: height must be parseable ✓                                         │
│  • CFR: season must be 2020-2025 ✓                                         │
│  • Yahoo: ranking must be numeric ✓                                        │
│                                                                              │
│  Skip rows that fail validation (logged + counted)                         │
└────┬─────────┬──────────┬────────────┬────────┬──────────────┘
     │         │          │            │        │
     ▼         ▼          ▼            ▼        ▼
┌────────────────────────────────────────────────────────────────────────────┐
│             TRANSFORMATION LAYER (Cleanse & Normalize)                    │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  PFF Transformer              NFL Transformer         CFR Transformer      │
│  • Grade: 0-100 →             • Height: "6-2" →       • Stat validation    │
│    5.0-10.0 scale               74 inches            (position-specific)   │
│  • Match prospect              • Weight parsing        • Match prospect     │
│    (PFF ID priority)           • Combine date parse    (fuzzy name match)   │
│  • Lineage track               • Match prospect        • Lineage track      │
│                                  (fuzzy match)         (source attribution) │
│                                • Lineage track                             │
│                                                                              │
│  All: Prospective ID extraction for deduplication                         │
└────┬──────────┬────────────┬─────────────────────┬──────────────────────┘
     │          │            │                     │
     └──────────┼────────────┼─────────────────────┘
                │            │
                ▼            ▼
┌────────────────────────────────────────────────────────────────────────────┐
│              MERGE LAYER (Deduplication & Conflict Resolution)             │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Input: Transformed data from 5 sources, each with prospect identity      │
│                                                                              │
│  Process:                                                                   │
│  1. Group by prospect identity (name + college + position + draft year)  │
│  2. For each group, link to same prospect_core record                    │
│  3. When fields conflict:                                                │
│     - PFF grade=85, Yahoo grade=78 → keep both (no conflict)            │
│     - Height=74 (NFL), Height=73 (PFF) → use most_recent=74             │
│     - Track conflict resolution in lineage                              │
│                                                                              │
│  Output: prospect_core with master identity + source IDs                 │
└────┬───────────────────────────────────────────────────────────────────┘
     │
     ▼
┌────────────────────────────────────────────────────────────────────────────┐
│         LOAD LAYER (Atomic Transaction, All-or-Nothing)                   │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  BEGIN TRANSACTION                                                          │
│  ├─ INSERT/UPDATE prospect_core                                           │
│  │  {id, name, position, college, pff_id, nfl_id, cfr_id, yahoo_id}      │
│  │                                                                         │
│  ├─ INSERT/UPDATE prospect_grades                                         │
│  │  {prospect_id, source, grade_raw, grade_normalized, ...}               │
│  │                                                                         │
│  ├─ INSERT/UPDATE prospect_measurements                                   │
│  │  {prospect_id, height, weight, forty_time, sources, conflicts}         │
│  │                                                                         │
│  ├─ INSERT/UPDATE prospect_college_stats                                  │
│  │  {prospect_id, season, passing_yards, tackles, ...}                    │
│  │                                                                         │
│  ├─ INSERT data_lineage (every field change)                              │
│  │  {entity_id, field, value_old, value_new, source, transform_rule}     │
│  │                                                                         │
│  COMMIT (all succeed or all rollback)                                     │
│                                                                              │
└────┬───────────────────────────────────────────────────────────────────┘
     │
     ▼
┌────────────────────────────────────────────────────────────────────────────┐
│              PUBLISH LAYER (Analytics & API Ready)                         │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  REFRESH MATERIALIZED VIEWS:                                              │
│  • prospect_quality_scores                                                │
│  • position_benchmarks                                                    │
│  • prospect_outliers                                                      │
│                                                                              │
│  NOTIFY:                                                                   │
│  • API servers (data ready)                                               │
│  • Monitoring (pipeline success)                                          │
│  • Teams (summary metrics)                                                │
│                                                                              │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Prospect Deduplication Example

```
INPUT (After Transformation)
════════════════════════════════════════════════════════════════

From PFF:
  pff_id: "alex-johnson-123"
  first_name: "Alex"
  last_name: "Johnson"
  position: "QB"
  college: "Alabama"
  overall_grade: 87.5

From NFL Combine:
  nfl_combine_id: "nfl-456"
  first_name: "Alexander"
  last_name: "Johnson"
  position: "QB"
  college: "Alabama"
  height: "6-2"
  weight: 210

From CFR:
  cfr_player_id: "cfr-789"
  first_name: "Alex"
  last_name: "Johnson"
  position: "QB"
  college: "Alabama"
  passing_yards: 3500

Matching Algorithm
════════════════════════════════════════════════════════════════

1. Extract identity from each source:
   PFF:    (Alex + Johnson + QB + Alabama)
   NFL:    (Alexander + Johnson + QB + Alabama)
   CFR:    (Alex + Johnson + QB + Alabama)

2. Fuzzy match (threshold 85%):
   PFF vs NFL:    "Alex Johnson" vs "Alexander Johnson" = 92% match ✓
   PFF vs CFR:    "Alex Johnson" vs "Alex Johnson" = 100% match ✓
   NFL vs CFR:    "Alexander Johnson" vs "Alex Johnson" = 92% match ✓
   College match: Alabama = Alabama = Alabama ✓
   Position:      QB = QB = QB ✓
   → SAME PERSON

3. Resolve to single prospect_core:

   CREATE prospect_core:
     id: uuid-123
     name_first: "Alex"          (PFF + CFR preferred over NFL)
     name_last: "Johnson"
     position: "QB"
     college: "Alabama"
     pff_id: "alex-johnson-123"  ← Link to PFF
     nfl_combine_id: "nfl-456"   ← Link to NFL
     cfr_player_id: "cfr-789"    ← Link to CFR
     yahoo_id: null
     data_quality_score: 0.95    (matched across 3 sources)

4. Insert source-specific data:

   CREATE prospect_grades:
     prospect_id: uuid-123
     source: "pff"
     grade_raw: 87.5
     grade_normalized: 9.4

   CREATE prospect_measurements:
     prospect_id: uuid-123
     height_inches: 74           (from NFL)
     weight_lbs: 210             (from NFL)
     sources: {height: "nfl", weight: "nfl"}
     forty_time: null

   CREATE prospect_college_stats:
     prospect_id: uuid-123
     season: 2024
     college: "Alabama"
     passing_yards: 3500         (from CFR)
     games_played: 12
     touchdowns: 28

5. Record lineage (every field):

   data_lineage:
     entity_id: uuid-123
     field_name: "pff_id"
     source_system: "pff"
     value_current: "alex-johnson-123"
     transformation_rule_id: "pff_source_id_extract"
     changed_at: 2026-02-14 03:10:00

   data_lineage:
     entity_id: uuid-123
     field_name: "height_inches"
     source_system: "nfl_combine"
     value_current: 74
     source_row_id: 456 (reference to nfl_combine_staging)
     transformation_rule_id: "nfl_height_parse"
     transformation_logic: 'parse "6-2" to 74'
     changed_at: 2026-02-14 03:15:00

OUTPUT
════════════════════════════════════════════════════════════════

prospect_core: 1 record (deduplicated)
prospect_grades: 1 record (PFF)
prospect_measurements: 1 record (NFL)
prospect_college_stats: 1 record (CFR)
data_lineage: 4+ records (every field)

Query: "Where did Alex Johnson's height come from?"
Answer: SELECT * FROM data_lineage 
        WHERE entity_id = 'uuid-123' AND field_name = 'height_inches'
Result: NFL Combine, value: 74, date: 2026-02-14 03:15
```

---

## 3. Table Relationships Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                      STAGING LAYER                               │
├──────────────────────────────────────────────────────────────────┤
│  pff_staging (raw)     │ nfl_staging (raw)    │ cfr_staging (raw) │
│  ├─ id (PK)            │ ├─ id (PK)           │ ├─ id (PK)        │
│  ├─ pff_id             │ ├─ nfl_id            │ ├─ cfr_player_id  │
│  ├─ overall_grade      │ ├─ height            │ ├─ passing_yards  │
│  ├─ position           │ ├─ position          │ ├─ position       │
│  └─ raw_json_data      │ └─ raw_json_data     │ └─ raw_html_data  │
└──────────────────┬─────┴─────────────┬────────┴──────────┬─────────┘
                   │                   │                  │
                   └───────────────────┼──────────────────┘
                                       │
                        ┌──────────────▼──────────────┐
                        │   TRANSFORMATION LAYER     │
                        │   (Validators & Mappers)   │
                        └──────────────┬──────────────┘
                                       │
                ┌──────────────────────┼──────────────────────┐
                │                      │                      │
                ▼                      ▼                      ▼
┌──────────────────────┐   ┌──────────────────────┐   ┌──────────────────────┐
│  CANONICAL LAYER     │   │  CANONICAL LAYER     │   │  CANONICAL LAYER     │
├──────────────────────┤   ├──────────────────────┤   ├──────────────────────┤
│  prospect_core       │   │ prospect_grades      │   │prospect_measurements │
│  (Identity Hub)      │   │ (Multi-Source)       │   │ (Reconciled)         │
│  ├─ id (PK)          │   │ ├─ id (PK)           │   │ ├─ id (PK)           │
│  ├─ name_first       │   │ ├─ prospect_id ──────┼──→│ ├─ prospect_id ──────┼──┐
│  ├─ name_last        │   │ │  (FK) ──────┐     │   │ │  (FK) ──────┐     │  │
│  ├─ pff_id           │   │ ├─ source     │     │   │ ├─ height     │     │  │
│  ├─ nfl_id           │   │ ├─ grade_raw  │     │   │ ├─ weight     │     │  │
│  ├─ cfr_id           │   │ ├─ grade_norm │     │   │ ├─ sources    │     │  │
│  └─ yahoo_id         │   │ └─ sample_size│     │   │ └─ conflicts  │     │  │
│                      │   └──────────────────────┘   └──────────────────────┘  │
│                      │                                                         │
│                      └─────────────────────────────────────────────────────────┘
│
│  ┌──────────────────────────────────────────────────────────────────────┐
│  │  prospect_college_stats (Position-Normalized)                       │
│  │  ├─ id (PK)                                                          │
│  │  ├─ prospect_id (FK) ───┐                                            │
│  │  ├─ season              │                                            │
│  │  ├─ passing_yards       │                                            │
│  │  ├─ tackles             │                                            │
│  │  └─ data_sources []     │                                            │
│  └───────────────────┬──────────────────────────────────────────────────┘
│                      │
└──────────────────────┼────────────────────────────────────────────────────┐
                       │                                                    │
        ┌──────────────▼────────────────┐                                  │
        │     AUDIT LAYER              │                                  │
        ├──────────────────────────────┤                                  │
        │ data_lineage                 │                                  │
        │ (Complete Audit Trail)       │                                  │
        │ ├─ id (PK)                   │                                  │
        │ ├─ entity_id (FK) ───────────┼──────────────────────────────────┘
        │ ├─ field_name                │
        │ ├─ value_current             │
        │ ├─ value_previous            │
        │ ├─ source_system             │
        │ ├─ transformation_rule_id    │
        │ ├─ had_conflict              │
        │ ├─ conflict_resolution_rule  │
        │ └─ changed_at                │
        └──────────────────────────────┘
```

---

## 4. Conflict Resolution Flow

```
When Multiple Sources Provide Same Field
═════════════════════════════════════════════════════════════

Input: PFF height=73, NFL height=74

1. Both recorded:
   INSERT prospect_measurements 
   (prospect_id, height_inches, sources, conflicting_sources)
   VALUES (uuid-123, ?, 
           {height: 'nfl'}, 
           {height: [{source: 'pff', value: 73}, 
                     {source: 'nfl', value: 74}]})

2. Apply conflict resolution rule:
   
   RULE: most_recent
   ├─ NFL: changed_at 2026-02-14 03:20
   ├─ PFF: changed_at 2026-02-14 03:10
   └─ Winner: NFL (more recent) = 74

   OR

   RULE: priority_order
   ├─ Priority: [nfl, pff, cfr]
   └─ Winner: NFL (highest priority) = 74

   OR

   RULE: data_quality_score
   ├─ NFL data_quality: 0.98
   ├─ PFF data_quality: 0.95
   └─ Winner: NFL (higher quality) = 74

3. Record lineage:
   INSERT data_lineage (
     entity_id: uuid-123,
     field_name: 'height_inches',
     value_current: 74,
     value_previous: 73,
     source_system: 'nfl_combine',
     had_conflict: true,
     conflicting_sources: {
       height: [
         {source: 'pff', value: 73},
         {source: 'nfl', value: 74}
       ]
     },
     conflict_resolution_rule: 'most_recent'
   )

4. Result:
   ✓ Conflict recorded
   ✓ Decision documented
   ✓ Auditable (can change rule, reprocess)
```

---

## 5. Pipeline Execution Timeline

```
Daily ETL Pipeline (Runs 3:00 AM UTC)
════════════════════════════════════════════════════════════════

3:00 AM
├─ START Pipeline (run_id: uuid-abc123)
│
├─ EXTRACT Phase (parallel, ~30s)
│  ├─ Task: PFF.extract()  ⧗━━━━━━━━━━━━ 15s
│  ├─ Task: NFL.extract()  ⧗━━━━━━━━━━━━━━ 20s
│  ├─ Task: CFR.extract()  ⧗━━━━━━━━━━━━━━━ 25s
│  ├─ Task: Yahoo.extract()  ⧗━━━━━ 8s
│  └─ DONE (max of all = 25s)
│
├─ VALIDATE Phase (~10s)
│  ├─ Validate PFF data (50 validation rules)
│  ├─ Validate NFL data (30 validation rules)
│  ├─ Validate CFR data (25 validation rules)
│  └─ Log failures: 3 rows skipped (0.05% error rate)
│
├─ TRANSFORM Phase (~45s)
│  ├─ PFFTransformer.process_batch(500 rows)  ⧗━━━━━ 12s
│  ├─ NFLTransformer.process_batch(200 rows)  ⧗━━━━ 10s
│  ├─ CFRTransformer.process_batch(800 rows)  ⧗━━━━━━ 15s
│  ├─ YahooTransformer.process_batch(150 rows)  ⧗━ 3s
│  └─ MERGE + DEDUPLICATE  ⧗━━━ 5s
│
├─ LOAD Phase (~20s)
│  ├─ BEGIN TRANSACTION
│  ├─ INSERT prospect_core (2,000 upserts)  ⧗━ 5s
│  ├─ INSERT prospect_grades (2,300 inserts)  ⧗━ 3s
│  ├─ INSERT prospect_measurements (1,800 inserts)  ⧗━ 4s
│  ├─ INSERT prospect_college_stats (1,500 inserts)  ⧗━ 3s
│  ├─ INSERT data_lineage (8,000 inserts)  ⧗━━ 4s
│  └─ COMMIT
│
├─ PUBLISH Phase (~10s)
│  ├─ REFRESH MATERIALIZED VIEW prospect_quality_scores  ⧗━ 3s
│  ├─ REFRESH MATERIALIZED VIEW position_benchmarks  ⧗━ 4s
│  └─ Notify API + monitoring
│
├─ METRICS LOGGED
│  ├─ Prospects loaded: 2,000
│  ├─ Grades loaded: 2,300
│  ├─ Conflicts detected: 45 (resolved automatically)
│  ├─ Validation failures: 3 (0.05%)
│  └─ Duration: 2:20 (2 min 20 sec)
│
└─ COMPLETE (Success) ✓ 3:02 AM

Pipeline Timeline Summary
────────────────────────────────────────────────────────────
Extract:       30 sec ▮▮▮▮▮
Validate:      10 sec ▮▮
Transform:     45 sec ▮▮▮▮▮▮▮▮▮
Load:          20 sec ▮▮▮▮
Publish:       10 sec ▮▮
────────────────────────────────────────────────────────────
Total:        115 sec (1:55) ~2 minutes
```

---

## 6. Data Quality Dashboard Queries

```
Question 1: Data Completeness by Source
════════════════════════════════════════════════════════════════

SELECT 
  source_system,
  COUNT(*) as records_processed,
  COUNT(CASE WHEN field_name IN ('grade_normalized', 'passing_yards') THEN 1 END) 
    as key_fields_present,
  ROUND(100.0 * COUNT(CASE WHEN field_name IN ('grade_normalized', 'passing_yards') THEN 1 END) 
        / COUNT(*), 2) as completeness_pct
FROM data_lineage
WHERE changed_at > now() - interval '1 day'
GROUP BY source_system;

Example Output:
┌────────────┬─────────────┬──────────────────┬──────────────────┐
│ source     │ records     │ key_fields       │ completeness_pct │
├────────────┼─────────────┼──────────────────┼──────────────────┤
│ pff        │ 2,000       │ 1,987            │ 99.35            │
│ nfl        │ 1,800       │ 1,710            │ 95.00            │
│ cfr        │ 1,500       │ 1,485            │ 99.00            │
│ yahoo      │ 500         │ 420              │ 84.00            │
└────────────┴─────────────┴──────────────────┴──────────────────┘

Question 2: Conflict Detection
════════════════════════════════════════════════════════════════

SELECT 
  field_name,
  COUNT(*) as conflict_count,
  array_agg(DISTINCT source_system) as involved_sources
FROM data_lineage
WHERE had_conflict = true 
  AND changed_at > now() - interval '1 day'
GROUP BY field_name
ORDER BY conflict_count DESC;

Example Output:
┌────────────────┬────────────────┬──────────────────┐
│ field          │ conflict_count │ involved_sources │
├────────────────┼────────────────┼──────────────────┤
│ weight_lbs     │ 28             │ {pff, nfl}       │
│ height_inches  │ 15             │ {pff, nfl}       │
│ position       │ 8              │ {pff, cfr}       │
└────────────────┴────────────────┴──────────────────┘

Question 3: Data Traceability (Find Full History)
════════════════════════════════════════════════════════════════

SELECT 
  field_name,
  value_current,
  value_previous,
  source_system,
  transformation_rule_id,
  changed_at
FROM data_lineage
WHERE entity_id = :prospect_id
ORDER BY changed_at DESC;

Example: prospect_id = uuid-123

Result: (Alex Johnson height)
┌────────────┬──────────────┬──────────────┬────────┬──────────────────────┬──────────────────────────┐
│ field      │ value_curr   │ value_prev   │ source │ transformation_rule  │ changed_at               │
├────────────┼──────────────┼──────────────┼────────┼──────────────────────┼──────────────────────────┤
│ height     │ 74           │ 73           │ nfl    │ nfl_height_parse     │ 2026-02-14 03:20:00      │
│ height     │ 73           │ NULL         │ pff    │ pff_fuzzy_match      │ 2026-02-14 03:10:00      │
└────────────┴──────────────┴──────────────┴────────┴──────────────────────┴──────────────────────────┘

Interpretation: 
- PFF reported 73 (from some data source)
- NFL reported 74 (from combine)
- System picked 74 (more recent: 03:20 vs 03:10)
- All documented + auditable
```

---

## 7. Schema Evolution Example

```
Scenario: Adding New Source (ESPN Injuries)

BEFORE ETL (Monolithic Approach)
════════════════════════════════════════════════════════════════
Prospect table:
  id, name, position, college, height, weight,
  grade, passing_yards, rushing_yards,
  injury_type, injury_date, ← NEW COLUMNS
  injury_recovery_status ← NEW COLUMNS

Problems:
  ✗ Mixing grades + stats + injuries in one table
  ✗ Schema bloat (will have 50+ columns)
  ✗ Deduplication logic must know about injury fields
  ✗ Injury data only from ESPN, but generic table structure

AFTER ETL (Layered Approach)
════════════════════════════════════════════════════════════════
Step 1: Create staging table
  CREATE TABLE espn_staging (
    id SERIAL PRIMARY KEY,
    extraction_id UUID,
    espn_athlete_id VARCHAR,
    injury_type VARCHAR,
    injury_date DATE,
    recovery_status VARCHAR,
    ...
  );

Step 2: Create transformer
  class ESPNTransformer(BaseTransformer):
    async def validate_staging_data(self, row):
      # Validation rules for injuries
    async def transform_staging_to_canonical(self, row, prospect_id):
      # Return prospect_injuries records

Step 3: Register in orchestrator
  self.transformers['espn'] = ESPNTransformer(...)

Step 4: Deploy (no schema changes to other tables!)
  Daily pipeline runs, loads espn_staging
  ESPNTransformer creates prospect_injuries records
  Lineage tracks all changes

Benefits:
  ✓ Canonical schema unchanged
  ✓ ESPN data isolated to injury table
  ✓ Deduplication logic unchanged
  ✓ Extensible (ESPN → Future Source = same pattern)
```

---

End of Visual Reference Guide
