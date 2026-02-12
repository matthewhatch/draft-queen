# Sprint 4: PFF Data Integration & Premium Analytics - User Stories
**Duration:** Mar 24 - Apr 6 (2 weeks)
**Focus:** Dockerization (priority), PFF scraper implementation, data reconciliation

---

## US-045: Dockerize Application for Production Deployment

### User Story
As a **DevOps engineer**  
I want to **containerize the entire application with Docker**  
So that **the app can be deployed consistently across development, staging, and production environments**

### Description
Create comprehensive Docker setup for the entire application including backend API, data pipeline, CLI tools, and PostgreSQL database. Enable multi-environment deployments with proper volume management, networking, and configuration handling.

### Acceptance Criteria
- [ ] Dockerfile for backend API service (FastAPI)
- [ ] Dockerfile for data pipeline service (ETL worker)
- [ ] Dockerfile for CLI service (optional, can use backend image)
- [ ] docker-compose.yml with all services (API, pipeline, database, redis)
- [ ] Environment variable configuration (.env support)
- [ ] Database initialization and migration on startup
- [ ] Health check endpoints for container orchestration
- [ ] Volume mounts for data persistence (cache, logs, database)
- [ ] Build scripts work on Linux, macOS, Windows
- [ ] Documentation for local development setup with Docker

### Technical Acceptance Criteria
- [ ] Base image: Python 3.11 slim
- [ ] Multi-stage builds for optimization
- [ ] Redis service for caching
- [ ] PostgreSQL service with proper initialization
- [ ] Network isolation between services
- [ ] Proper entrypoint scripts for startup
- [ ] Logging configuration (stdout for containers)
- [ ] Security best practices (non-root user, minimal layers)
- [ ] .dockerignore to exclude unnecessary files
- [ ] Works with poetry dependencies

### Tasks
- **DevOps:** Create Dockerfile for backend API
- **DevOps:** Create Dockerfile for data pipeline
- **DevOps:** Create docker-compose.yml
- **DevOps:** Write container initialization scripts
- **DevOps:** Create comprehensive Docker documentation

### Definition of Done
- [ ] All services start and run successfully
- [ ] Database initializes automatically
- [ ] Services communicate correctly
- [ ] Volumes persist data correctly
- [ ] Environment variables work properly
- [ ] Startup and shutdown graceful
- [ ] Documentation complete

### Effort
- **DevOps:** 5 story points
- **Total:** 5 story points

---

## US-040: PFF.com Draft Big Board Web Scraper

### User Story
As a **data engineer**  
I want to **scrape prospect grades and rankings from PFF.com**  
So that **analysts have access to industry-standard PFF grades for evaluation**

### Description
Build web scraper for PFF.com's Draft Big Board (https://www.pff.com/draft/big-board?season=2026). Extract prospect grades, rankings, and position-specific metrics. Integrate with existing multi-source pipeline.

### Context
**Spike-001 Outcome:** Scenario A (Low Risk, High Value)
- PFF.com uses static HTML (no Selenium needed)
- robots.txt permits scraping with reasonable rate limiting
- Terms of service allow internal data extraction
- High-value proprietary grades not available elsewhere

### Acceptance Criteria
- [ ] Scraper successfully extracts from PFF Draft Big Board
- [ ] Extracts: prospect name, grade (overall), position grade, ranking, position
- [ ] Handles pagination (multiple pages of prospects)
- [ ] Data validation (grades 0-100 scale, rankings sequential)
- [ ] Deduplicates against existing prospects
- [ ] Respects rate limiting (3-5s delays between requests)
- [ ] Proper User-Agent headers and robots.txt compliance
- [ ] Logs all scrapes with timestamps and data counts
- [ ] Fallback to cached data if scrape fails
- [ ] Tests with sample HTML fixtures

