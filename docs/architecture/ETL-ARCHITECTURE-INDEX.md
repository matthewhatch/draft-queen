# ETL Multi-Source Architecture: Complete Design Package

**Date:** February 15, 2026  
**Status:** Architectural Design Complete  
**Author:** Architect Review  

---

## Overview

This package documents a **complete architectural redesign** of the Draft Queen platform from a monolithic data loader into an **enterprise-grade ETL system** capable of reliably ingesting and managing data from 5+ external sources (PFF, NFL.com, College Football Reference, Yahoo, ESPN, etc.).

**Problem:** Current system has no audit trail, brittle matching, and doesn't scale beyond 2-3 sources.

**Solution:** Implement layered ETL architecture with:
- Source-specific **staging tables** (raw data capture)
- **Transformation layer** (cleansing, normalization, validation)
- **Canonical models** (deduplicated, conflict-resolved business entities)
- **Data lineage tracking** (complete audit trail for compliance/debugging)

---

## Document Structure

### 1. **ADR 0011: ETL Multi-Source Data Architecture**
**File:** [`docs/architecture/0011-etl-multi-source-architecture.md`](docs/architecture/0011-etl-multi-source-architecture.md)

**Content:**
- Complete technical architecture (layered data model)
- Source-specific staging table schemas (PFF, NFL, CFR, Yahoo, ESPN)
- Canonical transformation models (prospect_core, prospect_grades, etc.)
- Data lineage audit trail design
- ETL orchestration flow (extract → stage → transform → load → publish)
- Example transformation rules (PFF → canonical)
- Storage/performance trade-offs
- Implementation roadmap (4 phases)

**Audience:** Technical architects, senior engineers, engineering managers

**Key Diagrams:**
- Physical data layer architecture (5-layer model)
- Daily pipeline flow (6 phases)
- Entity relationship (staging → canonical → analytics)

---

### 2. **ETL Implementation Guide**
**File:** [`docs/architecture/ETL-IMPLEMENTATION-GUIDE.md`](docs/architecture/ETL-IMPLEMENTATION-GUIDE.md)

**Content:**
- Practical step-by-step implementation (3 phases)
- Database migration code (staging + canonical tables)
- Base transformer framework (abstract classes)
- Lineage recorder utility
- Source-specific transformers (PFF, CFR, NFL detailed code)
- ETL orchestrator implementation (full Python code)
- Monitoring & observability (data quality queries)
- Deployment checklist

**Audience:** Backend/Data engineers building the system

**Code Examples:**
- SQLAlchemy table definitions
- Python transformer classes
- Async orchestration patterns
- Lineage tracking implementation

---

### 3. **ETL Architecture Rationale (This Document)**
**File:** [`docs/ETL-ARCHITECTURE-RATIONALE.md`](docs/ETL-ARCHITECTURE-RATIONALE.md)

**Content:**
- High-level problem statement
- Solution overview (why ETL vs. other approaches)
- Architecture layers explained (extraction → staging → transformation → canonical → analytics)
- Three design principles (immutability, source-of-truth, auditability)
- Concrete worked example (Alex Johnson prospect across 4 sources)
- Storage/performance trade-offs explained
- Implementation roadmap
- Risk mitigation strategies
- Success metrics
- Questions for leadership

**Audience:** Product managers, technical leadership, stakeholders

**Key Insights:**
- Why staging tables matter (enables reprocessing)
- How lineage solves data quality debugging
- What makes this scalable (no schema changes per source)
- When it's ready (complete foundation in 4-5 weeks)

---

## Architecture Quick Reference

### Data Flow
```
External Sources (PFF, NFL, CFR, Yahoo, ESPN)
         ↓
    EXTRACTION (async parallel)
         ↓
    STAGING (raw data, immutable)
         ↓
    TRANSFORMATION (cleansing, normalization)
         ↓
    MERGE (deduplication, conflict resolution)
         ↓
    LOAD (canonical models, atomic transaction)
         ↓
    LINEAGE (audit trail recorded)
         ↓
    PUBLISH (materialized views, API)
```

### Key Tables

**Staging (Raw Data)**
- `pff_staging`: PFF grades, as-is
- `nfl_combine_staging`: NFL combine tests, as-is
- `cfr_staging`: CFR college stats, as-is
- `yahoo_staging`: Yahoo rankings, as-is

**Canonical (Single Source of Truth)**
- `prospect_core`: Deduplicated prospect identity
- `prospect_grades`: Multi-source normalized grades
- `prospect_measurements`: Reconciled physical tests
- `prospect_college_stats`: Position-normalized college stats

