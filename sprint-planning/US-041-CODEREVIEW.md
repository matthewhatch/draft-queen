# US-041: PFF Data Integration & Reconciliation — Code Review

**Reviewer:** QA Agent  
**Date:** 2026-02-12  
**Commit(s):** Unstaged changes (diff against `4055450`)  
**Test Results (initial):** 37 passed, 7 failed (44 total)  
**Test Results (after fixes):** 43 passed, 1 failed (44 total)

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

### Bug #1 — ~~CRITICAL~~ ✅ FIXED: `_write_audit()` uses wrong column names for `DataLoadAudit`

**File:** [pff_grade_loader.py](../data_pipeline/loaders/pff_grade_loader.py#L222-L237)  
**Severity:** CRITICAL — causes `TypeError` at runtime, failing 3 tests  
**Status:** ✅ **FIXED** — Now uses correct columns: `data_source`, `total_records_received`, `records_validated`, `records_inserted`, `records_updated`, `records_skipped`, `records_failed`, `status`, `error_summary`, `error_details`, `operator`.

<details>
<summary>Original finding (resolved)</summary>

The `_write_audit()` method constructed a `DataLoadAudit` with keyword arguments that didn't match the actual model columns:

| Loader used | Actual `DataLoadAudit` column |
|---|---|
| `source="pff"` | `data_source="pff"` |
| `load_type="grade_integration"` | ❌ Column does not exist |
| `records_processed=...` | `total_records_received=...` |
| `records_loaded=...` | `records_inserted=...` + `records_updated=...` |
| `records_rejected=...` | `records_failed=...` |

</details>

---

### Bug #2 — ~~HIGH~~ ✅ FIXED: `prospect_id` type mismatch (Integer vs UUID)

**File:** [prospect_grades.py](../data_pipeline/models/prospect_grades.py#L13)  
**Severity:** HIGH — would cause FK constraint error at runtime  
**Status:** ✅ **FIXED** — `prospect_id` now uses `Column(UUID(as_uuid=True), ForeignKey(...))` with proper `postgresql` import.

<details>
<summary>Original finding (resolved)</summary>

The `ProspectGrade` model declared `prospect_id` as `Column(Integer, ...)` but the `Prospect` model's primary key is `Column(UUID(as_uuid=True), ...)`. Migration was correct but ORM model was wrong.

</details>

---

### Bug #3 — ~~HIGH~~ ✅ FIXED: `test_exact_match_name_position_college` passes empty index

**File:** [test_pff_grade_loader.py](../tests/unit/test_pff_grade_loader.py#L68-L88)  
**Severity:** HIGH — test was fundamentally broken  
**Status:** ✅ **FIXED** — Test now builds a proper `prospect_index` and calls `_fuzzy_match()` directly with correct assertions.

---

### Bug #4 — ~~HIGH~~ ⚠️ PARTIALLY FIXED: `test_fuzzy_match_name_variation` — still failing

**File:** [test_pff_grade_loader.py](../tests/unit/test_pff_grade_loader.py#L91-L118)  
**Severity:** HIGH — 1 test still failing  
**Status:** ⚠️ **PARTIALLY FIXED** — Test was updated to use matching position (`"DL"`) and school (`"Georgia"`), but `"DL"` is a **DB position**, not a PFF position. `map_pff_position_to_db("DL")` returns `None` because `"DL"` isn't in `PFF_TO_DB_POSITION_MAP` (only `DT`→`DL` and `DE`→`DL` exist). This causes position score = 0.

Actual scoring: name `token_sort_ratio("j. carter", "jalen carter")` = 80, position = 0 (unmapped), college = 100.  
Composite: `(80 × 0.60) + (0 × 0.25) + (100 × 0.15)` = `48 + 0 + 15` = **63.0** — below 75 threshold.

**Fix:** Change PFF position in the test to a real PFF position that maps to `"DL"`:
```python
pff_data = self._make_pff_prospect(
    name="J. Carter",
    position="DT",     # ← Real PFF position (maps to DL)
    school="Georgia",
)
```

---

### Bug #5 — ~~MEDIUM~~ ✅ FIXED: `test_match_weights_name_heavy` — 60% name weight alone can't reach 75 threshold

**File:** [test_pff_grade_loader.py](../tests/unit/test_pff_grade_loader.py#L357-L388)  
**Severity:** MEDIUM — test failed due to wrong expectations  
**Status:** ✅ **FIXED** — Renamed to `test_match_weights_name_heavy_plus_college`, now uses full match (name + position + college) with correct assertion that composite ≥ `MATCH_THRESHOLD_HIGH`.

---

### Bug #6 — ~~MEDIUM~~ ✅ FIXED: Pipeline stage order comment inconsistency

**File:** [pff_pipeline_setup.py](../data_pipeline/orchestration/pff_pipeline_setup.py#L64-L69)  
**Severity:** MEDIUM — misleading comment  
**Status:** ✅ **FIXED** — Comment now reads `# After PFF_SCRAPE (order 2), before RECONCILIATION`.

---

### Bug #7 — MEDIUM: `PFFGradeLoadConnector` data flow gap — NOT FIXED

**File:** [stage_connectors.py](../data_pipeline/orchestration/stage_connectors.py#L391)  
**Severity:** MEDIUM — connector will always have empty data when called from pipeline  
**Status:** ❌ **NOT FIXED**

`PFFGradeLoadConnector.__init__` takes `pff_prospects` as a constructor arg, defaulting to `[]`. In `pff_pipeline_setup.py` line 65, it's constructed as `PFFGradeLoadConnector()` — with no data.

The `PFFConnector.execute()` scrapes PFF data and returns it, but there's no mechanism to pass that output into `PFFGradeLoadConnector`. The orchestrator runs stages sequentially but doesn't chain outputs between stages.

**Fix:** The connector needs a way to receive data from the previous stage. Options:
1. Pass the orchestrator's execution context/results into subsequent connectors
2. Have `PFFGradeLoadConnector` accept a callable that returns PFF data
3. Use a shared state dict between stages

---

### Bug #8 — ~~LOW~~ ✅ FIXED: Missing newline at end of `stage_connectors.py`

**File:** [stage_connectors.py](../data_pipeline/orchestration/stage_connectors.py)  
**Severity:** LOW  
**Status:** ✅ **FIXED** — File now ends with proper newline.

---

### Bug #9 — ~~LOW~~ ✅ FIXED: `reconcile_measurements()` not updated for PFF data

**File:** [reconciliation_engine.py](../data_pipeline/reconciliation/reconciliation_engine.py#L159)  
**Severity:** LOW  
**Status:** ✅ **FIXED** — `pff_data: Optional[Dict[str, Any]] = None` parameter added. Docstring updated. PFF handling block added to method body with authority rule application.

---

### Bug #10 — ~~LOW~~ ✅ FIXED: Em-dash guard not implemented

**File:** [pff_grade_loader.py](../data_pipeline/loaders/pff_grade_loader.py#L191)  
**Severity:** LOW  
**Status:** ✅ **FIXED** — Guard added: `if pff_college == "—": pff_college = ""`

---

### Bug #11 — NEW / CRITICAL: Syntax error in `pff_pipeline_setup.py` (introduced by fixes)

**File:** [pff_pipeline_setup.py](../data_pipeline/orchestration/pff_pipeline_setup.py#L71)  
**Severity:** CRITICAL — file will crash on import  
**Status:** ❌ **OPEN**

A stray extra `)` on line 71 was introduced when fixing Bug #6. The `register_stage()` call closes on line 70, then there's an orphaned `)` on line 71:

```python
        orchestrator.register_stage(
            stage=PipelineStage.PFF_GRADE_LOAD,
            connector=pff_grade_connector,
            order=45,  # After PFF_SCRAPE (order 2), before RECONCILIATION
        )
        )    # ← STRAY PAREN — syntax error
```

**Fix:** Remove the extra `)` on line 71.

---

## Test Results Summary

### Initial Review: 37 passed, 7 failed

| Test | Status | Root Cause |
|------|--------|-----------|
| `test_exact_match_name_position_college` | ❌ FAIL | Bug #3 — empty index passed |
| `test_fuzzy_match_name_variation` | ❌ FAIL | Bug #4 — mismatched position/school makes score too low |
| `test_batch_load_stats` | ❌ FAIL | Bug #1 — `DataLoadAudit` wrong columns |
| `test_audit_trail_written` | ❌ FAIL | Bug #1 — `DataLoadAudit` wrong columns |
| `test_duplicate_pff_entries_same_prospect` | ❌ FAIL | Bug #1 — `DataLoadAudit` wrong columns |
| `test_transaction_rollback_on_error` | ❌ FAIL | Bug #1 — `DataLoadAudit` wrong columns |
| `test_match_weights_name_heavy` | ❌ FAIL | Bug #5 — 60% weight can't reach 75 threshold |

### After Fixes: 43 passed, 1 failed

| Test | Status | Root Cause |
|------|--------|-----------|
| `test_exact_match_name_position_college` | ✅ PASS | Bug #3 fixed |
| `test_fuzzy_match_name_variation` | ❌ FAIL | Bug #4 — test uses `"DL"` as PFF position but `DL` is not in PFF→DB position map |
| `test_batch_load_stats` | ✅ PASS | Bug #1 fixed |
| `test_audit_trail_written` | ✅ PASS | Bug #1 fixed |
| `test_duplicate_pff_entries_same_prospect` | ✅ PASS | Bug #1 fixed |
| `test_transaction_rollback_on_error` | ✅ PASS | Bug #1 fixed |
| `test_match_weights_name_heavy_plus_college` | ✅ PASS | Bug #5 fixed (renamed) |

---

## Acceptance Criteria Checklist

| Criteria | Status | Notes |
|----------|--------|-------|
| New `prospect_grades` table schema | ✅ | Model + migration created, UUID FK fixed |
| PFF grades linked via fuzzy matching | ✅ | FK type fixed, matching logic works |
| Handle duplicates | ✅ | Upsert logic correct |
| Reconciliation rules: PFF authoritative | ✅ | Enum + rules + `reconcile_measurements()` all wired |
| Audit trail for grade changes | ✅ | Column names fixed, audit records write correctly |
| Daily updates integrated with pipeline | ⚠️ | Stage registered but data flow broken (Bug #7) |
| Handle missing/partial grades | ✅ | `PFFDataValidator.validate_batch()` + em-dash guard |
| Error logging for unmatched | ✅ | Proper logging with name/position/school |
| Unit tests passing | ⚠️ | 43/44 passing — 1 remaining (Bug #4) |

---

## Remaining Open Issues

| # | Severity | Issue | Fix |
|---|----------|-------|-----|
| **#4** | HIGH | `test_fuzzy_match_name_variation` uses `"DL"` (DB position) instead of a real PFF position like `"DT"` | Change test `position="DT"` |
| **#7** | MEDIUM | `PFFGradeLoadConnector` always gets empty data — no inter-stage data flow | Implement stage output chaining in orchestrator |
| **#11** | CRITICAL | Stray `)` on `pff_pipeline_setup.py` line 71 — syntax error | Delete the extra paren |
