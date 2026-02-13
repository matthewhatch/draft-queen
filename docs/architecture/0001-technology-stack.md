# ADR 0001: Technology Stack Selection

**Date:** 2026-02-09  
**Status:** Accepted

## Context

We are building an internal data analytics platform for NFL prospect evaluation. The platform needs to:
- Ingest data from multiple external sources (NFL.com, ESPN, Pro Days, Combine)
- Store and query ~2,000 prospect records with rich measurable data
- Provide fast query access for analysts via REST API
- Support exploratory data analysis via Jupyter notebooks
- Handle daily automated data refresh
- Scale to support 5-10 concurrent internal users

The project has a 6-week MVP timeline with limited resources (1-2 engineers per role).

## Decision

We select the following technology stack:

**Backend Framework:** FastAPI (Python)
- Rationale: Async-capable, minimal boilerplate, excellent for data APIs
- Enables rapid REST API development with automatic OpenAPI documentation

**Database:** PostgreSQL with SQLAlchemy ORM
- Rationale: ACID transactions, JSON support, excellent indexing for complex queries
- SQLAlchemy provides ORM abstraction and schema migrations

**Caching Layer:** Redis
- Rationale: Fast in-memory caching for frequently accessed analytics results
- Reduces database load for expensive aggregation queries

**Data Processing:** Python (pandas, NumPy, SQLAlchemy)
- Rationale: Single language across stack, excellent data manipulation libraries
- Analysts already familiar with Python for Jupyter notebooks

**Analytics/Visualization:** Jupyter Notebooks
- Rationale: Avoids building custom UI dashboard; analysts use familiar tool
- Supports exploratory analysis workflow; easy to version and share

**Orchestration:** APScheduler (Python)
- Rationale: Simple scheduled jobs; no need for complex orchestration framework
- Runs data refresh, quality checks, metric calculations

## Consequences

### Positive
- Single language (Python) reduces cognitive load and hiring needs
- FastAPI rapid development enables quick MVP iteration
- PostgreSQL + SQLAlchemy provide mature, production-tested data layer
- Jupyter notebooks allow analysts to start working immediately without UI development
- Open-source stack reduces licensing costs

### Negative
- Python may not scale to millions of records (acceptable for 2,000 prospects)
- Jupyter notebooks require manual refresh; not real-time dashboards
- Team must manage Redis and PostgreSQL operations
- No built-in monitoring/alerting (must be added manually)

### Migration Path
- If real-time dashboards needed later: add Grafana/Kibana on top of existing stack
- If scale increases dramatically: migrate to Go/Rust for compute layer
- Database abstraction allows future PostgreSQL→BigQuery migration if needed

## Alternatives Considered

### Node.js + GraphQL + React
- Rejected: Would require 3+ engineers (backend, frontend, DevOps); exceeds 6-week timeline
- Slower development for internal tool with simple query needs

### Python + Django
- Rejected: More scaffolding than needed; FastAPI faster for data APIs
- Django ORM less flexible for complex analytical queries

### Rust + Actix-web
- Rejected: Steep learning curve; slower initial development
- Overkill for 2,000-record dataset

### Serverless (AWS Lambda + DynamoDB)
- Rejected: Cost unpredictable; data model fits relational database better
- Harder to do complex analytical queries

## Related Decisions
- ADR-0002: Data Architecture
- ADR-0003: API Design (REST)
- ADR-0004: Deployment Strategy
