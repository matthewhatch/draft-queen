# College Football Reference (CFR) Integration - User Stories

**Sprint:** 4  
**Epic:** Multi-Source Data Integration  
**Related Documents:**
- [Product Strategy](./PRODUCT_STRATEGY_CFR_INTEGRATION.md)
- [Technical Specification](./TECHNICAL_SPEC_CFR_INTEGRATION.md)

---

## Overview

These user stories cover the integration of College Football Reference as a data source. The epic spans 2-3 weeks with phased rollout: scraper → pipeline integration → analytics.

---

## User Story 1: Core CFR Web Scraper

**ID:** US-056  
**Title:** Implement College Football Reference Web Scraper  
**Story Points:** 8  
**Priority:** HIGH  
**Sprint:** 4 (Week 1)

### Acceptance Criteria

- [ ] Scraper successfully fetches 2026 draft class from CFR website
- [ ] Parses player names, positions, schools, and college statistics
- [ ] Handles all position types (QB, RB, WR, TE, OL, DL, EDGE, LB, DB)
- [ ] Extracts 2024-2025 season statistics for each position
- [ ] Implements rate limiting (2-3 second delays)
- [ ] Caches results locally to avoid repeated requests
- [ ] Handles network errors gracefully (retry with exponential backoff)
- [ ] Logs all operations (success, errors, warnings)
- [ ] Unit tests: 100% pass (> 95% code coverage)
- [ ] No external API dependencies required

### Definition of Done

- Code reviewed and approved
- All unit tests passing
- Logging configured and working
- Documentation updated
- Ready for integration testing

### Technical Notes

**Data Points to Extract (by position):**
- QB: Passing yards, TDs, INTs, completion %, QB rating, rushing yards/TDs
- RB: Rushing attempts/yards/TDs, receptions, receiving yards/TDs
- WR: Receptions, receiving yards/TDs, yards per reception
- TE: Receptions, receiving yards/TDs
- OL: Games started, all-conference selections
- DL: Tackles, sacks, TFLs, forced fumbles
- EDGE: Sacks, TFLs, pressures
- LB: Tackles, sacks, TFLs, passes defended, INTs
- DB: Passes defended, INTs, tackles