### Technical Acceptance Criteria
- [ ] BeautifulSoup4 for HTML parsing
- [ ] Follows same pattern as NFL.com and Yahoo Sports scrapers
- [ ] Fuzzy matching for prospect identification
- [ ] PFF data validation framework
- [ ] Unit tests with HTML fixtures (90%+ coverage)
- [ ] Integration with main ETL pipeline
- [ ] Performance: scrape completes < 3 minutes

### Tasks
- **Data:** Build PFF.com scraper
- **Data:** Create HTML fixtures for testing
- **Data:** Implement grade validation
- **Data:** Write comprehensive tests
- **Backend:** Integrate into pipeline scheduler

### Definition of Done
- [ ] Scraper extracts all PFF data fields
- [ ] Data validated and parsed correctly
- [ ] Tests passing (90%+ coverage)
- [ ] Error handling verified
- [ ] Fallback caching working
- [ ] Integrated into daily pipeline

### Effort
- **Data:** 6 story points
- **Backend:** 1 story point
- **Total:** 7 story points

---

## US-041: PFF Data Integration & Reconciliation

### User Story
As a **data engineer**  
I want to **integrate PFF grades into the prospect database**  
So that **PFF data is available for analytics and reconciliation with other sources**

### Description
Add PFF grades to prospect records, establish reconciliation rules for conflicts (PFF grades vs. ESPN grades), and track PFF-sourced data in audit trail.

### Acceptance Criteria
- [ ] New table: prospect_grades (prospect_id, source, grade_overall, grade_position, grade_date)
- [ ] PFF grades linked to prospects via fuzzy matching (name + position + college)
- [ ] Handle duplicates (same prospect appears multiple times)
- [ ] Reconciliation rules: PFF authoritative for "grade" field
- [ ] Audit trail: track all grade changes with source
- [ ] Daily updates: PFF grades refresh with other sources
- [ ] Handle missing grades (partial data acceptable)
- [ ] Error logging for unmatched prospects

### Technical Acceptance Criteria
- [ ] Database schema for prospect_grades table
- [ ] Fuzzy matching algorithm (rapidfuzz)
- [ ] Transaction handling for atomicity
- [ ] Audit logging integration
- [ ] Batch insert with error recovery
- [ ] Unit tests for reconciliation logic

### Tasks
- **Backend:** Design prospect_grades schema
- **Backend:** Create migration for new table
- **Data:** Implement fuzzy matching
- **Backend:** Build grade reconciliation logic
- **Backend:** Integrate into pipeline
- **Data:** Write reconciliation tests

### Definition of Done
- [ ] Schema created and migrated
- [ ] PFF grades loading into database
- [ ] Reconciliation rules working
- [ ] Audit trail complete
- [ ] Tests passing

### Effort
- **Backend:** 4 story points
- **Data:** 2 story points
- **Total:** 6 story points

---

### Technical Implementation Guide

> **Audience:** Engineer implementing US-041. All file paths are relative to repo root.
> **Pre-requisites:** US-040 (PFF scraper) must be working. `rapidfuzz` is already in `pyproject.toml`.

---

#### 1 — Database: New `prospect_grades` Table

**File to create:** `data_pipeline/models/prospect_grades.py`

Add a new SQLAlchemy model in the existing models directory. Import `Base` from `backend/database/models.py`.

```python
# data_pipeline/models/prospect_grades.py
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey,
    UniqueConstraint, Index, func
)
from backend.database.models import Base

class ProspectGrade(Base):
    __tablename__ = "prospect_grades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    prospect_id = Column(Integer, ForeignKey("prospects.id", ondelete="CASCADE"), nullable=False, index=True)
    source = Column(String(50), nullable=False, index=True)          # "pff", "espn", "nfl", etc.
    grade_overall = Column(Float, nullable=True)                      # PFF 0–100 scale (store raw)
    grade_normalized = Column(Float, nullable=True)                   # Normalized to 5.0–10.0 scale
    grade_position = Column(String(10), nullable=True)                # Position at time of grading (PFF-native, e.g. "LT")
    match_confidence = Column(Float, nullable=True)                   # Fuzzy-match score 0–100
    grade_date = Column(DateTime, nullable=True)                      # Date grade was issued
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50), default="pff_loader")

    __table_args__ = (
        UniqueConstraint("prospect_id", "source", "grade_date", name="uq_prospect_grade_source_date"),
        Index("idx_grade_source", "source"),
        Index("idx_grade_prospect", "prospect_id"),
    )
```

