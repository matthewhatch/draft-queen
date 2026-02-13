# ADR 0010: Evaluate PFF.com as Premium Data Source

**Date:** 2026-02-10  
**Status:** Spike Investigation (Decision Pending)  
**Decision Made By:** Product Manager

## Context

PFF (Pro Football Focus) provides proprietary prospect grades and advanced analytics through their Draft Big Board. Adding PFF data could significantly enhance our prospect evaluation capabilities. However, PFF likely has stricter data licensing and scraping policies than public sources (NFL.com, ESPN, Yahoo Sports).

This ADR documents the spike investigation to determine:
1. Technical feasibility of scraping PFF.com
2. Legal/ethical compliance assessment
3. Value proposition vs. effort
4. Recommendation for MVP inclusion

## Investigation Plan

**Spike Duration:** 1 week (first week of Sprint 3, Mar 10-15, 2026)

### Phase 1: Technical Analysis (Assigned to Data Engineer)
```python
# Investigate:
1. PFF.com page structure
   - Static HTML vs. JavaScript-rendered
   - API endpoints (if available)
   - Data loading mechanism

2. Available data fields
   - Prospect grades (overall, by position)
   - Rankings (big board position)
   - Measurables (if provided)
   - Comparisons/metrics

3. Scraping feasibility
   - BeautifulSoup sufficient?
   - Need Selenium/Playwright?
   - Rate limiting constraints
   - Session management

4. Frequency/stability
   - Update frequency
   - Page structure changes
   - Historical data availability
```

**Example URL:** https://www.pff.com/draft/big-board?season=2026

### Phase 2: Legal/Compliance Review (Assigned to PM)
```
1. robots.txt analysis
   - Disallowed paths
   - Crawl delay
   - User-agent restrictions

2. Terms of Service review
   - Scraping prohibition?
   - Commercial use restrictions?
   - Attribution requirements?

3. Comparable practices
   - How do other platforms handle PFF data?
   - Industry norms
   - Risk assessment

4. Partnership opportunities
   - Does PFF have affiliate/partnership programs?
   - Cost for official data access?
   - Academic/research licenses?
```

### Phase 3: Value Assessment (Assigned to PM + Data Engineer)
```
1. Data uniqueness
   - What does PFF provide that others don't?
   - Grade/ranking coverage
   - Position-specific metrics
   - Historical grades available?

2. Alignment with other sources
   - Correlation with NFL.com, ESPN, Yahoo Sports?
   - Conflicts/reconciliation needed?
   - Enhancement vs. redundancy

3. Use cases
   - How would analysts use PFF grades?
   - Impact on production readiness scoring?
   - Draft position correlation?

4. Effort vs. value
   - Development effort (light/medium/heavy)
   - Maintenance burden
   - Risk assessment
```

## Expected Outcomes

### Scenario A: Low Technical Risk, Official Approval
**Findings:**
- Static HTML or available API
- robots.txt permits scraping
- Terms of service allow data extraction for internal use
- Unique, valuable data

**Recommendation:**
- ✅ Add PFF scraper to Sprint 3 or Sprint 4 backlog
- Create full user story (US-027 or similar)
- Estimate effort (likely 5-8 story points for scraper + reconciliation)
- Integrate into data reconciliation framework

**Next Steps:**
1. Build PFF scraper following existing pattern
2. Add PFF fields to prospect database
3. Update reconciliation rules (which source authoritative for grades?)
4. Include PFF grades in analytics endpoints

---

### Scenario B: Medium Risk, Partnership Opportunity
**Findings:**
- Dynamic JavaScript content (requires Selenium)
- robots.txt discourages scraping
- Terms of service ambiguous or restrictive
- Very valuable data

**Recommendation:**
- ⚠️ Contact PFF directly for partnership/API access
- Document business case for data partnership
- Skip MVP scraping; pursue official channel
- Consider as paid data source for 2.0 release

**Next Steps:**
1. Research PFF partnership program
2. Cost analysis for official data access
3. Include in post-launch enhancement roadmap
4. Document partnership approach

---

### Scenario C: High Legal Risk, Low Priority
**Findings:**
- Clearly prohibits scraping in ToS
- Dynamic rendering with heavy obfuscation
- robots.txt explicitly disallows
- Limited unique value

**Recommendation:**
- ❌ Skip for MVP
- Revisit after launch if business case changes
- Consider alternative premium sources
- Document decision for future reference

**Next Steps:**
1. Update product roadmap (PFF as "not MVP candidate")
2. Explore other premium sources (if needed)
3. Focus on maximizing value from public sources
4. Revisit in Sprint 5 planning

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Legal action from PFF | Contact for partnership; stop scraping immediately if requested |
| Technical fragility | PoC testing; HTML fixtures for stability |
| Resource drain | Time-boxed spike; clear decision criteria |
| Data quality conflicts | Reconciliation rules; audit trail |

## Decision Framework

**Proceed with Scraper IF:**
- ✅ Low legal risk (approved by PM/Legal)
- ✅ Unique, high-value data
- ✅ Effort < 8 story points
- ✅ Fits sprint capacity

**Pursue Partnership IF:**
- ⚠️ Medium risk but high value
- ⚠️ Official channel available
- ⚠️ Cost acceptable for 2.0 release

**Skip for MVP IF:**
- ❌ High legal risk
- ❌ Scraping technically complex (Selenium heavy)
- ❌ Value questionable
- ❌ Resource constraints

## Success Metrics for Spike

- [ ] Technical feasibility documented (Y/N)
- [ ] Legal risk assessed (Low/Medium/High)
- [ ] Effort estimate provided (if proceeding)
- [ ] Team has clear decision framework
- [ ] PoC code available (if applicable)

## Timeline

| Date | Activity |
|------|----------|
| Mar 10 | Spike starts; initial page analysis |
| Mar 12 | Technical feasibility report ready |
| Mar 14 | Legal/compliance assessment complete |
| Mar 15 | Spike review meeting; decision made |
| Mar 16 | Update backlog based on decision |

## Related Decisions

- ADR-0009: Data Sourcing (web scrapers for public sources)
- ADR-0002: Data Architecture (multi-source pipeline)

---

## Product Manager Notes

**Why investigate PFF.com?**
- PFF grades are industry standard for prospect evaluation
- Highly respected source among NFL scouts and analysts
- Could differentiate our platform vs. basic public sources
- Potential for monetization if data partnerships developed

**Trade-offs:**
- MVP complexity vs. competitive advantage
- Legal risk vs. data value
- Development effort vs. time to launch

**Strategic Considerations:**
- If low risk: include for stronger MVP
- If medium risk: pursue partnership for 2.0
- If high risk: focus on public sources, revisit later

**Launch Strategy:**
- MVP: Launch with NFL.com, Yahoo Sports, ESPN (proven safe)
- Quick Wins (Sprint 4): Add PFF if low-risk spike
- Post-Launch: Official partnerships for premium sources

---

**Spike Assigned To:** Data Engineer (lead) + PM (support)  
**Review Date:** March 15, 2026  
**Decision Urgency:** Mid-priority (doesn't block MVP launch)