**Lineage (Audit Trail)**
- `data_lineage`: Every field change, source, transformation

### Transformation Rules (Examples)

| Source | Field | Transformation | Rule ID |
|--------|-------|-----------------|---------|
| PFF | grade (0-100) | → 5.0-10.0 scale | `pff_grade_normalization` |
| PFF | name | Fuzzy match + college + position | `pff_prospect_matching` |
| NFL | height ("6-2") | → 74 inches | `nfl_height_parse` |
| CFR | passing_yards | Position-validate (QB only) | `cfr_stat_validation` |
| Multi-source | weight | PFF=310, NFL=315 → pick 315 | `most_recent_wins` |

---

## Implementation Phases

### Phase 1: Foundation (Weeks 1-2)
- [ ] Create all staging tables (migration)
- [ ] Create canonical tables (migration)  
- [ ] Create lineage audit table
- [ ] Build base transformer framework
- [ ] Build lineage recorder utility

**Deliverables:** Database schema, base classes, ready for transformers

### Phase 2: Source Transformers (Weeks 2-3)
- [ ] Implement PFF transformer (grades normalization)
- [ ] Implement CFR transformer (college stats validation)
- [ ] Implement NFL transformer (measurements parsing)
- [ ] Implement conflict resolution logic
- [ ] Build prospect deduplication algorithm

**Deliverables:** All transformers working, tested, documented

### Phase 3: Orchestration (Week 3-4)
- [ ] Build ETL orchestrator (extract, stage, transform, load)
- [ ] Implement parallel extraction
- [ ] Build atomic transaction handling
- [ ] Deploy APScheduler daily pipeline
- [ ] Create monitoring dashboards

**Deliverables:** End-to-end pipeline running daily, monitored

### Phase 4: Operations (Ongoing)
- [ ] Build data quality scorecard
- [ ] Create operational runbooks
- [ ] Performance optimization (partitioning, indexing)
- [ ] Add new sources (ESPN, etc.)
- [ ] Advanced analytics features

**Deliverables:** Production-ready operations, documented processes

---

## Why This Architecture?

### ✅ Scalability
- Adding new source = new staging table + transformer, no schema changes
- Can manage 10+ sources with same framework

### ✅ Auditability
- Complete lineage: "Where did this value come from?" answered in 1 query
- Complies with data governance requirements

### ✅ Data Quality
- Staging validation catches malformed data early
- Transformation testing isolates bugs
- Conflict detection explicit when sources disagree

### ✅ Operational Flexibility
- Can reprocess data through new transformation rules without re-extracting
- Can rollback to previous version using lineage
- Easy debugging: trace quality issues to root source

### ✅ Analytics Ready
- Lineage data enables data quality scorecards
- Source comparison metrics
- Confidence scoring for ML features

---

## Storage & Performance

### Storage (3x Raw Data)
```
Raw staging: 100 MB
Canonical:    50 MB
Lineage:     200 MB
─────────────────
Total:       350 MB

Mitigation: Archive staging >90 days (keep ~100 MB active)
```

### Pipeline Duration
```
Extraction:    30s (parallel)
Staging:       10s
Transform:     45s (batch)
Load:          20s (atomic)
─────────────────
Total:       ~2 min (acceptable for daily batch)

Future: Can optimize to <1 min with caching
```

### Query Performance
```
Canonical models:  FAST (indexed, normalized)
Lineage queries:   SLOW (large table, OLAP)
Solution:          Separate analytical DB (future)
```

---

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **Increased storage** | 3x growth | Archive old staging, plan DB size |
| **Pipeline latency** | 2 min vs 30s | Optimize transforms, parallel processing |
| **Transformation bugs** | Data quality regression | Comprehensive unit tests, staging validation |
| **Team skill gap** | Slow development | ETL training, pair programming, documentation |
| **Lineage performance** | Slow queries on big table | Archiving, partitioning, separate analytics DB |

**Overall Risk Level:** MEDIUM (mitigated by careful design)

---

## Success Criteria

By end of Phase 1-3 (4-5 weeks):

1. **Data Integration:** Successfully merge PFF + CFR + NFL data
   - Target: >95% prospects matched across sources
   - Success: prospect_core has multi-source IDs for 95%+ of records

2. **Auditability:** Complete lineage tracking
   - Target: 100% of fields traceable to source
   - Success: Can run `SELECT * FROM data_lineage WHERE entity_id = ?` and get full history