**Also update:** `backend/database/models.py`
- Add `relationship("ProspectGrade", backref="prospect", cascade="all, delete-orphan")` to the `Prospect` class, alongside the existing `measurables`, `stats`, `injuries`, `rankings` relationships.
- Add import: `from data_pipeline.models.prospect_grades import ProspectGrade` (or re-export via `__init__`).

**Alembic migration:**
```bash
cd /home/parrot/code/draft-queen
poetry run alembic revision --autogenerate -m "add_prospect_grades_table"
poetry run alembic upgrade head
```
Verify the generated migration creates the `prospect_grades` table with the correct columns and constraints.

---

#### 2 — PFF Position Mapping

**File to modify:** `data_pipeline/validators/pff_validator.py`

The PFF scraper returns granular positions (`LT`, `LG`, `C`, `RG`, `RT`, `DT`, `DE`, `SS`, `FS`) that don't exist in the DB `CHECK` constraint which only allows: `QB, RB, FB, WR, TE, OL, DL, EDGE, LB, DB, K, P`.

Add a mapping constant and helper function:

```python
PFF_TO_DB_POSITION_MAP = {
    "LT": "OL", "LG": "OL", "C": "OL", "RG": "OL", "RT": "OL", "OT": "OL",
    "DT": "DL", "DE": "DL",
    "SS": "DB", "FS": "DB", "CB": "DB",
    "EDGE": "EDGE", "LB": "LB",
    "QB": "QB", "RB": "RB", "FB": "FB", "WR": "WR", "TE": "TE",
    "K": "K", "P": "P", "LS": "OL",
}

def map_pff_position_to_db(pff_position: str) -> str | None:
    """Map a PFF-native position to a DB-compatible position code."""
    return PFF_TO_DB_POSITION_MAP.get(pff_position.upper().strip())
```

This is used in two places: (a) when matching PFF prospects to DB prospects, and (b) when inserting the `grade_position` field (store the raw PFF position so no data is lost).

---

#### 3 — Grade Scale Normalization

**File to modify:** `data_pipeline/validators/pff_validator.py`

PFF grades are 0–100 scale. The DB `prospect_grade` column is CHECK-constrained to 5.0–10.0. Store **both** the raw PFF grade (`grade_overall`) and a normalized value (`grade_normalized`).

```python
def normalize_pff_grade(pff_grade: float) -> float:
    """Convert PFF 0–100 grade to 5.0–10.0 scale.
    
    Formula: normalized = 5.0 + (pff_grade / 100.0) * 5.0
    PFF 0 → 5.0, PFF 50 → 7.5, PFF 100 → 10.0
    """
    clamped = max(0.0, min(100.0, pff_grade))
    return round(5.0 + (clamped / 100.0) * 5.0, 1)
```

---

#### 4 — PFF Grade Loader (Core Implementation)

**File to create:** `data_pipeline/loaders/pff_grade_loader.py`

This is the central piece. Model it after the existing `ProspectLoader` in `data_pipeline/loaders/prospect_loader.py`.

**Responsibilities:**
1. Accept a list of raw PFF prospect dicts (from `PFFScraper.scrape()`)
2. Fuzzy-match each to an existing `Prospect` in the database
3. Insert/update `ProspectGrade` records
4. Log unmatched prospects
5. Write `DataLoadAudit` record

**Key implementation details:**

