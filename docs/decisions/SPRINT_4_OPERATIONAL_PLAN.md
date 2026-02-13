# Sprint 4 Launch: Operational Implementation Plan
**Start Date:** February 10, 2026  
**Duration:** 2 weeks (Mar 24 - Apr 6)  
**Focus:** PFF Scraper + Data Integration  
**Total Points:** 7 + 6 = 13 story points

---

## 🎯 Sprint Objectives

### Primary: US-040 - PFF.com Scraper Implementation (7 pts)
- Build production-ready Playwright-based web scraper
- Extract prospect grades, rankings, position metrics
- Handle pagination and data validation
- 90%+ test coverage with fixtures
- Rate-limiting compliance (3-5s delays)

### Secondary: US-041 - PFF Data Integration (6 pts)
- Design `prospect_grades` database schema
- Implement fuzzy matching for prospect reconciliation
- Build reconciliation rules framework
- Integrate with ETL pipeline scheduler

---

## 📋 Task Breakdown - Operational Sequence

### Phase 1: Scraper Implementation (US-040)
**Target:** Days 1-5  
**Deliverable:** Working scraper with 90%+ test coverage

#### 1.1 Finalize Scraper Code
- [ ] Convert existing PoC to production version
- [ ] Add comprehensive error handling
- [ ] Implement rate limiting (3-5s delays)
- [ ] Add logging (timestamps, counts)
- [ ] Cache fallback mechanism
- **Files:** `data_pipeline/scrapers/pff_scraper.py`
- **Status:** PoC exists, needs hardening

#### 1.2 Create HTML Test Fixtures
- [ ] Scrape sample pages (1-3 actual pages)
- [ ] Save as HTML fixtures in `tests/fixtures/pff/`
- [ ] Include edge cases (missing fields, special characters)
- [ ] Document fixture purpose and expectations
- **Files:** `tests/fixtures/pff/page_1.html`, `page_2.html`, etc.
- **Estimated:** 1-2 hours

#### 1.3 Grade Validation Framework
- [ ] Validate grade range (0-100 scale)
- [ ] Validate rankings (sequential, no gaps)
- [ ] Check position codes (CB, EDGE, DT, etc.)
- [ ] Handle partial/missing data gracefully
- **File:** `data_pipeline/validators/pff_validator.py`
- **Estimated:** 2-3 hours

#### 1.4 Unit Tests (90%+ Coverage)
- [ ] Parse tests (with HTML fixtures)
- [ ] Validation tests (grade ranges, rankings)
- [ ] Rate limiting tests
- [ ] Cache fallback tests
- [ ] Error handling tests
- **File:** `tests/unit/test_pff_scraper.py`
- **Estimated:** 4-6 hours

#### 1.5 Pipeline Integration
- [ ] Add to data pipeline orchestrator
- [ ] Create PFF scraper stage
- [ ] Set up daily scheduling
- [ ] Integration tests
- **Files:** `data_pipeline/orchestration/pipeline_orchestrator.py`
- **Estimated:** 2-3 hours

**Phase 1 Total:** ~12-16 hours (1.5-2 days)

---

### Phase 2: Data Integration (US-041)
**Target:** Days 5-9  
**Deliverable:** Schema + reconciliation logic + integration

#### 2.1 Database Schema Design
- [ ] Design `prospect_grades` table:
  - `id`, `prospect_id`, `source`, `grade_overall`, `grade_position`, `grade_date`
  - Composite index: `(prospect_id, source, grade_date)`
  - Audit columns: `created_at`, `updated_by`
- [ ] Design reconciliation rules table
- **File:** Migration script in `migrations/versions/`
- **Estimated:** 1-2 hours

#### 2.2 Alembic Migration
- [ ] Create migration file
- [ ] Upgrade script (create tables, indexes)
- [ ] Downgrade script (rollback)
- [ ] Test migration locally
- **File:** `migrations/versions/xxxxx_add_prospect_grades.py`
- **Estimated:** 1 hour

