# Product Strategy: College Football Reference Integration

**Date:** February 15, 2026  
**Product Manager Decision:** Adding College Football Reference (CFR) as primary source for college statistics  
**Status:** Strategy Document (Ready for Implementation Planning)

---

## Executive Summary

**Objective:** Add College Football Reference (CFR) as a high-priority data source to strengthen our college performance metrics and competitive grading capabilities.

**Why CFR?**
- **Most Comprehensive:** Official statistics for all FBS/FCS players
- **Authoritative:** Industry standard for college football analytics
- **Accessible:** Public data, good structure for scraping
- **Complementary:** Fills gaps that PFF (draft grades) and Yahoo Sports cannot
- **Higher Quality:** Better data quality than Yahoo Sports for college stats

**Current State:** PFF-only pipeline (1 source)  
**Target State:** Multi-source pipeline with CFR as primary source for college stats  
**Timeline:** Sprint 4 (estimated 1-2 weeks)  
**Priority:** HIGH (enables competitive differentiation)

---

## Strategic Rationale

### Current Data Gaps

| Metric | Source | Status | Gap |
|--------|--------|--------|-----|
| Draft Grades | PFF | ✅ Available | None |
| Combine Results | NFL.com | ✅ Available | None |
| College Stats | Yahoo Sports | ❌ Limited/Inconsistent | **CRITICAL** |
| College Film Grades | None | ❌ Not Available | **MAJOR** |
| Injury Reports | ESPN | ❌ Not Available | **MAJOR** |
| **College Performance** | **None** | ❌ Not Available | **CRITICAL** |

**CFR closes the College Performance gap**, which is essential for:
- Evaluating production levels relative to draft grade
- Comparing FBS stars vs. FCS standouts
- Identifying statistical outliers (over/underperforming vs. grade)
- Supporting advanced analytics and comparative analysis

### Competitive Advantage

**With CFR integration:**
- ✅ Can identify prospects with elite college production vs. modest grade
- ✅ Can identify system QBs (good stats, lower grade)
- ✅ Can compare across position groups more rigorously
- ✅ Can build predictive models: (college stats + combine + grade) → NFL success
- ✅ Can support "controversial picks" analysis for draft room discussions

---

## Product Requirements

### Data Points to Capture from CFR

**Quarterback (QB)**
- Games played / Started
- Passing yards
- Touchdowns / Interceptions
- Completion percentage
- QB rating
- Rushing yards / TDs

**Running Back (RB)**
- Rushing attempts / Yards / TDs
- Receiving receptions / Yards / TDs
- Yards per carry
- Yards per game
- Total TD:Att ratio

**Wide Receiver (WR)**
- Receptions / Yards / TDs
- Yards per reception
- Receiving yards per game
- Targets (if available)

**Tight End (TE)**
- Receptions / Yards / TDs
- Yards per reception
- Receiving yards per game

**Offensive Linemen (OL)**
- Games started
- All-conference selections (proxy for quality)
- Position (LT, LG, C, RG, RT)

**Defensive Line (DL)**
- Tackles / Sacks
- TFLs (Tackles For Loss)
- Forced fumbles
- Position specialization

**Edge Rushers (EDGE)**
- Sacks
- TFLs
- Pressures (if available)
- Pass rush efficiency

**Linebackers (LB)**
- Tackles
- Sacks / TFLs
- Passes defended
- Interceptions

**Defensive Backs (DB)**
- Passes defended
- Interceptions
- Tackles
- Break-ups

### Data Schema Addition

**New Table: `prospect_college_stats`**