```python
# data_pipeline/loaders/pff_grade_loader.py
from rapidfuzz import fuzz, process
from sqlalchemy.orm import Session
from backend.database.models import Prospect
from data_pipeline.models.prospect_grades import ProspectGrade
from data_pipeline.validators.pff_validator import (
    normalize_pff_grade, map_pff_position_to_db, PFFDataValidator
)
from backend.database.models import DataLoadAudit
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

# Thresholds — tune these during testing
MATCH_THRESHOLD_HIGH = 90      # Auto-accept
MATCH_THRESHOLD_LOW = 75       # Reject below this
# Between LOW and HIGH → accept but flag for review

class PFFGradeLoader:
    def __init__(self, session: Session):
        self.session = session
        self.stats = {
            "total": 0, "matched": 0, "inserted": 0,
            "updated": 0, "unmatched": 0, "errors": 0,
        }
    
    def load(self, pff_prospects: list[dict]) -> dict:
        """Main entry point. Returns stats dict."""
        # 1. Validate input
        validated = PFFDataValidator.validate_batch(pff_prospects)
        self.stats["total"] = len(validated)
        
        # 2. Load all DB prospects for matching (single query)
        db_prospects = self.session.query(Prospect).all()
        prospect_index = self._build_match_index(db_prospects)
        
        # 3. Process each PFF prospect
        unmatched = []
        for pff_data in validated:
            try:
                self._process_one(pff_data, prospect_index)
            except Exception as e:
                logger.error(f"Error processing {pff_data.get('name')}: {e}")
                self.stats["errors"] += 1
        
        # 4. Commit transaction
        self.session.commit()
        
        # 5. Log unmatched
        if self.stats["unmatched"] > 0:
            logger.warning(f"{self.stats['unmatched']} PFF prospects could not be matched")
        
        # 6. Write audit record
        self._write_audit()
        
        return self.stats
    
    def _build_match_index(self, db_prospects: list[Prospect]) -> list[dict]:
        """Pre-process DB prospects into a fuzzy-matchable index."""
        return [
            {
                "id": p.id,
                "name": p.name.lower().strip(),
                "position": p.position,
                "college": (p.college or "").lower().strip(),
                "obj": p,
            }
            for p in db_prospects
        ]
    
    def _process_one(self, pff_data: dict, prospect_index: list[dict]):
        """Match one PFF prospect and upsert grade."""
        match = self._fuzzy_match(pff_data, prospect_index)
        
        if match is None:
            self.stats["unmatched"] += 1
            logger.info(f"UNMATCHED: {pff_data['name']} ({pff_data.get('position')}, {pff_data.get('school')})")
            return
        
        prospect_id, confidence = match
        self.stats["matched"] += 1
        
        pff_grade_raw = float(pff_data["grade"])
        grade_date = datetime.fromisoformat(pff_data["scraped_at"]) if pff_data.get("scraped_at") else datetime.now(timezone.utc)
        
        # Check for existing grade (upsert)
        existing = (
            self.session.query(ProspectGrade)
            .filter_by(prospect_id=prospect_id, source="pff")
            .first()
        )
        
        if existing:
            existing.grade_overall = pff_grade_raw
            existing.grade_normalized = normalize_pff_grade(pff_grade_raw)
            existing.match_confidence = confidence
            existing.grade_position = pff_data.get("position")
            existing.grade_date = grade_date
            existing.updated_at = datetime.now(timezone.utc)
            self.stats["updated"] += 1
        else:
            grade = ProspectGrade(
                prospect_id=prospect_id,
                source="pff",
                grade_overall=pff_grade_raw,
                grade_normalized=normalize_pff_grade(pff_grade_raw),
                grade_position=pff_data.get("position"),
                match_confidence=confidence,
                grade_date=grade_date,
            )
            self.session.add(grade)
            self.stats["inserted"] += 1
    
    def _fuzzy_match(self, pff_data: dict, prospect_index: list[dict]) -> tuple[int, float] | None:
        """
        Weighted fuzzy match: name (60%), position (25%), college (15%).
        Returns (prospect_id, confidence_score) or None.
        """
        pff_name = pff_data["name"].lower().strip()
        pff_position = map_pff_position_to_db(pff_data.get("position", ""))
        pff_college = (pff_data.get("school") or "").lower().strip()  # NOTE: PFF key is "school" not "college"
        
        best_match = None
        best_score = 0.0
        
        for candidate in prospect_index:
            # Name similarity (token_sort handles "John Smith Jr." vs "Smith, John")
            name_score = fuzz.token_sort_ratio(pff_name, candidate["name"])
            
            # Position match (exact after mapping = 100, else 0)
            pos_score = 100.0 if pff_position and pff_position == candidate["position"] else 0.0
            
            # College similarity
            college_score = fuzz.token_sort_ratio(pff_college, candidate["college"]) if pff_college else 50.0
            
            # Weighted composite
            composite = (name_score * 0.60) + (pos_score * 0.25) + (college_score * 0.15)
            
            if composite > best_score:
                best_score = composite
                best_match = candidate["id"]
        
        if best_score >= MATCH_THRESHOLD_LOW:
            return (best_match, round(best_score, 1))
        
        return None
    
    def _write_audit(self):
        """Write a DataLoadAudit record for this load run."""
        audit = DataLoadAudit(
            source="pff",
            load_type="grade_integration",
            status="completed" if self.stats["errors"] == 0 else "completed_with_errors",
            records_processed=self.stats["total"],
            records_loaded=self.stats["inserted"] + self.stats["updated"],
            records_rejected=self.stats["unmatched"] + self.stats["errors"],
            error_details={
                "unmatched": self.stats["unmatched"],
                "errors": self.stats["errors"],
            },
        )
        self.session.add(audit)
        self.session.commit()
```