**See Also:** [Technical Spec - Scraper Architecture](./TECHNICAL_SPEC_CFR_INTEGRATION.md#scraper-architecture)

---

## User Story 2: Prospect Matching Algorithm

**ID:** US-057  
**Title:** Implement CFR-to-Prospect Matching Algorithm  
**Story Points:** 5  
**Priority:** HIGH  
**Sprint:** 4 (Week 1-2)

### Acceptance Criteria

- [ ] Matches CFR players to existing prospects with 95%+ accuracy
- [ ] Primary matching: exact name + college + position
- [ ] Secondary matching: fuzzy name matching (85%+ similarity)
- [ ] Handles name variations (John vs. Johnny, nickname usage)
- [ ] Handles college name variations (TX vs. Texas, A&M vs. Texas A&M)
- [ ] Flags unmatched prospects for manual review
- [ ] Creates audit log of all matching decisions
- [ ] Unit tests demonstrate accuracy on 100+ real examples
- [ ] No false positive matches created
- [ ] Performance: < 100ms per prospect match

### Definition of Done

- Matching algorithm implemented and tested
- Manual QA review of 50 sample matches (spot-check)
- Audit log working correctly
- Documentation with examples
- Ready for pipeline integration

### Matching Quality Metrics

- Exact matches: 85%+
- Fuzzy matches: 10%+
- Manual review queue: < 5%
- False positives: 0%

**See Also:** [Technical Spec - Matching Algorithm](./TECHNICAL_SPEC_CFR_INTEGRATION.md#matching-algorithm)

---

## User Story 3: Database Schema for College Stats

**ID:** US-058  
**Title:** Create `prospect_college_stats` Table and Migration  
**Story Points:** 3  
**Priority:** HIGH  
**Sprint:** 4 (Week 1)

### Acceptance Criteria

- [ ] New table `prospect_college_stats` created with all required columns
- [ ] Columns support all position-specific statistics
- [ ] Foreign key to `prospects` table with CASCADE delete
- [ ] Unique constraint on (prospect_id, season)
- [ ] Proper indexes for query performance
- [ ] Data types appropriate for stats (numeric precision, ranges)
- [ ] Check constraints enforce valid data ranges
- [ ] Alembic migration created and tested
- [ ] Migration runs without errors on staging DB
- [ ] Rollback tested successfully

### Definition of Done

- Migration code reviewed
- Tested on staging database
- Rollback verified
- Schema documentation updated
- Ready for deployment

### Schema Details

See [Technical Spec - Database Schema](./TECHNICAL_SPEC_CFR_INTEGRATION.md#new-table-prospect_college_stats)

---

## User Story 4: CFR Pipeline Integration

**ID:** US-059  
**Title:** Integrate CFR Scraper into Daily Data Pipeline  
**Story Points:** 5  
**Priority:** HIGH  
**Sprint:** 4 (Week 2)

### Acceptance Criteria

- [ ] CFR scraper executes as part of daily pipeline (3 AM)
- [ ] Scraper runs after PFF scraper completes
- [ ] Data validated before insertion
- [ ] Records inserted into `prospect_college_stats` table
- [ ] Unmatched prospects logged and flagged
- [ ] Pipeline handles scraper failures gracefully (fallback to cache)
- [ ] Error recovery tested: network failures, parse errors, matching errors
- [ ] Pipeline monitoring: success/failure status logged
- [ ] Data quality checks pass (> 90% match rate, > 95% data completeness)
- [ ] Full pipeline runs in < 30 minutes

### Definition of Done

- Pipeline integration complete
- End-to-end tested on staging
- Monitoring alerts configured
- Error scenarios tested
- Ready for production deployment

### Monitoring & Alerts

Alert if:
- Match rate falls below 90%
- Parse error rate exceeds 5%
- Data quality score < 95%
- Scraper runtime > 25 minutes

**See Also:** [Technical Spec - Pipeline Integration](./TECHNICAL_SPEC_CFR_INTEGRATION.md#pipeline-integration)

---

## User Story 5: API Endpoints for College Stats

**ID:** US-060  
**Title:** Add College Stats Query Endpoints to REST API  
**Story Points:** 5  
**Priority:** MEDIUM  
**Sprint:** 4 (Week 2-3)

### Acceptance Criteria

- [ ] `GET /api/prospects/:id/college-stats` returns prospect college statistics
- [ ] Response includes all seasons (2024-2025 minimum)
- [ ] Response includes derived metrics (percentiles, efficiency rating)
- [ ] `GET /api/prospects/query` supports college stats filters
- [ ] Filters work: college_yards_min, college_tds_min, college_tds_max, etc.
- [ ] Results returned in < 500ms (cached)
- [ ] API documentation (Swagger) updated
- [ ] Error handling: proper HTTP status codes and messages
- [ ] Integration tests pass (> 95% coverage)
- [ ] Performance tested with 500+ prospect queries

### Definition of Done

- Endpoints implemented and tested
- Documentation updated
- Performance validated
- Ready for frontend integration

### API Response Format

**College Stats Response:**
```json
{
  "prospect_id": "uuid",
  "name": "John Doe",
  "position": "QB",
  "seasons": [
    {
      "year": 2025,
      "school": "Texas A&M",
      "games_played": 13,
      "games_started": 13,
      "passing_yards": 4500,
      "passing_tds": 35,
      "interceptions": 8,
      "completion_pct": 67.5,
      "qb_rating": 8.6
    }
  ]
}
```

**See Also:** [Technical Spec - API Integration](./TECHNICAL_SPEC_CFR_INTEGRATION.md#api-integration)

---

## User Story 6: Grade vs. Production Analysis Notebook

**ID:** US-061  
**Title:** Create "Grade vs. Production" Analytics Notebook  
**Story Points:** 5  
**Priority:** MEDIUM  
**Sprint:** 4 (Week 3)

### Acceptance Criteria

- [ ] Notebook demonstrates comparing PFF grade to college production
- [ ] Includes prospects with elite grade but modest production
- [ ] Includes prospects with modest grade but elite production
- [ ] Visualizations: scatter plots (grade vs. key stats)
- [ ] Statistics: correlation coefficients (grade ↔ college stats)
- [ ] Position-specific analysis (QB, RB, WR separately)
- [ ] Identifies statistical outliers
- [ ] Can filter by position, school, or other criteria
- [ ] Explanatory text and markdown cells
- [ ] Production-ready (no placeholder code)

### Definition of Done

- Notebook complete and tested
- Uses only existing API endpoints (no direct DB queries)
- Includes 3+ useful analyses
- Documentation complete
- Ready for analyst use

### Example Analyses

1. **Draft Grade vs. Production:** Scatter plot of PFF grade (x-axis) vs. college passing yards (y-axis). Highlight outliers.
2. **Position Benchmarks:** Summary stats for position (QB, RB, WR) showing avg production by grade tier.
3. **System Players:** Identify QBs with high college stats but modest PFF grades (system QBs hypothesis).

---

## User Story 7: Data Quality Validation & Reporting

**ID:** US-062  
**Title:** Build CFR Data Quality Monitoring and Reporting  
**Story Points:** 3  
**Priority:** MEDIUM  
**Sprint:** 4 (Week 2-3)

### Acceptance Criteria

- [ ] Post-scrape validation checks data completeness
- [ ] Validation reports generated daily
- [ ] Monitors matching accuracy (target: 95%+)
- [ ] Monitors parse error rate (target: < 5%)
- [ ] Monitors data completeness (target: > 95% non-null fields)
- [ ] Alerts if any metric drops below threshold
- [ ] Unmatched prospects logged for manual review
- [ ] JSON report generated daily with metrics
- [ ] Metrics accessible via API endpoint
- [ ] Documentation for interpreting metrics

### Definition of Done

- Validation logic implemented
- Monitoring working
- Alerts configured
- Reports accessible
- Documentation complete

### Quality Metrics to Track

```json
{
  "total_scraped": 500,
  "successfully_matched": 475,
  "match_accuracy": 0.95,
  "parse_errors": 2,
  "data_quality_score": 0.98,
  "timestamp": "2026-02-15T09:30:00Z"
}
```

---

## User Story 8: Documentation & Team Training

**ID:** US-063  
**Title:** Document CFR Integration and Train Team  
**Story Points:** 2  
**Priority:** MEDIUM  
**Sprint:** 4 (Week 3)

### Acceptance Criteria

- [ ] Developer guide created: how CFR scraper works
- [ ] API documentation updated with college stats endpoints
- [ ] Architecture decision record (ADR) created
- [ ] Data dictionary created for college stats fields
- [ ] Runbook created: monitoring and troubleshooting CFR issues
- [ ] Team training completed (recorded or live)
- [ ] FAQ document created for analysts
- [ ] All documentation in docs/ folder
- [ ] Reviewed and approved by team

### Definition of Done

- All documentation written and reviewed
- Team training completed
- No open questions on CFR integration

### Documents to Create/Update

- `docs/architecture/0011-cfr-data-source.md` (new ADR)
- `docs/guides/CFR_INTEGRATION_GUIDE.md` (new implementation guide)
- `docs/TROUBLESHOOTING_CFR.md` (new troubleshooting guide)
- Update `docs/README.md` navigation
- Update data dictionary

---

## User Story 9: Production Deployment & Validation

**ID:** US-064  
**Title:** Deploy CFR Integration to Production and Validate  
**Story Points:** 3  
**Priority:** HIGH  
**Sprint:** 4 (Week 3)

### Acceptance Criteria

- [ ] Database migration applied to production
- [ ] CFR scraper deployed to production
- [ ] First production run successful (2026 draft class loaded)
- [ ] Matching accuracy verified: 95%+
- [ ] Data quality checks pass
- [ ] Unmatched prospects reviewed by analyst
- [ ] API endpoints tested in production
- [ ] Performance validated (queries < 500ms)
- [ ] Monitoring and alerting working
- [ ] Rollback plan tested and ready
- [ ] Status communicated to team

### Definition of Done

- Production deployment successful
- Validation passed
- Team notified
- Monitoring active

### Pre-Deployment Checklist

- [ ] All tests passing
- [ ] Code reviewed
- [ ] Database backup taken
- [ ] Rollback plan documented
- [ ] Monitoring configured
- [ ] On-call engineer briefed
- [ ] Deployment window scheduled (off-peak)
- [ ] Stakeholders notified

---

## User Story 10 (Future): Advanced CFR Analytics

**ID:** US-065  
**Title:** Develop Advanced CFR Analytics (Future Spike)  
**Story Points:** 13  
**Priority:** LOW  
**Sprint:** 5 (Future)

### Description

Future work to leverage CFR data for predictive modeling and advanced analytics:
- Percentile rankings (position-specific, year-over-year)
- Efficiency metrics (yards per play, TD rate)
- Historical correlation analysis (college stats → draft success)
- Model training (college stats + combine + grade → draft position prediction)

### Acceptance Criteria

- [ ] Percentile calculation implemented and cached
- [ ] Efficiency metrics calculated for all positions
- [ ] Historical analysis (2023-2026) complete
- [ ] Predictive model trained and validated
- [ ] Jupyter notebook demonstrating predictions
- [ ] API endpoints for advanced metrics

---

## Dependency & Sequencing

```
┌─────────────────────────────────────────────────────────┐
│ User Story Dependencies (Sprint 4)                        │
└─────────────────────────────────────────────────────────┘

Week 1:
├─ US-056 (CFR Scraper) ────────────┐
├─ US-057 (Matching) ────────────────┤─→ US-059 (Pipeline)
├─ US-058 (Database Schema) ─────────┤

Week 2-3:
├─ US-059 (Pipeline) ───────→ US-060 (API)
├─ US-062 (Quality Monitoring)

Week 3:
├─ US-060 (API) ────────→ US-061 (Notebooks)
├─ US-063 (Documentation)
└─ US-064 (Deployment) ← All above stories
```

---

## Testing Strategy

### Unit Tests (US-056, US-057, US-058)
- Scraper parsing (HTML → Python dict)
- Matching algorithm accuracy
- Database schema validation
- Total: 50+ unit tests

### Integration Tests (US-059)
- End-to-end pipeline execution
- Database insertion
- No duplicates created
- Idempotent execution
- Error recovery
- Total: 15+ integration tests

### API Tests (US-060)
- Endpoint response format
- Filter logic
- Performance (response time < 500ms)
- Error handling
- Total: 20+ API tests

### E2E Tests (US-064)
- Production scraper execution
- Data quality validation
- Analyst queries working
- No existing data regression

---

## Success Metrics

### Quantitative
- ✅ 95%+ prospect matching accuracy
- ✅ < 5% parse error rate
- ✅ API response time < 500ms
- ✅ Pipeline runtime < 30 minutes
- ✅ 2000+ prospects with college stats

### Qualitative
- ✅ Analysts can answer: "Which prospects overperformed/underperformed relative to grade?"
- ✅ Analysts find the new data valuable
- ✅ No regression in existing platform functionality
- ✅ Team confident in data quality

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Low matching accuracy | Data gaps | Fuzzy matching + manual review |
| CFR HTML changes | Scraper breaks | Monitoring, version control, quick fixes |
| Performance issues | Slow queries | Caching, indexes, materialized views |
| Data quality | Incorrect decisions | Validation checks, alerts, audit trail |

---

## Effort Estimate

| User Story | Points | Owner | Duration |
|-----------|--------|-------|----------|
| US-056 (Scraper) | 8 | Data Eng | 3-4 days |
| US-057 (Matching) | 5 | Data Eng | 2-3 days |
| US-058 (Schema) | 3 | Backend | 1 day |
| US-059 (Pipeline) | 5 | Data Eng | 2-3 days |
| US-060 (API) | 5 | Backend | 2-3 days |
| US-061 (Notebooks) | 5 | Data Analyst | 2-3 days |
| US-062 (Validation) | 3 | Data Eng | 1-2 days |
| US-063 (Docs) | 2 | PM/Team | 1 day |
| US-064 (Deployment) | 3 | Backend | 1 day |
| **Total** | **39** | **Team** | **2-3 weeks** |

---

## Roll-Out Plan

**Week 1:** Development
- Scraper, matching, schema (US-056, US-057, US-058)

**Week 2:** Integration
- Pipeline integration, API endpoints (US-059, US-060)
- Quality monitoring (US-062)

**Week 3:** Validation & Launch
- Notebooks (US-061)
- Documentation (US-063)
- Production deployment (US-064)

**Post-Launch:** Monitoring
- QA validation
- Analyst feedback
- Performance optimization