```sql
CREATE TABLE prospect_college_stats (
  id UUID PRIMARY KEY,
  prospect_id UUID NOT NULL REFERENCES prospects(id),
  season INTEGER NOT NULL,
  school STRING NOT NULL,
  position STRING NOT NULL,
  
  -- Game Information
  games_played INTEGER,
  games_started INTEGER,
  
  -- Offense (Generic)
  total_touches INTEGER,
  total_yards INTEGER,
  total_touchdowns INTEGER,
  
  -- QB-Specific
  passing_attempts INTEGER,
  passing_completions INTEGER,
  passing_yards INTEGER,
  passing_tds INTEGER,
  interceptions INTEGER,
  completion_pct NUMERIC(5,2),
  qb_rating NUMERIC(5,2),
  rushing_yards INTEGER,
  rushing_tds INTEGER,
  
  -- RB/WR-Specific
  rushing_attempts INTEGER,
  rushing_yards INTEGER,
  rushing_tds INTEGER,
  receptions INTEGER,
  receiving_yards INTEGER,
  receiving_tds INTEGER,
  yards_per_reception NUMERIC(5,2),
  
  -- Defense-Specific
  tackles INTEGER,
  assisted_tackles INTEGER,
  sacks NUMERIC(5,2),
  tfls INTEGER,
  passes_defended INTEGER,
  interceptions INTEGER,
  forced_fumbles INTEGER,
  fumble_recoveries INTEGER,
  
  -- Derived Metrics
  efficiency_rating NUMERIC(5,2),  -- Calculated metric
  statistical_percentile NUMERIC(5,2),  -- vs. position peers
  
  -- Audit
  data_source VARCHAR(100),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## Implementation Strategy

### Phase 1: Core CFR Scraper (Week 1-2)

**Scraper Architecture**
```
src/data_pipeline/scrapers/
├── cfr_scraper.py           ← New scraper
├── base_scraper.py          ← Existing base class
├── pff_scraper.py           ← Existing
└── tests/
    └── test_cfr_scraper.py  ← New tests
```

**Key Considerations:**
1. **CFR URL Structure:** 
   - Base: `https://www.sports-reference.com/cfb/`
   - Player pages: `https://www.sports-reference.com/cfb/players/[name]-[id].html`
   - Team pages: `https://www.sports-reference.com/cfb/schools/[team]/2025.html`

2. **Scraping Approach:**
   - Start with team rosters (easier, more reliable)
   - Extract player links from team pages
   - Crawl individual player pages for detailed stats
   - Build cache layer to avoid repeated requests

3. **Data Matching:**
   - Match CFR players to existing prospects via:
     - Name + college + position (primary)
     - Fuzzy matching for name variations
     - Manual override mechanism for edge cases

### Phase 2: Pipeline Integration (Week 2-3)

**Pipeline Stages**
1. **Extract:** Scrape CFR (incremental, daily)
2. **Transform:** Normalize stats to schema
3. **Load:** Insert into `prospect_college_stats`
4. **Validate:** Check for data quality
5. **Reconcile:** Match to existing prospects
6. **Alert:** Flag any new/unmatched prospects

**Error Handling:**
- Cache fallback if scraping fails
- Partial data tolerance (incomplete stats OK)
- Logging of all matching failures
- Manual review queue for unmatched prospects

### Phase 3: Analytics Integration (Week 3-4)

**New API Endpoints**
- `GET /api/prospects/:id/college-stats` - View college stats
- `GET /api/analytics/college-stats/position/:pos` - Aggregate stats by position
- `GET /api/prospects/query?college_stats_filter=...` - Filter by college performance

**New Jupyter Notebooks**
- `College_Performance_Analysis.ipynb` - Explore CFR data
- `Grade_vs_Production.ipynb` - Compare PFF grade vs. CFR stats
- `Position_Benchmarks.ipynb` - Position-specific analytics

---

## Product Value

### For Internal Users (Analysts)
- **Better Prospect Evaluation:** Combine draft grade with college production
- **Statistical Rigor:** Data-driven arguments for draft room discussions
- **Outlier Detection:** Identify system players vs. elite performers
- **Trend Analysis:** See how college stats correlate with draft outcomes

### For Product Roadmap
- **Unlocks Phase 5 Analytics:** "Grade vs. Production" analysis
- **Enables Predictive Models:** College stats + Combine + Grade → NFL success prediction
- **Supports Future Export:** Enhanced prospect profiles with college context
- **Differentiates from Competitors:** Most tools focus on PFF grades; we add college performance context

