# Sprint 4-5 Story Prioritization: ETL First, CFR to Backlog

**Date:** February 15, 2026  
**Status:** Prioritized Story Roadmap  
**Decision:** ETL architecture is foundational; CFR can proceed in parallel once ETL foundation is ready

---

## 📌 Priority Strategy

**Rationale:**
- ETL architecture is **foundational** for all future data sources
- CFR integration can proceed in **parallel** once ETL staging tables exist
- Both initiatives use same transformation patterns
- Starting ETL now unblocks CFR later

**Timeline:**
- **Sprint 4 (Week 1-2):** ETL Foundation + Transformers
- **Sprint 4-5 (Week 2-4):** ETL Orchestration + CFR (parallel)
- **Sprint 5 (Week 3-4):** Analytics + Deployment

---

## 🎯 SPRINT 4 - PRIORITY STORIES (ETL)

### Phase 1: ETL Foundation (Week 1)

**ETL-001: Create Staging Tables**
- **Story Points:** 5
- **Priority:** CRITICAL
- **Owner:** Backend Engineer
- **Description:** Create all source-specific staging tables (PFF, NFL, CFR, Yahoo, ESPN)
- **Acceptance Criteria:**
  - [ ] pff_staging table created with all columns
  - [ ] nfl_combine_staging table created
  - [ ] cfr_staging table created
  - [ ] yahoo_staging table created
  - [ ] espn_staging table created (schema only)
  - [ ] All tables have proper indexes
  - [ ] Data hashing columns present
  - [ ] Extraction tracking (extraction_id, timestamp)
  - [ ] Migration tested on staging DB
  - [ ] Rollback verified

**Definition of Done:**
- Migration code reviewed
- All tables tested with sample data
- Documentation updated
- Ready for transformer phase

---

**ETL-002: Create Canonical Tables**
- **Story Points:** 5
- **Priority:** CRITICAL
- **Owner:** Backend Engineer
- **Description:** Create canonical business entity tables (prospect_core, prospect_grades, measurements, college_stats, lineage)
- **Acceptance Criteria:**
  - [ ] prospect_core table created (identity hub)
  - [ ] prospect_grades table created (multi-source)
  - [ ] prospect_measurements table created
  - [ ] prospect_college_stats table created
  - [ ] data_lineage table created (audit trail)
  - [ ] All foreign keys and constraints in place
  - [ ] Proper indexes for query performance
  - [ ] Migration tested
  - [ ] Rollback verified

**Definition of Done:**
- Migration code reviewed
- Schema documentation complete
- Ready for transformer phase

---

**ETL-003: Create Base Transformer Framework**
- **Story Points:** 5
- **Priority:** CRITICAL
- **Owner:** Data Engineer
- **Description:** Abstract base classes for all transformers with common patterns
- **Acceptance Criteria:**
  - [ ] BaseTransformer abstract class created
  - [ ] Common validation methods
  - [ ] Lineage recording utilities
  - [ ] Error handling patterns
  - [ ] Logging configured
  - [ ] Unit tests > 95% coverage
  - [ ] Code examples for inheritance
  - [ ] Documentation complete

**Definition of Done:**
- Code reviewed
- All unit tests passing
- Ready for source-specific transformer implementation

---

**ETL-004: Create Lineage Recorder**
- **Story Points:** 3
- **Priority:** CRITICAL
- **Owner:** Data Engineer
- **Description:** Utility for recording data lineage (field changes, sources, transformations)
- **Acceptance Criteria:**
  - [ ] LineageRecorder class created
  - [ ] Tracks source_system, field_name, old_value, new_value
  - [ ] Records transformation_rule applied
  - [ ] Timestamps recorded automatically
  - [ ] Can query "where did this value come from?"
  - [ ] Unit tests passing
  - [ ] Performance: < 100ms per record
  - [ ] Documentation complete

**Definition of Done:**
- Code reviewed
- Tested with mock data
- Performance validated
- Ready for transformer use

---

### Phase 2: ETL Transformers (Week 1-2)

**ETL-005: Implement PFF Transformer**
- **Story Points:** 5
- **Priority:** HIGH
- **Owner:** Data Engineer
- **Description:** Transform PFF staging data to canonical models
- **Acceptance Criteria:**
  - [ ] Read from pff_staging
  - [ ] Normalize grade (0-100 → 5.0-10.0)
  - [ ] Prospect matching (PFF ID priority)
  - [ ] Record lineage for all changes
  - [ ] Handle edge cases (missing fields, invalid grades)
  - [ ] Write to prospect_core + prospect_grades
  - [ ] Unit tests with real PFF data
  - [ ] Performance: < 100ms per prospect
  - [ ] 100% code coverage

