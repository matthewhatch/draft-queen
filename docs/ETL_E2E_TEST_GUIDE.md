# ETL End-to-End Test Guide

## Quick Start

```bash
# From project root directory
cd /home/parrot/code/draft-queen

# Make sure Poetry environment is activated
source /home/parrot/.cache/pypoetry/virtualenvs/nfl-draft-queen-1FicStbu-py3.11/bin/activate

# Run the E2E test
PYTHONPATH=/home/parrot/code/draft-queen/src python scripts/test_e2e_etl.py
```

## What the Test Does

### 1. **Setup Phase**
- Connects to PostgreSQL database
- Clears any previous test data

### 2. **Data Preparation Phase**
- Inserts 3 sample PFF records into `pff_staging`
  - John Smith (QB, Alabama, grade 87.5)
  - Mike Johnson (WR, Ohio State, grade 78.3)
  - David Williams (RB, Georgia, grade 82.1)
- Inserts 2 sample CFR records into `cfr_staging`
  - Tom Jones (RB, Georgia, rushing stats)
  - James Brown (WR, Alabama, receiving stats)

### 3. **Orchestrator Execution Phase**
Runs the full ETL pipeline through 6 phases:
1. **EXTRACT** - Loads staging table metadata
2. **TRANSFORM** - Executes PFF + CFR transformers in parallel
3. **VALIDATE** - Runs data quality checks
4. **MERGE** - Deduplicates prospects across sources
5. **LOAD** - Atomically commits to canonical tables
6. **PUBLISH** - Refreshes materialized views

### 4. **Verification Phase**
Queries database to verify:
- ✓ Records in prospect_core (deduplicated)
- ✓ Records in prospect_grades (normalized 5.0-10.0 scale)
- ✓ Records in prospect_college_stats (position-specific)
- ✓ Records in data_lineage (complete audit trail)
- ✓ Pipeline execution status in etl_pipeline_runs

### 5. **Summary Phase**
Prints comprehensive test results and verdict

## Expected Output

```
============================================================
Verifying Results in Database
============================================================

✓ prospect_core records: 5
✓ prospect_grades records: 3
✓ prospect_college_stats records: 2
✓ data_lineage records (this extraction): 45
✓ ETL pipeline run status: completed
  - Records staged: 5
  - Records transformed: 5
  - Records loaded: 5
✓ Duplicate prospect groups: 0

============================================================
E2E TEST SUMMARY
============================================================

Extraction ID: <uuid>
Timestamp: 2026-02-15T...

Input Data:
  - PFF records inserted: 3
  - CFR records inserted: 2

Pipeline Results:
  - Overall Status: success
  - Duration: 8.45s
  - Quality Score: 98.5%

Database Verification:
  - prospect_core records: 5
  - prospect_grades records: 3
  - prospect_college_stats records: 2
  - data_lineage records: 45
  - Duplicate groups: 0

Pipeline Run Status:
  - Status: completed
  - Staged: 5
  - Transformed: 5
  - Loaded: 5

============================================================
✅ E2E TEST PASSED - All checks successful!
============================================================
```

## Troubleshooting

### Error: "Failed to connect to database"
- Check PostgreSQL is running: `psql -U postgres -c "SELECT 1;"`
- Verify connection string in script: `postgresql+asyncpg://postgres:postgres@localhost/draft_queen`
- Check credentials in `.env` or connection config

### Error: "Relation 'pff_staging' does not exist"
- Run migrations first:
  ```bash
  alembic upgrade head
  ```
- Verify tables exist:
  ```bash
  psql postgresql://postgres:postgres@localhost/draft_queen -c "\dt pff_staging cfr_staging"
  ```

### Error: "KeyError: 'PFF' in register_transformer"
- Ensure all transformers are imported properly
- Check that transformer classes inherit from BaseTransformer
- Verify enum values match: `TransformerType.PFF = "pff"`

### Pipeline Status: "Failed"
- Check logs for phase that failed (extract, transform, validate, etc.)
- Common issues:
  - **Validation failed:** Quality score < 95% (check grade ranges)
  - **Transform failed:** Missing required fields in staging data
  - **Load failed:** Database transaction error (check disk space, permissions)

## Test Data Details

### PFF Test Data
- All records inserted with `extraction_source='test'`
- Grades intentionally varied (78.3 - 87.5) to test range validation
- Positions: QB, WR, RB for testing position-specific logic

### CFR Test Data
- Different prospects from PFF (no duplicates expected)
- Includes realistic college stats:
  - RB with rushing + receiving stats
  - WR with high receiving targets/yards
- Tests position-specific stat validation

## Manual Database Inspection

After test completes, inspect results:

```bash
# Connect to database
psql postgresql://postgres:postgres@localhost/draft_queen

# View canonical prospects
SELECT id, name_first, name_last, position, college FROM prospect_core 
WHERE created_from_source IN ('pff', 'cfr') 
LIMIT 10;

# View normalized grades
SELECT p.name_last, g.grade, g.source FROM prospect_grades g
JOIN prospect_core p ON g.prospect_id = p.id 
LIMIT 10;

# View college stats
SELECT p.name_last, s.season, s.position, s.rushing_yards, s.receiving_yards 
FROM prospect_college_stats s
JOIN prospect_core p ON s.prospect_id = p.id 
LIMIT 10;

# View transformation lineage
SELECT entity_id, field_name, value_current, transformation_rule_id 
FROM data_lineage 
LIMIT 20;

# Check for duplicates (should be 0)
SELECT COUNT(*) FROM prospect_core
GROUP BY LOWER(name_first), LOWER(name_last), position
HAVING COUNT(*) > 1;
```

## Performance Metrics

Expected execution times on typical hardware:
- Extract phase: ~500ms (load metadata)
- Transform phase: ~3-5s (parallel PFF + CFR)
- Validate phase: ~1-2s (quality checks)
- Merge phase: ~1-2s (deduplication)
- Load phase: ~1-2s (transaction commit)
- Publish phase: ~500ms (view refresh)
- **Total: ~8-15 seconds**

## Next Steps After Successful E2E Test

1. **Real Data Testing**
   - Replace test data with actual PFF API data
   - Use real CFR scraper data
   - Test with full prospect database

2. **Stress Testing**
   - Test with 10,000+ prospects
   - Measure performance scaling
   - Verify transaction deadlock handling

3. **Error Path Testing**
   - Inject invalid grades (fail quality validation)
   - Missing required fields (fail transformation)
   - Database connection loss (verify rollback)

4. **Idempotency Testing**
   - Run same extraction twice
   - Verify identical results
   - Check no duplicates created

5. **Staging Deployment**
   - Deploy orchestrator to staging environment
   - Run E2E test against staging database
   - Verify in staging logs and monitoring

## Success Criteria

✅ **Test passes if:**
- Overall status = "success"
- prospect_core has records
- prospect_grades has records
- prospect_college_stats has records
- data_lineage has records (audit trail)
- No critical errors in pipeline phases
- Pipeline run status = "completed"

❌ **Test fails if:**
- Any phase errors occur
- Quality validation fails
- No records loaded to canonical tables
- Database transaction fails
- Lineage tracking incomplete