3. **Scalability:** Can add new source in <1 day
   - Target: Zero schema changes needed
   - Success: Yahoo/ESPN sources add staging table + transformer only

4. **Data Quality:** Automatic conflict detection
   - Target: System flags when PFF grade ≠ Yahoo grade
   - Success: data_lineage shows conflict resolution per conflict

5. **Operations:** Monitored, reliable pipeline
   - Target: >99% success rate
   - Success: <1 hour MTTR when issues occur

---

## Questions for Stakeholders

### For Engineering Leadership
1. **Timeline:** Can we dedicate 4-5 weeks for proper foundation vs. quick-and-dirty?
2. **Team:** Do we need to hire ETL engineer or train existing backend team?
3. **Future:** Should we plan for real-time CDC (Kafka) now, or stick with daily batch?

### For Product
1. **Data Completeness:** Is 95% deduplication accuracy acceptable for 2026 draft?
2. **Feature Priority:** Which analytical queries are most important? (Used for roadmapping)
3. **Regulatory:** Any audit/compliance requirements for data lineage?

### For Operations
1. **Monitoring:** What's acceptable error rate for data quality? Alert thresholds?
2. **Deployment:** Can we afford 2-minute pipeline duration? Or need <1 minute?
3. **Retention:** How long should we keep staging data for audit/reprocessing?

---

## Next Steps

1. **Get Approval:** Review this architecture with technical leadership + product
2. **Start Phase 1:** Implement foundation (database + base classes) immediately
3. **Parallel Development:** While Phase 1 finishing, start building transformers
4. **Testing:** Build comprehensive test suite for transformations
5. **Deployment:** Roll out to staging environment, validate with real data
6. **Production Launch:** Deploy to production with monitoring

---

## Document Index

| Document | Purpose | Audience | Length |
|----------|---------|----------|--------|
| [0011-etl-multi-source-architecture.md](docs/architecture/0011-etl-multi-source-architecture.md) | Technical design, schemas, flow | Engineers, architects | 800 lines |
| [ETL-IMPLEMENTATION-GUIDE.md](docs/architecture/ETL-IMPLEMENTATION-GUIDE.md) | Step-by-step code examples | Backend/data engineers | 600 lines |
| [ETL-ARCHITECTURE-RATIONALE.md](docs/ETL-ARCHITECTURE-RATIONALE.md) | Business rationale, examples | Leadership, PM, engineers | 400 lines |
| [ETL-ARCHITECTURE-INDEX.md](docs/ETL-ARCHITECTURE-INDEX.md) | This document | All stakeholders | 500 lines |

---

## Related Decisions

- **ADR-0002:** Event-Driven Pipeline (previous architecture pattern)
- **ADR-0003:** API Design (how canonical data is consumed)
- **ADR-0004:** Caching Strategy (materialized views on canonical data)
- **ADR-0010:** PFF Data Source (first source implementation)

---

## Appendix: Alternative Approaches Considered

### A. Status Quo (Monolithic Loader)
- **Pros:** Simple, fast development
- **Cons:** Brittle, not auditable, doesn't scale
- **Verdict:** ❌ Unacceptable as system grows

### B. Real-Time Event Streaming (Kafka)
- **Pros:** Event-driven, scalable, real-time
- **Cons:** Overkill (sources don't provide events), expensive, complex
- **Verdict:** ❌ Future consideration, not now

### C. Single Universal Staging Table
- **Pros:** Fewer tables
- **Cons:** Mixing incompatible schemas (PFF grades ≠ combine tests)
- **Verdict:** ❌ Creates more problems than solves

### D. ETL Tool (Talend, Informatica)
- **Pros:** Pre-built connectors, visual design
- **Cons:** Vendor lock-in, expensive, less flexible for custom logic
- **Verdict:** ❌ Not justified for 5 sources, custom code better

### E. **Proposed: Layered ETL Architecture**
- **Pros:** Scalable, auditable, flexible, educational
- **Cons:** More tables, additional code complexity
- **Verdict:** ✅ **RECOMMENDED** - Best long-term foundation

---

## Approval Sign-Off

- [ ] CTO / VP Engineering: Approve timeline and resource allocation
- [ ] Product Manager: Approve data quality trade-offs
- [ ] Data Engineering Lead: Confirm team capacity
- [ ] Security/Compliance: Confirm lineage meets audit requirements

---

**Document Status:** Ready for Implementation  
**Last Updated:** February 15, 2026  
**Version:** 1.0 (Architectural Design Complete)
