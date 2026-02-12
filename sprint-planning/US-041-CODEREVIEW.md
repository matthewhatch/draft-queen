# US-041: PFF Data Integration & Reconciliation — Code Review

**Reviewer:** QA Agent  
**Date:** 2026-02-12  
**Commit(s):** Unstaged changes (diff against `4055450`)  
**Test Results:** 37 passed, 7 failed (44 total)

---

## Summary

The implementation covers all 11 items from the file checklist in the technical spec. Files created/modified:

| # | File | Status |
|---|------|--------|
| 1 | `data_pipeline/models/prospect_grades.py` | ✅ Created |
| 2 | `backend/database/models.py` | ✅ Modified (relationship + import) |
| 3 | `migrations/versions/v002_add_prospect_grades_table.py` | ✅ Created |
| 4 | `data_pipeline/validators/pff_validator.py` | ✅ Modified (position map + normalization) |
| 5 | `data_pipeline/loaders/pff_grade_loader.py` | ✅ Created |
| 6 | `data_pipeline/reconciliation/reconciliation_engine.py` | ✅ Modified (PFF source + authority) |
| 7 | `data_pipeline/orchestration/pipeline_orchestrator.py` | ✅ Modified (PFF_GRADE_LOAD enum) |
| 8 | `data_pipeline/orchestration/pff_pipeline_setup.py` | ✅ Modified (register grade stage) |
| 9 | `data_pipeline/orchestration/stage_connectors.py` | ✅ Modified (PFFGradeLoadConnector) |
| 10 | `tests/unit/test_pff_grade_loader.py` | ✅ Created |
| 11 | `tests/unit/test_reconciliation.py` | ✅ Modified (PFF test class) |
| 12 | `migrations/env.py` | ✅ Modified (ProspectGrade import) |

---

## Findings

### Bug #1 — CRITICAL: `_write_audit()` uses wrong column names for `DataLoadAudit`