### Success Metrics
- ✅ 95%+ of 2026 draft class matched to CFR data
- ✅ API endpoints return < 500ms
- ✅ Data quality > 98% (verified vs. manual samples)
- ✅ No duplicate prospects created
- ✅ Analysts can compare grade vs. production

---

## Risks & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|-----------|
| **CFR HTML structure changes** | Scraper breaks | Medium | Version scraper, maintain test fixtures, monitoring alerts |
| **Hard to match CFR → PFF** | High duplicate/missing data | Medium | Fuzzy matching algo, manual override UI, audit logs |
| **Performance: Too slow** | API timeouts on analytics | Low | Caching, materialized views, async queries |
| **Incomplete data** | Many players missing college stats | High | Accept partial data, flag gaps for users, fallback to null |
| **Rate limiting** | CFR blocks scraper | Low | Respectful delays (2-3s), user-agent rotation, low frequency |

---

## Dependencies & Sequencing

**Blockers:** None (can proceed immediately)

**Dependencies:**
1. Current prospect database stable (exists ✅)
2. Base scraper framework (exists ✅)
3. Data pipeline orchestration (exists ✅)

**Sequencing:**
1. ✅ PFF scraper (current - Sprint 3)
2. → CFR scraper (proposed - Sprint 4)
3. → Analytics integration (Sprint 4-5)
4. → UI/Export features (Sprint 5)

---

## Alternative Data Sources

We evaluated these alternatives to CFR:

| Source | Pros | Cons | Decision |
|--------|------|------|----------|
| **College Football Reference** | Complete, official, authoritative | HTML scraping required | ✅ PRIMARY |
| **ESPN College Stats** | Some API endpoints | Limited coverage, hard to access | ❌ Secondary |
| **Pro Football Reference** | Similar to CFR | Less specific for draft | ❌ Secondary |
| **Manual Data Entry** | Reliable, accurate | Not scalable (2,000+ players) | ❌ Infeasible |
| **Academic CSV datasets** | Free, complete | Outdated (2023 max) | ❌ Not current |

**Recommendation:** CFR is the only viable option for current, comprehensive college statistics.

---

## Success Criteria (Product)

- [ ] CFR scraper operational and integrated into daily pipeline
- [ ] 95%+ prospect matching between CFR and existing database
- [ ] New `prospect_college_stats` table populated for 2026 class
- [ ] API endpoints functional and documented
- [ ] Analysts can query college stats via API
- [ ] New Jupyter notebooks demonstrate value
- [ ] No performance regression on existing API endpoints
- [ ] Documented data dictionary for college stats

---

## Timeline & Resource Plan

| Phase | Duration | Owner | Deliverable |
|-------|----------|-------|-------------|
| Phase 1: Core Scraper | 1 week | Data Engineer | Working CFR scraper + tests |
| Phase 2: Integration | 1 week | Data Engineer | Pipeline integration + validation |
| Phase 3: Analytics | 1 week | Backend + Data | API endpoints + notebooks |
| Phase 4: Validation | 3 days | QA | Test coverage, manual verification |
| **Total** | **2-3 weeks** | Team | **Production-ready** |

---

## Product Manager Sign-Off

**Decision:** APPROVED for Sprint 4 implementation

**Rationale:**
- Fills critical gap in college performance data
- Supports strategic roadmap goals (analytics, export features)
- Low technical risk (proven scraping pattern with PFF)
- High strategic value (competitive differentiation)
- Enables Phase 5 analytics work

**Owner:** Data Engineer  
**Stakeholder Review:** Before production deployment  
**Success Review:** After Sprint 4 completion

---

**Next Steps:**
1. Share this document with engineering team
2. Create technical specification (scraping details, exact schema)
3. Create user stories for sprint planning
4. Schedule kick-off meeting with Data Engineer
5. Update sprint roadmap