**Critical note on PFF field names:** The PFF scraper returns `"school"` NOT `"college"`. The DB model uses `college`. The fuzzy matcher must map `pff_data["school"]` → candidate `college`.

---

#### 5 — Update Reconciliation Engine

**File to modify:** `data_pipeline/reconciliation/reconciliation_engine.py`

Three changes needed:

**5a. Add `PFF` to `DataSource` enum:**
```python
class DataSource(Enum):
    NFL = "nfl"
    ESPN = "espn"
    CBS = "cbs"
    YAHOO = "yahoo"
    PFF = "pff"          # ← ADD THIS
```

**5b. Add `PFF_GRADES` to `FieldCategory` enum:**
```python
class FieldCategory(Enum):
    BASIC = "basic"
    MEASURABLE = "measurable"
    STATS = "stats"
    RANKINGS = "rankings"
    INJURIES = "injuries"
    PFF_GRADES = "pff_grades"    # ← ADD THIS
```

**5c. Update authority rules in `__init__`:**
```python
# In AUTHORITY_RULES dict, add:
FieldCategory.PFF_GRADES: [DataSource.PFF],
```

**5d. Update `reconcile()` method signature and body:**

The current `reconcile()` signature is `reconcile(self, nfl_data, espn_data, cbs_data)`. Add `pff_data=None` parameter:

```python
def reconcile(self, nfl_data, espn_data, cbs_data, pff_data=None):
```

When `pff_data` is provided and a prospect has a PFF grade match, PFF is authoritative for the grade field — it should override any existing `prospect_grade` value from other sources.

---

#### 6 — Pipeline Integration

**File to modify:** `data_pipeline/orchestration/pipeline_config.py`

Add a new pipeline stage that runs AFTER the PFF scrape stage and calls `PFFGradeLoader`:

```python
# In create_default_pipeline() or equivalent:
from data_pipeline.loaders.pff_grade_loader import PFFGradeLoader

# Register a new stage: PFF_GRADE_LOAD
# This stage should run after PipelineStage.PFF_SCRAPE
# It takes PFF scraper output and loads grades into DB
orchestrator.register_stage(
    PipelineStage.PFF_GRADE_LOAD,   # Add this to PipelineStage enum
    connector=PFFGradeLoadConnector(),
    order=45  # After PFF_SCRAPE (order 40), before RECONCILE (order 50)
)
```