#### 2.3 Fuzzy Matching Implementation
- [ ] Use `rapidfuzz` for name matching
- [ ] Match: name + position + college
- [ ] Handle variations (abbreviations, nicknames)
- [ ] Threshold tuning (>85% match confidence)
- **File:** `data_pipeline/matching/prospect_matcher.py`
- **Estimated:** 3-4 hours

#### 2.4 Grade Reconciliation Logic
- [ ] Define reconciliation rules (PFF authoritative for grades)
- [ ] Handle conflicts between sources
- [ ] Audit trail logging
- [ ] Batch insert with rollback on error
- **File:** `data_pipeline/reconciliation/grade_reconciler.py`
- **Estimated:** 3-4 hours

#### 2.5 Pipeline Integration
- [ ] Add grade integration to orchestrator
- [ ] Set daily update cycle
- [ ] Error recovery mechanism
- [ ] Integration tests
- **Estimated:** 2-3 hours

**Phase 2 Total:** ~12-16 hours (1.5-2 days)

---

## 🔧 Implementation Order (Start Now)

### Week 1 Priority (High Value, Blockers)
1. **1.1** Finalize scraper code (today/tomorrow)
2. **1.2** Create HTML test fixtures (parallel)
3. **1.3** Grade validation (can start now)
4. **1.4** Unit tests (as code stabilizes)
5. **2.1** Database schema design (parallel)

### Week 2 Priority (Integration)
6. **1.5** Pipeline integration
7. **2.2** Alembic migration
8. **2.3** Fuzzy matching
9. **2.4** Reconciliation logic
10. **2.5** Pipeline integration + testing

---

## ✅ Definition of Done for Sprint 4

### Code Quality
- [ ] PFF scraper at 90%+ test coverage
- [ ] All tests passing
- [ ] No linting errors (pylint/flake8)
- [ ] Type hints on all functions
- [ ] Docstrings complete

### Functionality
- [ ] Scraper extracts all 5+ data fields
- [ ] Grade validation working
- [ ] Fuzzy matching tested (>85% accuracy)
- [ ] Reconciliation rules enforced
- [ ] Rate limiting working (3-5s delays)
- [ ] Error fallback to cache

### Integration
- [ ] Pipeline orchestrator includes PFF stage
- [ ] Daily scheduler running
- [ ] Database migrations applied
- [ ] Audit trail logging working
- [ ] Performance: <3 min for full scrape

### Documentation
- [ ] Code comments and docstrings
- [ ] HTML fixture documentation
- [ ] API documentation for new DB tables
- [ ] Reconciliation rules documented

---

## 📊 Success Metrics

| Metric | Target | Status |
|--------|--------|--------|
| **Test Coverage** | 90%+ | Not started |
| **Scraper Performance** | <3 min | PoC works |
| **Data Extraction** | 100+ prospects | Demo works |
| **Fuzzy Match Accuracy** | >85% | To implement |
| **Error Recovery** | 100% | To implement |
| **Daily Uptime** | 99%+ | To implement |

---

## 🚀 Ready to Begin

**Starting Point:**
- ✅ PoC code exists: `data_pipeline/scrapers/pff_scraper_playwright.py`
- ✅ Spike complete with architecture validated
- ✅ Playwright installed in dependencies
- ✅ BeautifulSoup4 available
- ✅ Database migrations framework in place

**First Action:**
1. Start with **Task 1.1** (finalize scraper)
2. Create production version from PoC
3. Add error handling, logging, caching
4. Ready to move to testing phase

**Questions to clarify:**
- Database credentials/access for prospect_grades table?
- Scheduler preference (APScheduler already configured)?
- Rate limiting: Hard 3-5s or adaptive?
- Reconciliation priority: PFF authoritative or weighted average?

---

*Sprint 4 Launch Ready - Awaiting start signal*
