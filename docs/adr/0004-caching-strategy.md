# ADR 0004: Caching Strategy - Redis for Analytics

**Date:** 2026-02-09  
**Status:** Accepted

## Context

Many analytics queries are expensive (aggregations, trends, calculations) but don't need real-time accuracy. Examples:
- Position group statistics (rarely changes except daily refresh)
- Trend analysis (year-over-year comparisons)
- Injury risk assessments
- Production readiness scores

We need to balance performance (sub-500ms response times) with freshness (shouldn't be older than daily refresh).

## Decision

We implement a **Redis caching layer** with TTL-based invalidation:

**Cache Strategy by Endpoint Type**

1. **Transactional Queries** (no caching)
   - `GET /api/prospects` → direct database queries
   - `POST /api/prospects/query` → direct database queries
   - Rationale: These need real-time accuracy; volume low

2. **Analytics Endpoints** (aggressive caching)
   - `GET /api/analytics/positions/:pos` → 24-hour TTL
   - `GET /api/analytics/trends/:pos` → 24-hour TTL
   - `GET /api/analytics/injury-risk/:id` → 24-hour TTL
   - Rationale: Results stable until daily refresh; expensive to calculate

3. **Aggregated Data** (moderate caching)
   - `GET /api/data/quality` → 1-hour TTL
   - Rationale: Monitoring needs freshness; recalculate hourly

4. **Static Reference Data** (long-term caching)
   - Colleges list, positions list → 7-day TTL
   - Rationale: Rarely changes; safe to cache long-term

**Cache Invalidation**

```
Pipeline Trigger (3 AM daily):
  1. Data refresh completes
  2. Clear ALL cache keys
  3. Background worker pre-warms cache:
     - Calculate all position stats
     - Calculate all trends
     - Populate Redis

If Manual Refresh Triggered:
  1. Refresh completes
  2. Clear cache immediately
  3. Pre-warm cache

Cache Key Naming:
  position_stats:{position}:{date}
  trends:{position}:{years}
  injury_risk:{prospect_id}
  data_quality:{date}
```

**Implementation**

```python
# FastAPI dependency injection
@app.get("/api/analytics/positions/{position}")
async def get_position_stats(position: str, redis: Redis = Depends(get_redis)):
    cache_key = f"position_stats:{position}:{today()}"
    
    # Try cache first
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Cache miss: calculate
    result = calculate_position_stats(position)
    await redis.setex(cache_key, 86400, json.dumps(result))  # 24h TTL
    
    return result
```

## Consequences

### Positive
- Performance: Analytics queries drop from 5-10s to 50-100ms via cache hits
- Reduced database load: expensive aggregations happen once daily
- Predictable costs: fixed query patterns; no query explosion
- Pre-warming: analysts get instant results after daily refresh
- Simple invalidation: TTL-based strategy robust against edge cases

### Negative
- Stale data: results up to 24 hours old between refreshes
- Additional infrastructure: Redis must be managed/monitored
- Memory overhead: entire analytics dataset in memory (~100MB)
- No real-time precision: trends calculated once daily
- Cache coherence: must ensure cache invalidation working

### Acceptable Stale Data?
- Yes: prospect data itself only updates daily
- Acceptable lag: analysts accept "refreshed daily at 3 AM" model
- If real-time needed: analysts can query raw data directly (slower)

## Alternatives Considered

### No Caching (Direct Database Queries)
- Rejected: Analytics queries hit 10s+ latency; unacceptable UX
- Would require database optimization only; still slow for aggregations

### Materialized Views Only (no Redis)
- Considered: PostgreSQL materialized views refresh nightly
- Decision: Use both - materialized views in DB, Redis for API cache
- Rationale: Dual caching provides safety and speed

### Application-Level In-Memory Cache (Python dict)
- Rejected: Only works single-process; breaks with multiple API workers
- Redis provides distributed cache across all processes

### Client-Side Caching (ETags, Last-Modified)
- Considered: Browser/client caches responses
- Decision: Combine with Redis - cache on both server and client
- Rationale: Maximizes cache hit rates

### Cache-Aside vs Write-Through vs Write-Behind
- Decision: Cache-Aside (lazy population on first request)
- Alternative: Write-Through (populate during pipeline execution)
- Rationale: Simpler implementation; pipeline handles pre-warming anyway

## Related Decisions
- ADR-0002: Data Architecture (pipeline refreshes at 3 AM)
- ADR-0003: API Design (transactional queries bypass cache)
- ADR-0007: Monitoring (cache hit rates tracked)