Also add `PFF_GRADE_LOAD` to the `PipelineStage` enum in `data_pipeline/orchestration/pipeline_orchestrator.py`.

Create a thin connector wrapper:

```python
# data_pipeline/orchestration/connectors/pff_grade_connector.py
class PFFGradeLoadConnector(DataConnector):
    def execute(self, context=None) -> list:
        from backend.database.connection import DatabaseManager
        from data_pipeline.loaders.pff_grade_loader import PFFGradeLoader
        
        # Get PFF data from previous stage output (context)
        pff_data = context.get("pff_scrape_output", [])
        if not pff_data:
            logger.warning("No PFF data available for grade loading")
            return []
        
        with DatabaseManager().get_session() as session:
            loader = PFFGradeLoader(session)
            stats = loader.load(pff_data)
        
        return [stats]
```

---

#### 7 — Unit Tests

**File to create:** `tests/unit/test_pff_grade_loader.py`

Cover these scenarios:

| # | Test Case | Expected Outcome |
|---|-----------|-----------------|
| 1 | Exact name+position+college match | `matched=1`, `inserted=1`, confidence ≥ 90 |
| 2 | Fuzzy name match ("Jalen Carter" vs "J. Carter") | matched with confidence 75–90 |
| 3 | No match (completely unknown prospect) | `unmatched=1`, no DB insert |
| 4 | Duplicate PFF entries for same prospect | Second entry updates, `updated=1` |
| 5 | Missing grade field | Skipped by validator, `errors` or filtered |
| 6 | Position mapping (PFF "LT" → DB "OL") | Correct position match |
| 7 | Grade normalization (PFF 91.6 → DB 9.6) | `grade_normalized` = 9.6 |
| 8 | PFF "school" mapped to DB "college" | Match succeeds |
| 9 | Batch with mix of matched/unmatched | Stats reflect correct counts |
| 10 | Audit record written after load | `DataLoadAudit` row exists |
| 11 | Transaction rollback on critical error | No partial data committed |

**Test fixture pattern:** Use `unittest.mock.patch` to mock the DB session, or create an in-memory SQLite session. Follow the pattern in `tests/unit/test_reconciliation.py` (564 lines, class-based).

```python
# tests/unit/test_pff_grade_loader.py
import pytest
from unittest.mock import MagicMock, patch
from data_pipeline.loaders.pff_grade_loader import PFFGradeLoader, MATCH_THRESHOLD_LOW

class TestPFFGradeLoader:
    def setup_method(self):
        self.session = MagicMock()
        self.loader = PFFGradeLoader(self.session)
    
    def _make_pff_prospect(self, name="Travis Hunter", position="CB", school="Colorado", grade="96.2"):
        return {
            "name": name, "position": position, "school": school,
            "class": "Jr.", "height": "6' 1\"", "weight": "185",
            "grade": grade, "scraped_at": "2026-02-12T00:00:00",
        }
    
    def _make_db_prospect(self, id=1, name="Travis Hunter", position="DB", college="Colorado"):
        p = MagicMock()
        p.id = id; p.name = name; p.position = position; p.college = college
        return p
    
    # ... test methods per table above
```

Also add reconciliation-specific tests:

**File to modify:** `tests/unit/test_reconciliation.py`

Add test cases for:
- `DataSource.PFF` is recognized
- `FieldCategory.PFF_GRADES` authority rules resolve to PFF
- When PFF grade conflicts with another source, PFF wins

---

#### 8 — File Checklist