**Definition of Done:**
- Code reviewed
- All unit tests passing
- Tested with PFF staging data
- Ready for integration

---

**ETL-006: Implement NFL Transformer**
- **Story Points:** 5
- **Priority:** HIGH
- **Owner:** Data Engineer
- **Description:** Transform NFL staging to canonical measurements
- **Acceptance Criteria:**
  - [ ] Read from nfl_combine_staging
  - [ ] Parse height "6-2" → 74 inches
  - [ ] Validate measurements (ranges, types)
  - [ ] Prospect matching (fuzzy match)
  - [ ] Record lineage (source, date, test_type)
  - [ ] Handle test invalidations
  - [ ] Write to prospect_measurements
  - [ ] Unit tests with sample combine data
  - [ ] Performance: < 100ms per prospect

**Definition of Done:**
- Code reviewed
- All tests passing
- Ready for integration

---

**ETL-007: Implement CFR Transformer**
- **Story Points:** 5
- **Priority:** HIGH
- **Owner:** Data Engineer
- **Description:** Transform CFR staging to canonical college stats
- **Acceptance Criteria:**
  - [ ] Read from cfr_staging
  - [ ] Validate position-specific stats
  - [ ] Prospect matching (fuzzy match)
  - [ ] Normalize stats (per position)
  - [ ] Record lineage
  - [ ] Write to prospect_college_stats
  - [ ] Handle partial seasons
  - [ ] Unit tests with CFR data
  - [ ] Performance: < 100ms per prospect

**Definition of Done:**
- Code reviewed
- All tests passing
- Ready for integration

---

**ETL-008: Create Data Quality Validation**
- **Story Points:** 3
- **Priority:** HIGH
- **Owner:** Data Engineer
- **Description:** Post-transformation validation checks
- **Acceptance Criteria:**
  - [ ] Validate prospect_core (no duplicates, required fields)
  - [ ] Validate grades (range 5.0-10.0)
  - [ ] Validate measurements (height/weight ranges)
  - [ ] Validate college stats (position-specific ranges)
  - [ ] Generate quality metrics (completeness %, error count)
  - [ ] Alert if quality < 95%
  - [ ] Unit tests passing
  - [ ] Documentation complete

**Definition of Done:**
- Code reviewed
- All tests passing
- Ready for orchestrator

---

### Phase 3: ETL Orchestration (Week 2)

**ETL-009: Create ETL Orchestrator**
- **Story Points:** 8
- **Priority:** CRITICAL
- **Owner:** Backend Engineer
- **Description:** Main pipeline orchestrator managing all stages
- **Acceptance Criteria:**
  - [ ] Execute extraction (parallel async)
  - [ ] Execute staging (insert raw data)
  - [ ] Execute validation (quality checks)
  - [ ] Execute transformation (all transformers)
  - [ ] Execute merge (deduplication)
  - [ ] Execute load (atomic transaction)
  - [ ] Record lineage
  - [ ] Publish materialized views
  - [ ] Handle errors gracefully
  - [ ] Logging comprehensive
  - [ ] Performance: < 30 minutes full pipeline
  - [ ] Idempotent (can re-run safely)

**Definition of Done:**
- Code reviewed
- End-to-end tested
- Performance validated
- Ready for APScheduler integration

---

**ETL-010: Integrate ETL with APScheduler**
- **Story Points:** 3
- **Priority:** HIGH
- **Owner:** Backend Engineer
- **Description:** Schedule ETL pipeline to run daily
- **Acceptance Criteria:**
  - [ ] ETL runs daily at 3 AM UTC
  - [ ] Logging of execution time
  - [ ] Monitoring alerts configured
  - [ ] Graceful handling of overlapping runs
  - [ ] Rollback capability
  - [ ] Tested in staging environment
  - [ ] Documentation complete

**Definition of Done:**
- Deployed to staging
- Tested with real data
- Monitoring active
- Ready for production

---

