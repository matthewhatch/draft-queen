# US-045: Dockerize Application for Production Deployment - Implementation Plan

**Story:** Dockerize Application for Production Deployment  
**Sprint:** Sprint 4  
**Effort:** 5 story points  
**Status:** IN PROGRESS  

---

## Overview

US-045 requires containerizing the entire NFL Draft Queen application for consistent multi-environment deployment. This includes:
- Backend API (FastAPI)
- Data pipeline (ETL worker)
- CLI tools
- PostgreSQL database
- Redis cache
- Supporting services

---

## Architecture

```
Docker Compose Stack
├── API Service (FastAPI)
│   ├── Port: 8000
│   ├── Health check: /health
│   └── Depends on: db, redis
├── Pipeline Service (ETL Worker)
│   ├── Scheduled tasks
│   ├── Data ingestion
│   └── Depends on: db, redis
├── PostgreSQL Database
│   ├── Port: 5432
│   ├── Volume: postgres_data
│   └── Init scripts: migrations
├── Redis Cache
│   ├── Port: 6379
│   └── Volume: redis_data
└── pgAdmin (optional, dev only)
    ├── Port: 5050
    └── Database UI
```

---

## Task Breakdown

### Task 1: Dockerfile for Backend API
- Base: python:3.11-slim
- Install system dependencies
- Copy pyproject.toml and install Poetry dependencies
- Copy application code
- Expose port 8000
- Entrypoint: uvicorn

### Task 2: Dockerfile for Data Pipeline
- Base: python:3.11-slim (reuse from Task 1)
- Install dependencies (same as API)
- Copy application code
- Entrypoint: pipeline scheduler

### Task 3: docker-compose.yml
- Service definitions (API, pipeline, db, redis)
- Network configuration
- Volume mounts
- Environment variables
- Startup order and health checks
- .env file support

### Task 4: Container Initialization Scripts
- Database initialization (alembic migrations)
- Entrypoint scripts for each service
- Health check scripts
- Configuration management

### Task 5: Documentation
- Docker setup guide
- Local development with Docker
- Production deployment guide
- Environment configuration reference
- Troubleshooting guide

---

## Key Requirements

### Base Images
- API & Pipeline: python:3.11-slim
- Database: postgres:15-alpine
- Cache: redis:7-alpine

### Security
- Non-root user (appuser)
- Minimal image layers
- .dockerignore to exclude dev files
- No secrets in Dockerfile

### Performance
- Multi-stage builds
- Layer caching optimization
- Minimal final image size

### Development
- Volume mounts for code hot-reload
- Debug logging enabled
- pgAdmin for database inspection

### Production
- Health checks
- Graceful shutdown
- Proper logging to stdout/stderr
- Environment-based configuration

---

## Files to Create

1. **docker/Dockerfile.api** - FastAPI backend
2. **docker/Dockerfile.pipeline** - ETL worker
3. **docker/entrypoint.api.sh** - API startup script
4. **docker/entrypoint.pipeline.sh** - Pipeline startup script
5. **docker/init-db.sh** - Database initialization
6. **docker/.dockerignore** - Exclude build files
7. **docker-compose.yml** - Service orchestration
8. **docker-compose.prod.yml** - Production overrides
9. **.env.example** - Environment template
10. **docs/DOCKER_SETUP.md** - Implementation guide

---

## Implementation Status

- [ ] Task 1: Dockerfile for API
- [ ] Task 2: Dockerfile for Pipeline
- [ ] Task 3: docker-compose.yml
- [ ] Task 4: Initialization scripts
- [ ] Task 5: Documentation
- [ ] Verification: All services start
- [ ] Verification: Database initializes
- [ ] Verification: Services communicate
- [ ] Verification: Volumes persist data
- [ ] Verification: Environment config works

---

## Success Criteria

✅ All services start and run successfully  
✅ Database initializes automatically on first run  
✅ Services communicate correctly (API talks to DB)  
✅ Volumes persist data across container restarts  
✅ Environment variables properly applied  
✅ Startup and shutdown graceful  
✅ Documentation complete and tested  
✅ Build works on Linux, macOS, Windows  
✅ Security best practices followed  
✅ Performance acceptable (image size, startup time)  

