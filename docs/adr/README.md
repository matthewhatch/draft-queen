# Architecture Decision Records (ADR) Index

**Last Updated:** February 9, 2026

This directory contains Architecture Decision Records documenting major design decisions for the NFL Draft Analytics Platform. Each ADR captures the context, decision, consequences, and alternatives considered for a specific architectural concern.

## Quick Reference

| ID | Title | Status | Category |
|----|-------|--------|----------|
| [0001](#adr-0001-technology-stack) | Technology Stack Selection | ✅ Accepted | Foundation |
| [0002](#adr-0002-data-architecture) | Data Architecture - Event-Driven Pipeline | ✅ Accepted | Data |
| [0003](#adr-0003-api-design) | API Design - REST over GraphQL | ✅ Accepted | API |
| [0004](#adr-0004-caching-strategy) | Caching Strategy - Redis for Analytics | ✅ Accepted | Performance |
| [0005](#adr-0005-authentication) | Authentication & Authorization - Simple Internal Access | ✅ Accepted | Security |
| [0006](#adr-0006-deployment) | Deployment Strategy - Single Containerized Instance | ✅ Accepted | DevOps |
| [0007](#adr-0007-monitoring) | Monitoring & Observability - Prometheus + Dashboard | ✅ Accepted | Operations |
| [0008](#adr-0008-export-formats) | Data Export Formats - JSON, CSV, Parquet | ✅ Accepted | Data |
| [0009](#adr-0009-data-sourcing) | Data Sourcing Strategy - Public Web Scrapers | ✅ Accepted | Data |
| [0010](#adr-0010-pff-data-source) | Evaluate PFF.com as Premium Data Source | 🔍 Spike | Data |

## Detailed ADR Summaries

### ADR 0001: Technology Stack Selection

**File:** [0001-technology-stack.md](0001-technology-stack.md)

**Decision:** Use Python with FastAPI, PostgreSQL, Redis, and Jupyter notebooks.

**Key Points:**
- FastAPI for rapid REST API development
- PostgreSQL + SQLAlchemy for reliable data storage
- Redis for caching expensive analytics queries
- Python across stack (backend + data processing)
- Jupyter notebooks instead of custom UI (analysts' familiar tool)

**Why This Matters:** Single-language stack reduces cognitive load and enables faster MVP delivery than multi-language alternatives (Node.js + React would require 3+ engineers).

**Alternatives Rejected:**
- Node.js + GraphQL + React (too complex for MVP)
- Django (more boilerplate than FastAPI)
- Rust + Actix-web (steep learning curve)
- Serverless (AWS Lambda not suited for stateful pipeline)

---

### ADR 0002: Data Architecture - Event-Driven Pipeline

**File:** [0002-data-architecture.md](0002-data-architecture.md)

**Decision:** Daily batch pipeline with extraction, transformation, loading (ETL), plus audit trail and materialized views.

**Key Points:**
- **Extract:** Multiple source adapters (NFL.com, ESPN, Pro Days)
- **Transform:** Validation, deduplication, enrichment
- **Load:** Atomic writes with audit logging
- **Materialized Views:** Pre-calculated analytics for performance
- **Historical Snapshots:** Track changes for trend analysis

**Why This Matters:** Ensures data reliability and enables traceability. Analysts trust data because all changes are logged.

**Trade-offs:**
- **Plus:** Single source of truth, audit trail, historical analysis
- **Minus:** Batch delays (daily refresh only), storage overhead for audit logs

**Alternatives Rejected:**
- Real-time event streaming (Kafka) - overkill; sources don't provide event streams
- Multiple databases - unnecessary complexity
- No audit trail - loses ability to track changes

---

### ADR 0003: API Design - REST over GraphQL

**File:** [0003-api-design.md](0003-api-design.md)

**Decision:** REST endpoints with JSON responses.

**Key Points:**
- Simple endpoints: `GET /api/prospects`, `POST /api/prospects/query`, `GET /api/analytics/positions/{pos}`
- HTTP caching works naturally for GET requests
- Automatic OpenAPI documentation via FastAPI
- Easy to test with curl/Postman
- Works with Jupyter notebooks and Python scripts

**Why This Matters:** Minimizes complexity; REST sufficient for internal tool with predictable query patterns.

**Trade-offs:**
- **Plus:** Simple, cacheable, well-documented, familiar
- **Minus:** Potential overfetching, fixed schema requires versioning

**Alternatives Rejected:**
- GraphQL - unnecessary complexity for 2,000-record dataset
- gRPC - harder for Jupyter clients
- SOAP/XML - outdated

---

### ADR 0004: Caching Strategy - Redis for Analytics

**File:** [0004-caching-strategy.md](0004-caching-strategy.md)

**Decision:** Redis caching with TTL-based invalidation and nightly pre-warming.

**Key Points:**
- **Transactional Queries:** No caching (need real-time accuracy)
- **Analytics:** 24-hour TTL (stable until daily refresh)
- **Quality Metrics:** 1-hour TTL (monitoring needs freshness)
- **Reference Data:** 7-day TTL (colleges, positions rarely change)
- **Pre-warming:** Cache populated after daily pipeline completes

**Why This Matters:** Analytics queries drop from 5-10s to 50-100ms via cache hits. Drastically improves analyst experience.

**Trade-offs:**
- **Plus:** Fast queries, reduced database load, pre-warming provides instant results
- **Minus:** Data stale up to 24 hours, additional Redis infrastructure

**Alternatives Rejected:**
- No caching - unacceptable query latency
- Materialized views only - database still strained
- In-memory cache - breaks with multiple API workers

---

### ADR 0005: Authentication & Authorization - Simple Internal Access

**File:** [0005-authentication.md](0005-authentication.md)

**Decision:** API keys over OAuth2 for authentication; all analysts have read-only access.

**Key Points:**
- **Development:** No authentication (open API)
- **Production:** API key in Authorization header + TLS
- **Authorization:** All analysts have same read-only permissions
- **Audit:** Each key tied to individual analyst
- **Management:** Admin generates/rotates keys manually

**Why This Matters:** Sufficient for internal team; OAuth2 would add weeks of development for minimal value.

**Key Management:**
- Setup: Admin generates key, delivers securely
- Rotation: Quarterly; 7-day grace period
- Compromise: Immediate deactivation, audit logs reviewed

**Alternatives Rejected:**
- OAuth2 (Google, Okta) - significant overhead for internal-only users
- Kerberos/LDAP - requires corporate infrastructure
- mTLS - certificate distribution complexity
- No auth - completely unacceptable

**Migration Path:** If organization grows, upgrade to LDAP integration or OAuth2.

---

### ADR 0006: Deployment Strategy - Single Containerized Instance

**File:** [0006-deployment.md](0006-deployment.md)

**Decision:** Docker container on single VM with managed PostgreSQL and Redis.

**Key Points:**
- **Development:** Local container
- **Staging:** Small VM (~$50/month)
- **Production:** Medium VM (~$100/month)
- **Deployment:** GitHub Actions CI/CD, manual production deployment
- **Health Check:** Automated via `GET /health` endpoint

**Why This Matters:** Simple, cost-effective (~$100/month for production), adequate for 5-10 users. Scales to multi-container if needed.

**Deployment Process:**
1. GitHub push triggers CI
2. Tests run, Docker image built
3. Deploy to staging for verification
4. Manual production deployment with rollback capability

**Trade-offs:**
- **Plus:** Simple, cost-effective, familiar Docker workflow
- **Minus:** Single point of failure, no automatic scaling, manual intervention required

**Scalability Path:**
- Phase 1: Current (single instance, 10 users)
- Phase 2: Multiple containers + load balancer (50 users)
- Phase 3: Kubernetes cluster (100+ users)

**Alternatives Rejected:**
- Kubernetes/EKS - too complex for MVP; keep as Phase 2 upgrade
- Serverless (Lambda) - poor fit for stateful pipeline
- Bare metal - less manageable than containers

---

### ADR 0007: Monitoring & Observability - Prometheus + Dashboard

**File:** [0007-monitoring.md](0007-monitoring.md)

**Decision:** Prometheus metrics collection with alert rules and simple HTML dashboard.

**Key Points:**
- **Metrics Collected:**
  - API: request count, latency, errors, in-flight requests
  - Database: query counts, latency, connection pool usage
  - Cache: hit/miss rates, memory usage
  - Business: prospect count, data refresh status, quality metrics
  - System: CPU, memory, uptime

- **Alert Rules:**
  - High error rate (> 1% for 5 min)
  - Slow requests (p95 > 1 second)
  - Data refresh failure (no refresh in 24h)
  - Data quality issue (< 99% completeness)
  - Resource exhaustion (memory > 2GB, connection pool > 80%)

- **Notifications:** Email alerts for critical issues

- **Dashboard:** Simple HTML + Plotly charts (refreshes every 30 seconds)

**Why This Matters:** Production visibility essential for debugging. Even internal tool needs monitoring for reliability.

**Trade-offs:**
- **Plus:** Quick issue detection, debugging visibility, industry-standard
- **Minus:** Prometheus infrastructure to manage, alert tuning required

**Alternatives Rejected:**
- Grafana - beautiful dashboards but unnecessary complexity for MVP
- Cloud monitoring (CloudWatch, Stackdriver) - vendor lock-in, overkill cost
- ELK Stack - too heavyweight for application logs
- No monitoring - unacceptable for production

**Future:** Upgrade to Grafana if dashboards become critical.

---

### ADR 0008: Data Export Formats - JSON, CSV, Parquet

**File:** [0008-export-formats.md](0008-export-formats.md)

**Decision:** Support JSON, CSV, and Parquet export formats.

**Key Points:**
- **CSV** → Spreadsheet analysis (Excel), sharing with non-technical users
- **JSON** → Python/JavaScript processing, API integration, nested data, type preservation
- **Parquet** → Big data tools (DuckDB, Polars, cloud warehouses), columnar compression

**Why This Matters:** Analysts use different downstream tools; supporting multiple formats removes friction.

**Trade-offs:**
- **Plus:** Flexibility, compatibility, performance optimization by format
- **Minus:** Three formats to maintain and test

**Alternatives Rejected:**
- Excel (.xlsx) - verbose, limited for large exports
- XML - outdated
- Protocol Buffers - requires specialized tooling

---

### ADR 0009: Data Sourcing Strategy - Public Web Scrapers

**File:** [0009-data-sourcing.md](0009-data-sourcing.md)

**Decision:** Build web scrapers for public sources (NFL.com, Yahoo Sports) instead of relying on non-existent official APIs.

**Key Points:**
- **Phase 1 (Sprint 1):** NFL.com Combine and Draft tracker scraper
- **Phase 2 (Sprint 2):** Yahoo Sports scraper for additional metrics
- **Phase 3 (Sprint 3):** ESPN for injury reports
- **Robustness:** User-Agent rotation, rate limiting, retry logic, fallback caching
- **Legal:** Respectful scraping of public data; internal use; compliant with robots.txt

**Why This Matters:** Enables data-driven platform without external partnerships or licensing. MVP timeline feasible with scraping.

**Trade-offs:**
- **Plus:** No API dependency, current data, public information, cost-free
- **Minus:** Fragility (breaks on site changes), maintenance burden, legal gray area

**Legal Considerations:**
- Public data; internal use; respectful rate limiting
- Risk acceptable for MVP
- Migration path to official partnerships for 2.0

**Alternatives Rejected:**
- Official NFL API - not publicly available
- Manual data entry - not viable for 2,000+ prospects
- Crowdsourced data - too slow for MVP
- Data vendors (PFF) - expensive, not justified for MVP

---

### ADR 0010: Evaluate PFF.com as Premium Data Source

**File:** [0010-pff-data-source.md](0010-pff-data-source.md)

**Status:** 🔍 Spike Investigation (Decision Pending - Week 1 of Sprint 3)

**Decision:** Time-boxed investigation to determine if PFF.com's Draft Big Board should be added as a data source.

**Key Questions:**
- **Technical:** Can we scrape it? (Static HTML vs. JavaScript-rendered?)
- **Legal:** Is scraping allowed? (robots.txt, ToS, partnership opportunities?)
- **Value:** What unique data does PFF provide? Worth the effort?
- **Risk:** Legal, technical, maintenance burden?

**Investigation Schedule:**
- Start: Mar 10 (Sprint 3 Week 1)
- Complete: Mar 15 (end of Week 1)
- Decision: Mid-Sprint 3 review meeting

**Three Scenarios:**
1. **Low Risk, High Value** → Add to Sprint 3/4 backlog
2. **Medium Risk, High Value** → Pursue official partnership for 2.0
3. **High Risk** → Skip for MVP; revisit later

**Why Consider PFF?**
- Industry-standard prospect grades
- Highly valued by NFL scouts
- Could differentiate our platform
- Potential for premium data partnerships

**Current Status:** Investigation begins Mar 10; decision framework established.

---

**Key Points:**
- **CSV** → Spreadsheet analysis (Excel), sharing with non-technical users
- **JSON** → Python/JavaScript processing, API integration, nested data, type preservation
- **Parquet** → Big data tools (DuckDB, Polars, cloud warehouses), columnar compression

**API Design:**
```
GET /api/prospects/export?format=csv
GET /api/prospects/export?format=json&filter={position:QB}
GET /api/prospects/export?format=parquet&fields=name,position,forty_time
```

**Performance by Format:**
| Format | Size (2K prospects) | Speed | Schema |
|--------|-------------------|-------|--------|
| CSV | 5 MB | Medium | Lost |
| JSON | 8 MB | Medium | Preserved |
| Parquet | 1 MB | Fast | Preserved |

**Why This Matters:** Analysts use different downstream tools; supporting multiple formats removes friction.

**CSV Limitations:** No schema info; types ambiguous when loading. Mitigated by including schema in JSON export and documentation.

**Alternatives Rejected:**
- Excel (.xlsx) - verbose, limited for large exports
- XML - outdated
- Arrow IPC - less tool support than Parquet
- Protocol Buffers - requires specialized tooling

---

## Decision Dependencies

```
0001: Technology Stack
  ├─→ 0002: Data Architecture (Python enables pipeline)
  ├─→ 0003: API Design (FastAPI for REST)
  ├─→ 0006: Deployment (Python-friendly containerization)
  └─→ 0007: Monitoring (FastAPI middleware for metrics)

0002: Data Architecture
  ├─→ 0004: Caching Strategy (materialized views + Redis)
  ├─→ 0006: Deployment (pipeline runs via APScheduler)
  └─→ 0007: Monitoring (pipeline health tracked)

0003: API Design
  ├─→ 0004: Caching Strategy (HTTP caching for GET requests)
  ├─→ 0005: Authentication (API key middleware)
  └─→ 0008: Export Formats (export endpoints)

0004: Caching Strategy
  └─→ 0006: Deployment (Redis infrastructure)

0005: Authentication
  ├─→ 0006: Deployment (TLS for production)
  └─→ 0007: Monitoring (audit logs tied to API keys)

0006: Deployment
  └─→ 0007: Monitoring (health check confirms deployment)

0007: Monitoring
  └─ (no dependencies)

0008: Export Formats
  ├─→ 0003: API Design (export endpoints)
  └─→ 0006: Deployment (export endpoints in production)
```

## How to Use These ADRs

1. **For New Team Members:** Read ADR 0001-0003 to understand core architecture
2. **For Implementation:** Reference specific ADR for technical details
3. **For Future Decisions:** Use these as templates and precedents
4. **For Upgrades:** Check "Alternatives Considered" and "Migration Path" sections
5. **For Discussions:** Link to specific ADRs in tech discussions to provide context

## When to Create New ADRs

Create new ADRs when:
- Making significant architectural decisions
- Choosing between multiple technology/approach options
- Setting important policies (security, performance, scalability)
- Documenting trade-offs for future reference

Use existing ADRs as templates. Keep them concise but comprehensive.

## ADR Status Definitions

- **Accepted:** Decision made and implemented (or planned for implementation)
- **Deprecated:** Replaced by newer ADR; keep for historical reference
- **Superseded:** Decision overridden; new ADR documents why
- **Proposed:** Under discussion; not yet implemented

All current ADRs are **Accepted** as of Sprint 1.

---

**Repository:** `/home/parrot/code/draft-queen/docs/adr/`

**Questions?** Reference the specific ADR document or discuss in architecture review meetings.