**ETL-011: Create Monitoring & Alerts**
- **Story Points:** 3
- **Priority:** HIGH
- **Owner:** Backend Engineer
- **Description:** Monitor ETL execution and data quality
- **Acceptance Criteria:**
  - [ ] Log extraction duration
  - [ ] Log transformation duration
  - [ ] Track quality metrics per source
  - [ ] Alert if pipeline duration > 30 min
  - [ ] Alert if quality score < 95%
  - [ ] Alert if error rate > 5%
  - [ ] Dashboard queries created
  - [ ] Documentation complete

**Definition of Done:**
- Monitoring queries working
- Alerts tested
- Documentation complete
- Ready for operations

---

## 📅 SPRINT 5 - PRIORITY STORIES (ETL Analytics + CFR)

### Phase 4: Analytics & API (Week 3-4)

**ETL-012: Create Materialized Views for Analytics**
- **Story Points:** 5
- **Priority:** HIGH
- **Owner:** Backend Engineer
- **Description:** Create summary views for efficient querying
- **Acceptance Criteria:**
  - [ ] vw_prospect_summary (canonical + all sources)
  - [ ] vw_prospect_quality_scores (per source)
  - [ ] vw_position_benchmarks (stat aggregates)
  - [ ] vw_prospect_outliers (statistical anomalies)
  - [ ] All views refresh nightly
  - [ ] Indexes on common filter columns
  - [ ] Query performance < 500ms

**Definition of Done:**
- Views created and tested
- Refresh times validated
- API ready to use

---

**ETL-013: Create Analytics API Endpoints**
- **Story Points:** 5
- **Priority:** HIGH
- **Owner:** Backend Engineer
- **Description:** API endpoints for analytics queries
- **Acceptance Criteria:**
  - [ ] `GET /api/analytics/prospect-summary/:id`
  - [ ] `GET /api/analytics/position-benchmarks/:position`
  - [ ] `GET /api/analytics/quality-scores`
  - [ ] `GET /api/analytics/lineage/:prospect_id/:field`
  - [ ] Performance < 500ms
  - [ ] Error handling
  - [ ] Documentation (Swagger)
  - [ ] Integration tests passing

**Definition of Done:**
- Endpoints tested
- Documentation complete
- Ready for frontend

---

**ETL-014: ETL Operational Runbook**
- **Story Points:** 3
- **Priority:** MEDIUM
- **Owner:** PM/Backend Engineer
- **Description:** Documentation for operations team
- **Acceptance Criteria:**
  - [ ] Troubleshooting guide created
  - [ ] Common issues documented
  - [ ] Recovery procedures documented
  - [ ] Escalation procedures documented
  - [ ] Monitoring checklist created
  - [ ] On-call playbook created

**Definition of Done:**
- Documentation complete
- Team trained
- Ready for production

---

## 🚀 BACKLOG - CFR & OTHER STORIES (Move to Sprint 4-5 if ETL unblocked)

### CFR Integration Stories (Can start Week 2 once ETL staging exists)

**CFR-001 (was US-056): Core CFR Web Scraper**
- Story Points: 8
- Priority: HIGH (backlog - unblocked after ETL-002)
- Owner: Data Engineer
- Dependencies: ETL-002 (staging tables created)

**CFR-002 (was US-057): Prospect Matching Algorithm**
- Story Points: 5
- Priority: HIGH (backlog - unblocked after ETL-005)
- Owner: Data Engineer
- Dependencies: CFR-001

**CFR-003 (was US-058): Database Schema**
- Story Points: 3
- Priority: HIGH
- Owner: Backend Engineer
- Status: Can proceed in parallel with ETL (no dependency)

**CFR-004 (was US-059): CFR Pipeline Integration**
- Story Points: 5
- Priority: MEDIUM (backlog - unblocked after ETL-009)
- Owner: Data Engineer
- Dependencies: ETL-009 (orchestrator)

**CFR-005 (was US-060): API Endpoints**
- Story Points: 5
- Priority: MEDIUM (backlog)
- Owner: Backend Engineer
- Dependencies: CFR-004

**CFR-006 (was US-061): Analytics Notebooks**
- Story Points: 5
- Priority: MEDIUM (backlog)
- Owner: Data Analyst
- Dependencies: ETL-013 (analytics API)

**CFR-007 (was US-062): Data Quality Validation**
- Story Points: 3
- Priority: MEDIUM (backlog)
- Owner: Data Engineer
- Dependencies: CFR-004

**CFR-008 (was US-063): Documentation & Training**
- Story Points: 2
- Priority: LOW (backlog)
- Owner: PM/Team

