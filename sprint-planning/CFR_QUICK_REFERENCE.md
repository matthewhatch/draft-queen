# CFR Integration - Quick Reference Guide for Team

**Date:** February 15, 2026  
**For:** Engineering Team, Data Analyst, PM  
**Purpose:** One-page overview of College Football Reference integration initiative

---

## What Are We Doing?

Adding **College Football Reference (CFR)** as a data source to provide college performance statistics alongside PFF grades.

---

## Why?

| Gap | Problem | CFR Solution |
|-----|---------|-------------|
| No college stats | Can't evaluate production vs. grade | Scrape CFR for comprehensive college stats |
| System players hidden | Can't identify good stats + modest grade | Compare college performance to PFF grade |
| Limited analytics | Can't predict NFL success from college | Foundation for predictive models |

---

## Timeline

- **Planning:** Feb 15-22 (this week + next)
- **Sprint 4:** ~3 weeks (estimated mid-March)
  - Week 1: Scraper + DB (Data Eng + Backend)
  - Week 2: Pipeline + API (Data Eng + Backend)
  - Week 3: Analytics + Deploy (Team)
- **Launch:** Early-to-Mid April

---

## What Needs to Happen

### Data Engineer
1. Build CFR web scraper (US-056, 8 pts)
2. Implement matching algorithm (US-057, 5 pts)
3. Integrate into pipeline (US-059, 5 pts)
4. Quality monitoring (US-062, 3 pts)

### Backend Engineer
1. Create database schema (US-058, 3 pts)
2. Build API endpoints (US-060, 5 pts)
3. Deployment & validation (US-064, 3 pts)

### Data Analyst
1. Create analytics notebooks (US-061, 5 pts)

### PM
1. Documentation (US-063, 2 pts)
2. Team coordination

**Total Effort:** 39 story points, 2-3 weeks

---

## Key Files

### For Planning
- [Executive Summary](./EXECUTIVE_SUMMARY_CFR.md) - Start here
- [Product Strategy](./PRODUCT_STRATEGY_CFR_INTEGRATION.md) - Why + what + requirements
- [User Stories](./USER_STORIES_CFR_INTEGRATION.md) - 9 stories for sprint

### For Implementation
- [Technical Specification](./TECHNICAL_SPEC_CFR_INTEGRATION.md) - How to build it
  - Scraper architecture
  - Matching algorithm
  - Database schema
  - API design
  - Testing strategy

### For Reference
- Data source: https://www.sports-reference.com/cfb/
- Example stats: https://www.sports-reference.com/cfb/draft/2026.html

---

## Data Points to Capture

**By Position:**
- **QB:** Passing yards, TDs, INTs, completion %, QB rating, rushing yards
- **RB:** Rushing yards/TDs, receptions, receiving yards, yards per carry
- **WR:** Receptions, receiving yards/TDs, yards per reception
- **TE:** Receptions, receiving yards/TDs
- **OL:** Games started, all-conference selections
- **DL:** Tackles, sacks, TFLs, forced fumbles
- **LB:** Tackles, TFLs, sacks, passes defended, INTs
- **DB:** Passes defended, INTs, tackles

---

## Database Changes

**New Table:** `prospect_college_stats`
- Stores 2024-2025 college stats
- Links to prospects via foreign key
- Position-specific columns (~30 total)
- Supports future archival/historical analysis

**See:** [Technical Spec - Database Schema](./TECHNICAL_SPEC_CFR_INTEGRATION.md#database-schema)

---

## API Changes

**New Endpoints:**

1. **Get prospect college stats:**
   ```
   GET /api/prospects/:id/college-stats
   ```

2. **Filter by college performance:**
   ```
   GET /api/prospects/query?college_yards_min=3000
   ```

3. **Position benchmarks:**
   ```
   GET /api/analytics/college-stats/position/QB
   ```

---

## Success Metrics

✅ 95%+ prospect matching  
✅ < 5% parse errors  
✅ < 500ms API response time  
✅ Analysts find new data valuable  
✅ No existing feature regression  

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| HTML structure changes | Monitoring, version control, quick fixes |
| Low match accuracy | Fuzzy matching + manual review |
| Performance issues | Caching, indexes, async processing |

---

## Architecture Diagram

```
Daily Pipeline (3 AM)
│
├─ PFF Scraper (existing)
│  └─→ prospect_grades table
│
├─ CFR Scraper (NEW)
│  ├─→ Scrape 2000 prospects
│  ├─→ Extract college stats
│  ├─→ Match to prospects
│  └─→ prospect_college_stats table
│
├─ Reconciliation (existing)
│  └─→ Quality checks
│
└─ Analytics (NEW)
   ├─→ Materialized views
   └─→ New API endpoints

Result: Unified prospect database with:
├─ PFF grades
├─ College stats (NEW)
├─ Combine results
└─ (Later: Injury data)
```

---

## Questions?

**For product/strategy:** See [Product Strategy](./PRODUCT_STRATEGY_CFR_INTEGRATION.md)

**For technical details:** See [Technical Specification](./TECHNICAL_SPEC_CFR_INTEGRATION.md)

**For sprint work:** See [User Stories](./USER_STORIES_CFR_INTEGRATION.md)

**For implementation:** See [Technical Specification - Implementation](./TECHNICAL_SPEC_CFR_INTEGRATION.md#pipeline-integration)

---

## Next Steps

This Week:
- [ ] Team review meeting
- [ ] Q&A on approach
- [ ] Assign story owners

Sprint 4 Planning:
- [ ] Add stories to sprint board
- [ ] Estimate remaining uncertainties
- [ ] Identify blockers/dependencies

Sprint 4 Execution:
- [ ] Week 1: Scraper + Schema
- [ ] Week 2: Pipeline + API
- [ ] Week 3: Analytics + Deploy

---

## Quick Links

**Documentation:** /docs/
- [Executive Summary](./EXECUTIVE_SUMMARY_CFR.md)
- [Product Strategy](./PRODUCT_STRATEGY_CFR_INTEGRATION.md)
- [Technical Specification](./TECHNICAL_SPEC_CFR_INTEGRATION.md)
- [User Stories](./USER_STORIES_CFR_INTEGRATION.md)
- [This Quick Reference](./CFR_QUICK_REFERENCE.md)

**Code:** /src/
- Scraper: `/data_pipeline/scrapers/cfr_scraper.py` (to be created)
- Tests: `/tests/unit/test_cfr_scraper.py` (to be created)
- Models: `/backend/database/models.py` (to be updated with ProspectCollegeStats)

**Data Source:** https://www.sports-reference.com/cfb/

---

**Version:** 1.0  
**Last Updated:** February 15, 2026  
**Owner:** Product Manager  
**Status:** Ready for team review