**File:** [pff_grade_loader.py](../data_pipeline/loaders/pff_grade_loader.py#L222-L237)  
**Severity:** CRITICAL — causes `TypeError` at runtime, failing 3 tests

The `_write_audit()` method constructs a `DataLoadAudit` with keyword arguments that don't match the actual model columns:

| Loader uses | Actual `DataLoadAudit` column |
|---|---|
| `source="pff"` | `data_source="pff"` |
| `load_type="grade_integration"` | ❌ Column does not exist |
| `records_processed=...` | `total_records_received=...` |
| `records_loaded=...` | `records_inserted=...` + `records_updated=...` |
| `records_rejected=...` | `records_failed=...` |

The actual `DataLoadAudit` model (in `backend/database/models.py` line 254) has columns: `data_source`, `total_records_received`, `records_validated`, `records_inserted`, `records_updated`, `records_skipped`, `records_failed`, `status`, `error_summary`, `error_details`, `operator`.

**Fix:** Rewrite `_write_audit()` to use the correct column names:
```python
audit = DataLoadAudit(
    data_source="pff",
    total_records_received=self.stats["total"],
    records_validated=self.stats["matched"],
    records_inserted=self.stats["inserted"],
    records_updated=self.stats["updated"],
    records_skipped=self.stats["unmatched"],
    records_failed=self.stats["errors"],
    status="success" if self.stats["errors"] == 0 else "partial",
    error_summary=f"unmatched={self.stats['unmatched']}, errors={self.stats['errors']}",
    error_details={"unmatched": self.stats["unmatched"], "errors": self.stats["errors"]},
    operator="pff_grade_loader",
)
```

**Tests affected:** `test_audit_trail_written`, `test_duplicate_pff_entries_same_prospect`, `test_transaction_rollback_on_error`

---

### Bug #2 — HIGH: `prospect_id` type mismatch (Integer vs UUID)

**File:** [prospect_grades.py](../data_pipeline/models/prospect_grades.py#L13)  
**Severity:** HIGH — will cause FK constraint error at runtime

The `ProspectGrade` model declares `prospect_id` as `Column(Integer, ForeignKey("prospects.id", ...))`, but the `Prospect` model's primary key is `Column(UUID(as_uuid=True), ...)`.

The migration file at [v002_add_prospect_grades_table.py](../migrations/versions/v002_add_prospect_grades_table.py#L26) correctly uses `postgresql.UUID(as_uuid=True)` for `prospect_id`, so the migration is right but **the ORM model is wrong**.

**Fix:** In `data_pipeline/models/prospect_grades.py`, change:
```python
# FROM:
prospect_id = Column(Integer, ForeignKey("prospects.id", ondelete="CASCADE"), ...)
# TO:
from sqlalchemy.dialects.postgresql import UUID
prospect_id = Column(UUID(as_uuid=True), ForeignKey("prospects.id", ondelete="CASCADE"), ...)
```

This also affects the return type annotation in `_fuzzy_match()` — it returns `Tuple[str, float]` but the ID is actually a UUID, not str. The code works because mock objects are used in tests, but the annotation is misleading.

---

### Bug #3 — HIGH: `test_exact_match_name_position_college` passes empty index

**File:** [test_pff_grade_loader.py](../tests/unit/test_pff_grade_loader.py#L77-L82)  
**Severity:** HIGH — test is fundamentally broken

The test calls `self.loader._process_one(pff_data, [])` with an **empty** prospect index. With no candidates to match against, `_fuzzy_match()` returns `None`, so the prospect is counted as unmatched. The assertion `stats["matched"] == 1` then fails.

**Fix:** Build a proper prospect index from the mock DB prospect and pass it:
```python
prospect_index = [{
    "id": db_prospect.id,
    "name": "travis hunter",
    "position": "DB",
    "college": "colorado",
    "obj": db_prospect,
}]
self.loader._process_one(pff_data, prospect_index)
```

---

### Bug #4 — HIGH: `test_fuzzy_match_name_variation` — threshold too aggressive for abbreviations

**File:** [test_pff_grade_loader.py](../tests/unit/test_pff_grade_loader.py#L85-L102)  
**Severity:** HIGH — test fails, reveals real matching gap

The test matches PFF `"J. Carter"` against DB `"Jalen Carter"` with:
- PFF position `"CB"` (maps to `"DB"`) vs DB `"DL"` → position score = 0
- PFF school `"Colorado"` vs DB `"georgia"` → college score ≈ 30
- Name: `token_sort_ratio("j. carter", "jalen carter")` ≈ 63

Composite: `(63 × 0.60) + (0 × 0.25) + (30 × 0.15)` = `37.8 + 0 + 4.5` = **42.3** — well below threshold of 75.

This is actually a correct rejection by the algorithm. The test expectations are wrong — `"J. Carter"` with wrong position and wrong school *shouldn't* match. The test description is misleading.

**Fix:** Either:
- (a) Change the test to use matching position and school: `position="DL"`, `school="Georgia"` — this would test pure name fuzz
- (b) Accept this as a correct rejection and change the assertion to `assert match is None`

---

### Bug #5 — MEDIUM: `test_match_weights_name_heavy` — 60% name weight alone can't reach 75 threshold

**File:** [test_pff_grade_loader.py](../tests/unit/test_pff_grade_loader.py#L345-L368)  
**Severity:** MEDIUM — test fails, reveals design consideration

The test has a perfect name match (100) but wrong position (0) and wrong school (0):
- Composite = `(100 × 0.60) + (0 × 0.25) + (0 × 0.15)` = **60.0**

60.0 < 75 threshold, so `_fuzzy_match()` returns `None`.

This is actually *by design* — the spec says name is 60% weight, meaning a perfect name match alone maxes at 60 points, deliberately below the 75 threshold to prevent false positives. The test expectation is wrong.

**Fix:** Adjust the test to validate the actual design. Either:
- Add at least partial college match to reach threshold, OR
- Assert `match is None` and add a comment: "Perfect name alone (60%) is intentionally below threshold (75) to prevent false positives"

---

### Bug #6 — MEDIUM: Pipeline stage order inconsistency

**File:** [pff_pipeline_setup.py](../data_pipeline/orchestration/pff_pipeline_setup.py#L64-L69)  
**Severity:** MEDIUM — confusing but not crash-level

The PFF_SCRAPE stage is registered at `order=2`, but the comment on PFF_GRADE_LOAD says `order=45 # After PFF_SCRAPE (order 40)`. The comment references order 40 but PFF_SCRAPE is actually at order 2. This is misleading.

**Fix:** Update the comment:
```python
order=45,  # After PFF_SCRAPE (order 2), before RECONCILIATION
```

Or reconsider the ordering scheme for consistency.

---

### Bug #7 — MEDIUM: `PFFGradeLoadConnector` data flow gap

**File:** [stage_connectors.py](../data_pipeline/orchestration/stage_connectors.py#L391)  
**Severity:** MEDIUM — connector will always have empty data when called from pipeline

`PFFGradeLoadConnector.__init__` takes `pff_prospects` as a constructor arg, defaulting to `[]`. In `pff_pipeline_setup.py` line 67, it's constructed as `PFFGradeLoadConnector()` — with no data.

The `PFFConnector.execute()` scrapes PFF data and returns it, but there's no mechanism to pass that output into `PFFGradeLoadConnector`. The orchestrator runs stages sequentially but doesn't appear to chain outputs between stages.

**Fix:** The connector needs a way to receive data from the previous stage. Options:
1. Pass the orchestrator's execution context/results into subsequent connectors
2. Have `PFFGradeLoadConnector` accept a callable that returns PFF data
3. Use a shared state dict between stages

This is the same gap noted in the tech spec (Section 6, "Get PFF data from previous stage output (context)") but wasn't addressed in the implementation.

---

### Bug #8 — MEDIUM: Missing newline at end of `stage_connectors.py`

**File:** [stage_connectors.py](../data_pipeline/orchestration/stage_connectors.py)  
**Severity:** LOW — style issue, some tools complain

The file doesn't end with a newline character. POSIX standard requires a newline at EOF.

---

### Bug #9 — LOW: `reconcile_measurements()` not updated for PFF data

**File:** [reconciliation_engine.py](../data_pipeline/reconciliation/reconciliation_engine.py#L159)  
**Severity:** LOW — partially complete

The tech spec called for adding a `pff_data=None` parameter to the `reconcile_measurements()` method. The `DataSource.PFF`, `FieldCategory.PFF_GRADES`, and authority rules were all added correctly, but the actual reconcile method was not updated to accept or process PFF data.

The new reconciliation tests work because they only test enum existence and manual conflict creation — they never call `reconcile_measurements()` with PFF data.

**Fix:** Add `pff_data` parameter to `reconcile_measurements()` and add PFF grade reconciliation logic within the method body.

---

### Bug #10 — LOW: Em-dash guard not implemented

**File:** [pff_grade_loader.py](../data_pipeline/loaders/pff_grade_loader.py)  
**Severity:** LOW

The tech spec (Gotcha #5) warned about PFF scraper returning `"—"` for missing school/class fields. No guard was added in the loader. Bug #4 from `BUGS.md` is still open.

**Fix:** Add to `_fuzzy_match()`:
```python
pff_college = (pff_data.get("school") or "").lower().strip()
if pff_college == "—":
    pff_college = ""
```

---

## Test Results Summary

**Total: 44 tests (37 passed, 7 failed)**

| Test | Status | Root Cause |
|------|--------|-----------|
| `test_exact_match_name_position_college` | ❌ FAIL | Bug #3 — empty index passed |
| `test_fuzzy_match_name_variation` | ❌ FAIL | Bug #4 — mismatched position/school makes score too low |
| `test_batch_load_stats` | ❌ FAIL | Bug #1 — `DataLoadAudit` wrong columns |
| `test_audit_trail_written` | ❌ FAIL | Bug #1 — `DataLoadAudit` wrong columns |
| `test_duplicate_pff_entries_same_prospect` | ❌ FAIL | Bug #1 — `DataLoadAudit` wrong columns |
| `test_transaction_rollback_on_error` | ❌ FAIL | Bug #1 — `DataLoadAudit` wrong columns |
| `test_match_weights_name_heavy` | ❌ FAIL | Bug #5 — 60% weight can't reach 75 threshold |

---

## Acceptance Criteria Checklist

| Criteria | Status | Notes |
|----------|--------|-------|
| New `prospect_grades` table schema | ✅ | Model + migration created |
| PFF grades linked via fuzzy matching | ⚠️ | Works but FK type mismatch (Bug #2) |
| Handle duplicates | ✅ | Upsert logic correct |
| Reconciliation rules: PFF authoritative | ⚠️ | Enum + rules added, but `reconcile_measurements()` not wired (Bug #9) |
| Audit trail for grade changes | ❌ | Wrong column names crash at runtime (Bug #1) |
| Daily updates integrated with pipeline | ⚠️ | Stage registered but data flow broken (Bug #7) |
| Handle missing/partial grades | ✅ | `PFFDataValidator.validate_batch()` filters correctly |
| Error logging for unmatched | ✅ | Proper logging with name/position/school |
| Unit tests passing | ❌ | 7/14 failing |

---

## Priority Fix Order

1. **Bug #1** (CRITICAL) — Fix `DataLoadAudit` column names → unblocks 4 tests
2. **Bug #2** (HIGH) — Fix `prospect_id` type to UUID → required for DB runtime
3. **Bug #3** (HIGH) — Fix `test_exact_match` to pass prospect index → unblocks 1 test
4. **Bug #4** (HIGH) — Fix `test_fuzzy_match` expectations → unblocks 1 test
5. **Bug #5** (MEDIUM) — Fix `test_match_weights` expectations → unblocks 1 test
6. **Bug #7** (MEDIUM) — Implement stage data flow for pipeline
7. **Bug #9** (LOW) — Wire PFF into `reconcile_measurements()`
8. **Bug #10** (LOW) — Add em-dash guard
