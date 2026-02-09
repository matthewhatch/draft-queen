# ADR 0002: Data Architecture - Event-Driven Pipeline

**Date:** 2026-02-09  
**Status:** Accepted

## Context

Prospect data comes from multiple external sources (NFL.com, ESPN, Pro Days, Combine) that update on different schedules. We need to:
- Reliably ingest data from multiple sources daily
- Deduplicate and validate data
- Maintain data audit trail (who added/modified what/when)
- Support both real-time queries and batch analytics
- Handle data quality issues gracefully
- Archive historical snapshots for trend analysis

## Decision

We implement an event-driven pipeline architecture:

**Daily Batch Pipeline**
1. **Extraction** (Source-specific adapters)
   - NFL.com adapter → prospect details, combine results
   - ESPN adapter → college production stats
   - Pro Days adapter → position-specific measurements

2. **Transformation** (Validation & enrichment)
   - Schema validation (required fields, type checking)
   - Deduplication (merge duplicate prospect records)
   - Unit conversion (metrics to standardized units)
   - Data enrichment (calculate derived fields, ratings)

3. **Loading** (Atomic writes to database)
   - Transaction-based: all-or-nothing writes
   - Audit logging: track all changes with timestamp, source
   - Historical snapshots: preserve day-by-day state for trends

**Data Store Layout**
```
Core Tables:
- prospects (id, name, position, college, ...)
- measurements (prospect_id, height, weight, 40_time, ...)
- college_stats (prospect_id, year, position, receptions, ...)
- injuries (prospect_id, date, type, severity, ...)
- audit_log (entity_type, entity_id, action, old_value, new_value, timestamp)

Materialized Views (updated nightly):
- position_stats (aggregated measurables by position)
- prospect_trends (year-over-year changes)
- injury_patterns (position-specific injury frequencies)
```

**Technology Choices**
- APScheduler: triggers daily pipeline at 3 AM (off-peak)
- SQLAlchemy: ORM handles complex inserts/updates
- Pandas: data transformation and deduplication
- PostgreSQL transactions: ensures data consistency

## Consequences

### Positive
- Single source of truth: PostgreSQL is authoritative
- Audit trail: all changes tracked and immutable
- Historical analysis: snapshots enable trend analysis
- Decoupled from source APIs: pipeline retries automatically
- Simple to debug: each stage can be tested independently

### Negative
- Batch delays: data refreshes once daily, not real-time
- Storage overhead: audit logs and snapshots increase disk usage (~10x raw data)
- Complexity: pipeline orchestration requires monitoring
- Pipeline failures: data stale until pipeline succeeds

### Mitigation Strategies
- Automatic retries with exponential backoff
- Email alerts on pipeline failures
- Manual trigger for emergency refreshes
- Health check endpoint for monitoring

## Alternatives Considered

### Real-Time Event Streaming (Kafka/Pulsar)
- Rejected: Overkill for daily batch data
- NFL.com/ESPN don't provide event streams; still polling

### Multiple Databases (Analytics DB + Transactional DB)
- Rejected: Added complexity; single PostgreSQL sufficient for 2,000 records
- Future option if scaling to millions of records

### No Audit Trail (Direct overwrites)
- Rejected: Loses change history needed for trend analysis
- Can't detect data quality issues if previous values lost

### Append-Only Event Log
- Rejected: Simpler audit log sufficient; full event sourcing unnecessary

## Related Decisions
- ADR-0003: API Design (how data is queried)
- ADR-0004: Deployment (how pipeline runs in production)
- ADR-0005: Caching Strategy (materialized views for performance)
