# ADR 0003: API Design - REST over GraphQL

**Date:** 2026-02-09  
**Status:** Accepted

## Context

The platform needs to expose prospect data via API for:
- Jupyter notebooks (exploratory analysis)
- Batch exports (CSV, JSON, Parquet)
- Analytics calculations (aggregations, trends)
- Future web UI (if needed)

We must choose between REST and GraphQL for the API design.

## Decision

We use **REST** with JSON for all API endpoints.

**API Structure**
```
Query Endpoints:
GET /api/prospects                    # List all prospects (paginated)
GET /api/prospects/{id}               # Get prospect detail
POST /api/prospects/query             # Complex query with filters

Analytics Endpoints:
GET /api/analytics/positions/{pos}    # Position group stats
GET /api/analytics/trends/{pos}       # Historical trends
GET /api/analytics/injury-risk/{id}   # Injury assessment

Export Endpoints:
GET /api/prospects/export?format=json
GET /api/prospects/export?format=csv
GET /api/prospects/export?format=parquet

Admin Endpoints:
GET /api/data/quality                 # Quality metrics
POST /api/data/refresh                # Trigger pipeline

Health Endpoints:
GET /health                           # Service health
GET /metrics                          # Prometheus metrics
```

**Request/Response Format**
```json
// List with pagination
GET /api/prospects?page=1&limit=20&sort=rating

{
  "status": "success",
  "data": [
    {
      "id": "1",
      "name": "Player Name",
      "position": "QB",
      "college": "University",
      "measurements": {
        "height": 77,
        "weight": 215,
        "forty_time": 4.89
      }
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 2000,
    "pages": 100
  }
}

// Complex query
POST /api/prospects/query

{
  "filters": {
    "position": "QB",
    "height": { "min": 75, "max": 80 },
    "college": ["Alabama", "Ohio State"],
    "forty_time": { "max": 5.0 }
  },
  "sort": "rating",
  "limit": 50
}
```

## Consequences

### Positive
- Simple: analysts understand REST; no learning curve for GraphQL
- Cacheable: HTTP GET requests cache naturally via Redis
- Exploratory: easy to test endpoints manually via curl/Postman
- Documentation: FastAPI auto-generates OpenAPI/Swagger docs
- Versioning: straightforward URL-based versioning if needed
- Multiple clients: works with Jupyter, Python scripts, future web UI

### Negative
- Overfetching: some endpoints return more fields than needed
- Underfetching: might need multiple calls for related data
- No query optimization: clients can't request specific fields
- Fixed schema: changes require versioning

### Why Not GraphQL?
- Complexity: GraphQL schema and resolver development overhead
- Overkill: dataset small enough (2,000 records) that overfetching negligible
- Exploratory use: analysts benefit more from simple, documented REST
- Debug difficulty: GraphQL errors harder to troubleshoot
- Cache invalidation: harder to cache GraphQL responses

## Alternatives Considered

### GraphQL
- Better: flexible field selection for complex UI scenarios
- Worse: unnecessary complexity for internal tool with simple queries
- Decision: rejected in favor of simplicity

### gRPC
- Better: efficient binary protocol, real-time streaming
- Worse: Jupyter clients harder to implement; overkill for batch analytics
- Decision: rejected in favor of HTTP/JSON simplicity

### SOAP/XML
- Decision: rejected; outdated

### Custom Binary Protocol
- Decision: rejected; HTTP/JSON standard sufficient

## Related Decisions
- ADR-0001: Technology Stack (FastAPI enables REST design)
- ADR-0004: Deployment (REST endpoints easy to expose via HTTP)
- ADR-0006: Caching Strategy (HTTP caching for GET requests)