| # | Action | File | Type |
|---|--------|------|------|
| 1 | Create | `data_pipeline/models/prospect_grades.py` | New model |
| 2 | Modify | `backend/database/models.py` | Add relationship |
| 3 | Create | `migrations/versions/XXX_add_prospect_grades_table.py` | Alembic autogenerate |
| 4 | Modify | `data_pipeline/validators/pff_validator.py` | Add position map + grade normalization |
| 5 | Create | `data_pipeline/loaders/pff_grade_loader.py` | Core loader |
| 6 | Modify | `data_pipeline/reconciliation/reconciliation_engine.py` | Add PFF source + authority |
| 7 | Modify | `data_pipeline/orchestration/pipeline_orchestrator.py` | Add PFF_GRADE_LOAD stage |
| 8 | Modify | `data_pipeline/orchestration/pipeline_config.py` | Register new stage |
| 9 | Create | `data_pipeline/orchestration/connectors/pff_grade_connector.py` | Pipeline connector |
| 10 | Create | `tests/unit/test_pff_grade_loader.py` | Unit tests |
| 11 | Modify | `tests/unit/test_reconciliation.py` | Add PFF test cases |

---

#### 9 — Known Gotchas & Warnings

1. **PFF uses `"school"`, DB uses `"college"`** — the fuzzy matcher must map this. Do NOT rename the PFF scraper output key; handle the difference in the loader.

2. **PFF positions are granular** — `LT`, `LG`, `C`, `RG`, `RT`, `DT`, `DE`, `SS`, `FS`. The DB CHECK constraint only allows `QB, RB, FB, WR, TE, OL, DL, EDGE, LB, DB, K, P`. Store the raw PFF position in `grade_position`, but use the mapped position for fuzzy matching.

3. **PFF grade is 0–100** — the existing `prospect_grade` column on `prospects` table is CHECK-constrained to 5.0–10.0. The new `prospect_grades` table should store both raw (`grade_overall`, 0–100) and normalized (`grade_normalized`, 5.0–10.0).

4. **PFF height is a string** like `"6' 5\""` — the loader does NOT need to parse this since we're only loading grades, not updating prospect measurables.