**CFR-009 (was US-064): Production Deployment**
- Story Points: 3
- Priority: MEDIUM (backlog)
- Owner: Backend Engineer
- Dependencies: All CFR stories

**CFR-010 (was US-065): Advanced Analytics (Future)**
- Story Points: 13
- Priority: LOW (future spike)
- Owner: Data Analyst
- Timeline: Post-Sprint 5

---

## 📊 Story Point Summary

### Sprint 4 (ETL - Priority)
| Phase | Stories | Points | Duration |
|-------|---------|--------|----------|
| Foundation | ETL-001 to ETL-004 | 18 | Week 1 |
| Transformers | ETL-005 to ETL-008 | 18 | Week 1-2 |
| Orchestration | ETL-009 to ETL-011 | 14 | Week 2 |
| **Sprint 4 Total** | **11 stories** | **50 points** | **2 weeks** |

### Sprint 5 (ETL Analytics + CFR Backlog - Ready to pull)
| Phase | Stories | Points | Duration |
|-------|---------|--------|----------|
| Analytics | ETL-012 to ETL-014 | 13 | Week 3-4 |
| CFR (if capacity) | CFR-001 to CFR-009 | 39 | Week 3-4 (parallel) |
| **Sprint 5 Total** | **12 stories** | **52 points** | **2 weeks** |

---

## 🎯 Parallelization Strategy

```
Sprint 4 Timeline:
┌─────────────────────────────────────────────────────────┐
│ Week 1:                                                 │
│ ├─ Backend: ETL-001, ETL-002 (staging + canonical)     │
│ ├─ Data Eng: ETL-003, ETL-004 (base framework)         │
│ └─ All: Review & test                                   │
│                                                         │
│ Week 2:                                                 │
│ ├─ Data Eng: ETL-005, ETL-006, ETL-007 (transformers) │
│ ├─ Backend: ETL-009, ETL-010, ETL-011 (orchestrator)  │
│ ├─ Data Eng: ETL-008 (validation)                      │
│ └─ All: Integration testing                            │
│                                                         │
│ Week 3 (if ready):                                     │
│ ├─ Data Eng: CFR-001 (scraper) [PARALLEL]             │
│ ├─ Backend: ETL-012, ETL-013 (analytics API)          │
│ └─ All: Integration testing                            │
└─────────────────────────────────────────────────────────┘
```

---

## ✅ Rationale for Prioritization

### Why ETL First?
1. **Foundational:** All data sources (PFF, NFL, CFR, Yahoo, ESPN) use same infrastructure
2. **Scalable:** Adding sources requires no schema changes once foundation exists
3. **Unblocks Future:** Phase 5 analytics depend on ETL lineage and canonical models
4. **Enterprise-Ready:** Proper data warehouse foundation for potential commercialization

### Why CFR to Backlog?
1. **Not Blocking:** Can proceed in parallel once ETL staging exists
2. **Reuses Framework:** CFR transformer uses same patterns as PFF/NFL
3. **Lower Priority:** Nice-to-have vs. must-have (ETL is must-have)
4. **Flexible Timing:** Can start Week 2 without impacting ETL delivery

### Win-Win Approach
- **Week 1:** Build ETL foundation (no blocking)
- **Week 2:** Parallel work (ETL transformers + CFR scraper)
- **Week 3:** Integrate (CFR into ETL pipeline)
- **Week 4:** Analytics & deployment

---

## 🚀 Success Criteria

### ETL Success (Sprint 4)
- ✅ All 11 ETL stories complete
- ✅ 50+ story points delivered
- ✅ Pipeline runs daily successfully
- ✅ Data quality > 95%
- ✅ Zero regressions in existing APIs

### CFR Success (Sprint 4-5)
- ✅ Stories 1-9 complete (39 points)
- ✅ 95%+ prospect matching
- ✅ All college stats in database
- ✅ API endpoints working
- ✅ Integrated with ETL pipeline

---

## 📋 Next Steps

1. **This Week:** Review prioritization with team
2. **Next Week:** Create detailed Sprint 4 task breakdown (ETL stories)
3. **Sprint Planning:** Assign owners, estimate remaining details
4. **Sprint Kickoff:** Start ETL Phase 1 (staging + canonical tables)

---

**Prioritization Complete**  
**Status:** Ready for Sprint Planning  
**Date:** February 15, 2026

