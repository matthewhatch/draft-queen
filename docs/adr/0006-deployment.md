# ADR 0006: Deployment Strategy - Single Containerized Instance

**Date:** 2026-02-09  
**Status:** Accepted

## Context

We need to deploy the analytics platform to production. Decisions required:
- Deployment target (cloud vs. on-premise)
- Containerization strategy
- Scaling approach
- Infrastructure management overhead

Constraints:
- 5-10 internal users (low traffic)
- 6-week MVP timeline (limited DevOps resources)
- Internal use only (no public-facing SLA requirements)

## Decision

We deploy as **single containerized instance** with Docker:

**Deployment Architecture**

```
┌─────────────────────────────────────────┐
│         Production Server (VM)          │
├─────────────────────────────────────────┤
│  Docker Container                       │
│  ├─ FastAPI (gunicorn, 4 workers)      │
│  ├─ APScheduler (background jobs)      │
│  └─ Application code                    │
├─────────────────────────────────────────┤
│  PostgreSQL 14 (managed or local)      │
│  Redis 7 (local or managed)            │
└─────────────────────────────────────────┘

External Services:
  - PostgreSQL database (AWS RDS or self-hosted)
  - Redis cache (AWS ElastiCache or self-hosted)
  - Static backups (S3 or network storage)
```

**Docker Configuration**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"

EXPOSE 8000

CMD ["gunicorn", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", "main:app"]
```

**Deployment Environments**

| Environment | Server | Database | Redis | Cost | Updates |
|---|---|---|---|---|---|
| Development | Local laptop | Local SQLite | Local Redis | $0 | Any time |
| Staging | Small VM | Managed RDS | Managed Redis | $50/mo | Before production |
| Production | Medium VM | Managed RDS | Managed Redis | $100/mo | Scheduled downtime |

**Deployment Process**

```
1. GitHub Push
   └─→ Trigger webhook

2. CI Pipeline (GitHub Actions)
   ├─→ Run tests
   ├─→ Build Docker image
   ├─→ Push to Docker registry
   └─→ Deploy to staging

3. Manual Testing on Staging
   └─→ Verify functionality

4. Production Deployment (Manual)
   ├─→ Pull latest Docker image
   ├─→ Run migrations (if DB schema changed)
   ├─→ Stop old container
   ├─→ Start new container
   ├─→ Verify health check passing
   └─→ Gradual traffic migration

5. Rollback (If needed)
   ├─→ Revert to previous image
   ├─→ Stop current container
   ├─→ Start previous version
```

**Scalability Path** (if needed)

```
Current (Single instance):
  - 10 concurrent users
  - 10 concurrent requests
  - Sub-500ms response times

Phase 2 (Multiple instances):
  - Load balancer (nginx)
  - 3 API containers
  - Shared PostgreSQL + Redis
  - ~50 concurrent users

Phase 3 (Kubernetes):
  - EKS or GKE cluster
  - Auto-scaling to 100+ users
  - Database sharding
```

## Consequences

### Positive
- Simple: single Docker image, straightforward deployment
- Fast: 6-week timeline realistic with this approach
- Cost-effective: ~$100/month for small VM + managed services
- Familiar: standard Docker workflow; most teams know this pattern
- Scalable: can move to multi-container if traffic increases
- Stateless: containers can restart without data loss (state in PostgreSQL/Redis)

### Negative
- Single point of failure: one server = one instance down
- No automatic scaling: manual intervention for traffic spikes
- No high availability: maintenance requires downtime
- Container overhead: uses more resources than bare metal
- No built-in disaster recovery
- Manual deployment process prone to human error

### Acceptable for MVP?
- Yes: internal tool; downtime acceptable for <50 users
- Yes: scalability not critical at launch
- Yes: DevOps overhead minimal

## Alternatives Considered

### Kubernetes (EKS/GKE)
- Better: auto-scaling, high availability, industry standard
- Worse: significant setup complexity; not justified for 10 users
- Decision: Rejected for MVP; keep as Phase 2 upgrade

### Serverless (AWS Lambda)
- Better: no server management; built-in scaling
- Worse: cold starts problematic for daily batch jobs; harder to manage state
- Decision: Rejected; stateful pipeline not well-suited to serverless

### Virtual Machine (No Containers)
- Better: simpler if team knows sysadmin
- Worse: harder to reproduce; no isolation; harder to scale
- Decision: Docker containers provide necessary abstraction

### Bare Metal Server
- Rejected: over-complex; Docker simpler

## Monitoring & Maintenance

```
Daily:
  - Check health endpoint (GET /health)
  - Review error logs

Weekly:
  - Review performance metrics
  - Check disk space

Monthly:
  - Security patches
  - Dependency updates
  - Database maintenance

Quarterly:
  - Full disaster recovery test
  - Capacity planning review
```

## Related Decisions
- ADR-0001: Technology Stack (Docker-friendly stack)
- ADR-0002: Data Architecture (stateless design enables containerization)
- ADR-0007: Monitoring & Observability