5. **Em-dash `"—"` in PFF data** — the PFF scraper may return `"—"` for missing school/class fields. Treat this as `None`. There is an open bug for this (Bug #4 in `qa_reports/BUGS.md`). If that bug isn't fixed before you start, add a guard: `if value == "—": value = None`.

6. **`DataLoadAudit` model** — already exists in `backend/database/models.py`. Use `source="pff"` and `load_type="grade_integration"`.

7. **Existing `MatchResult` dataclass** — in `data_pipeline/validators/deduplication.py` there is already a `MatchResult` dataclass and `DeduplicationEngine` with `find_match()`. Consider reusing or extending it rather than building matching from scratch. It already uses `rapidfuzz` and has weighted scoring.

8. **Test database** — tests use mocked sessions (no real DB). Follow the pattern in existing tests under `tests/unit/`.

9. **Transaction boundary** — wrap the entire batch load in a single transaction. On error, rollback everything (no partial loads). The `_write_audit()` should commit separately so audit is recorded even on failure.

---

#### 10 — Suggested Implementation Order

1. **Model + migration** (tasks 1–3 in checklist) — get the table created first
2. **Validators** (task 4) — position map + grade normalization, easy to unit test independently
3. **Loader** (task 5) — core fuzzy matching and DB insertion logic
4. **Unit tests** (task 10) — test the loader against mocked data
5. **Reconciliation updates** (tasks 6, 11) — add PFF to the reconciliation engine
6. **Pipeline integration** (tasks 7–9) — wire it into the automated pipeline
7. **End-to-end test** — run `poetry run python -m data_pipeline.orchestration.pipeline_config` and verify grades appear in DB

---

## US-042: PFF Grades in Analytics Endpoints

### User Story
As a **analyst**  
I want to **view PFF grades alongside other prospect metrics**  
So that **I can make holistic evaluations using industry-standard grades**

### Description
Add PFF grades to existing analytics endpoints and create new PFF-specific endpoints for grade-based analysis.

### Acceptance Criteria
- [ ] Endpoint: `GET /api/prospects/:id` includes pff_grade fields
- [ ] New endpoint: `GET /api/analytics/pff-grades/:position` (grade distribution by position)
- [ ] New endpoint: `GET /api/analytics/grade-correlations` (PFF vs. position tier)
- [ ] Grade comparison: PFF grade vs. actual draft position (for historical validation)
- [ ] Grade percentiles: where does prospect's PFF grade rank vs. position group
- [ ] Response time < 500ms (cached)

### Technical Acceptance Criteria
- [ ] SQL queries for grade analytics
- [ ] Materialized views for performance
- [ ] Redis caching (1-day TTL)
- [ ] JSON response formatting

### Tasks
- [ ] PFF grades visible in prospect detail
- [ ] Grade analytics endpoints working
- [ ] Performance meets targets
- [ ] Tests passing

### Effort
- **Backend:** 4 story points
- **Total:** 4 story points

---

### User Story
As a **DevOps engineer**  
I want to **containerize the entire application with Docker**  
So that **the app can be deployed consistently across development, staging, and production environments**

### Description
Create comprehensive Docker setup for the entire application including backend API, data pipeline, CLI tools, and PostgreSQL database. Enable multi-environment deployments with proper volume management, networking, and configuration handling.

### Acceptance Criteria
- [ ] Dockerfile for backend API service (FastAPI)
- [ ] Dockerfile for data pipeline service (ETL worker)
- [ ] Dockerfile for CLI service (optional, can use backend image)
- [ ] docker-compose.yml with all services (API, pipeline, database, redis)
- [ ] Environment variable configuration (.env support)
- [ ] Database initialization and migration on startup
- [ ] Health check endpoints for container orchestration
- [ ] Volume mounts for data persistence (cache, logs, database)
- [ ] Build scripts work on Linux, macOS, Windows
- [ ] Documentation for local development setup with Docker

### Technical Acceptance Criteria
- [ ] Base image: Python 3.11 slim
- [ ] Multi-stage builds for optimization
- [ ] Redis service for caching
- [ ] PostgreSQL service with proper initialization
- [ ] Network isolation between services
- [ ] Proper entrypoint scripts for startup
- [ ] Logging configuration (stdout for containers)
- [ ] Security best practices (non-root user, minimal layers)
- [ ] .dockerignore to exclude unnecessary files
- [ ] Works with poetry dependencies

### Tasks
- **DevOps:** Create Dockerfile for backend API
- **DevOps:** Create Dockerfile for data pipeline
- **DevOps:** Create docker-compose.yml
- **DevOps:** Write container initialization scripts
- **DevOps:** Create comprehensive Docker documentation

### Definition of Done
- [ ] All services start and run successfully
- [ ] Database initializes automatically
- [ ] Services communicate correctly
- [ ] Volumes persist data correctly
- [ ] Environment variables work properly
- [ ] Startup and shutdown graceful
- [ ] Documentation complete

### Effort
- **DevOps:** 5 story points
- **Total:** 5 story points

---

## Sprint 4 Summary

**Total Story Points:** ~22 points (refocused on critical work)

**Priority Focus:**
1. **US-045** (Dockerize - 5 pts) - TOP PRIORITY for deployment readiness
2. **US-040** (PFF Scraper - 7 pts) - Fix critical bug, complete integration
3. **US-041** (Data Integration - 6 pts) - Depends on US-040
4. **US-042** (Analytics Endpoints - 4 pts) - Depends on US-041

**Key Outcomes:**
- ✅ Application containerized with Docker (deployment ready)
- ✅ PFF.com scraper operational & bug fixed
- ✅ PFF grades integrated into database
- ✅ PFF data visible in analytics endpoints

**Moved to Sprint 5:**
- US-043 (Grade Conflict Dashboard - 4 pts)
- US-044 (Data Quality Enhancement - 4 pts)

**Reason:** Focus on critical bug fixes, Dockerization, and core data flow
