# Docker Setup Guide - Draft Queen

Complete guide for building, running, and deploying Draft Queen using Docker and Docker Compose.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Architecture](#architecture)
4. [Configuration](#configuration)
5. [Common Commands](#common-commands)
6. [Development Workflow](#development-workflow)
7. [Production Deployment](#production-deployment)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required
- Docker 20.10+ ([Install Docker](https://docs.docker.com/get-docker/))
- Docker Compose 2.0+ ([Install Docker Compose](https://docs.docker.com/compose/install/))
- At least 4GB RAM available for containers
- Git (for cloning the repository)

### Optional
- Make (for running Makefile commands)
- VS Code Remote Containers extension
- Docker Desktop (for GUI management)

---

## Quick Start

### 1. Clone Repository
```bash
git clone <repository-url>
cd draft-queen
```

### 2. Configure Environment
```bash
# Copy example environment file
cp .env.example .env

# Edit for your setup (optional - defaults work for local dev)
# nano .env
```

### 3. Build Images
```bash
# Build all services
docker-compose build

# Or build specific service
docker-compose build api
docker-compose build pipeline
```

### 4. Start Services
```bash
# Start all services
docker-compose up -d

# Or with logs
docker-compose up

# Start specific service
docker-compose up -d api
```

### 5. Verify Services
```bash
# Check status
docker-compose ps

# View logs
docker-compose logs -f api

# Test API health
curl http://localhost:8000/health
```

### 6. Access Services
- **API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **Database:** localhost:5432
- **Redis:** localhost:6379
- **pgAdmin:** http://localhost:5050

---

## Architecture

### Services

```
┌─────────────────────────────────────────┐
│          Draft Queen Stack              │
├─────────────────────────────────────────┤
│                                         │
│  ┌──────────────┐  ┌──────────────┐   │
│  │   FastAPI    │  │    ETL       │   │
│  │    API       │  │   Pipeline   │   │
│  │ :8000        │  │              │   │
│  └──────┬───────┘  └────────┬─────┘   │
│         │                   │         │
│         └───────────┬───────┘         │
│                     │                 │
│         ┌───────────┼───────────┐    │
│         │           │           │    │
│    ┌────▼──┐  ┌─────▼───┐ ┌───▼──┐ │
│    │  DB   │  │  Redis  │ │pgAdmin│ │
│    │ :5432 │  │ :6379   │ │:5050  │ │
│    └───────┘  └─────────┘ └───────┘ │
│                                      │
└──────────────────────────────────────┘
```

### Volumes

- **postgres_data:** Database storage (persisted)
- **redis_data:** Cache storage (persisted)
- **pgadmin_data:** pgAdmin configuration (persisted)
- **./data:** Application data directory (mounted)
- **./logs:** Application logs (mounted)

### Networks

- **draft-queen-network:** Internal bridge network for service communication
- All services communicate via container hostnames (e.g., `db`, `redis`)

---

## Configuration

### Environment Variables

Create `.env` file from `.env.example`:

```bash
cp .env.example .env
```

Key variables:

```env
# Docker/Container Settings
ENVIRONMENT=development          # development, staging, production
LOG_LEVEL=INFO                  # DEBUG, INFO, WARNING, ERROR

# Database
DB_HOST=db                      # Docker service name
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres            # Change in production!
DB_NAME=draft_queen

# Redis
REDIS_URL=redis://redis:6379/0

# API
API_PORT=8000
API_HOST=0.0.0.0

# pgAdmin (dev only)
PGADMIN_EMAIL=admin@example.com
PGADMIN_PASSWORD=admin
PGADMIN_PORT=5050
```

### Docker Compose Profiles

Development (default):
```bash
docker-compose up
```

Development with pgAdmin:
```bash
docker-compose --profile dev up
```

---

## Common Commands

### Container Management

```bash
# Start services
docker-compose up -d

# Stop services (keep data)
docker-compose stop

# Stop and remove containers
docker-compose down

# Remove containers and volumes (DESTRUCTIVE!)
docker-compose down -v

# View logs
docker-compose logs -f
docker-compose logs -f api
docker-compose logs -f pipeline

# View service status
docker-compose ps
```

### Image Management

```bash
# Build images
docker-compose build

# Rebuild without cache
docker-compose build --no-cache

# Build specific service
docker-compose build api

# View images
docker images | grep draft-queen
```

### Database Management

```bash
# Access database
docker-compose exec db psql -U postgres -d draft_queen

# Run migrations
docker-compose exec api alembic upgrade head

# Create migration
docker-compose exec api alembic revision --autogenerate -m "message"

# Access pgAdmin
# Open http://localhost:5050
# Username: admin@example.com
# Password: admin
```

### Debugging

```bash
# Execute command in container
docker-compose exec api bash
docker-compose exec pipeline bash

# View Python logs in API
docker-compose exec api tail -f logs/api.log

# Check environment variables
docker-compose exec api env

# Health check
docker-compose exec api curl http://localhost:8000/health
```

---

## Development Workflow

### Hot Reload

Volumes are mounted, so changes are reflected immediately:

```bash
# Start with hot reload
docker-compose up -d api

# Edit code locally
nano backend/api/routes.py

# Changes are reflected in the container
# Uvicorn will auto-reload with --reload flag
```

### Adding Dependencies

```bash
# Update pyproject.toml
nano pyproject.toml

# Install locally (development)
poetry install

# Update containers
docker-compose build
docker-compose up -d api
```

### Running Tests

```bash
# Run tests in container
docker-compose exec api pytest tests/

# Run specific test
docker-compose exec api pytest tests/unit/test_pff_scraper.py -v

# With coverage
docker-compose exec api pytest --cov=backend tests/
```

### Database Migrations

```bash
# Create new migration
docker-compose exec api alembic revision --autogenerate -m "Add new table"

# Apply migrations
docker-compose exec api alembic upgrade head

# Check migration status
docker-compose exec api alembic current
```

---

## Production Deployment

### Before Deployment

1. **Update Configuration**
   ```bash
   # Create production .env file
   cp .env.example .env.prod
   nano .env.prod
   
   # Update critical values
   ENVIRONMENT=production
   DB_PASSWORD=<strong-random-password>
   PGADMIN_PASSWORD=<strong-random-password>
   ```

2. **Security**
   - Change all default passwords
   - Use secrets management (Docker Secrets, Vault)
   - Use HTTPS/TLS for API
   - Configure firewall rules

3. **Performance**
   - Increase resource limits
   - Use external database (RDS, Cloud SQL)
   - Use external Redis (ElastiCache, MemoryStore)
   - Configure load balancer

### Deployment Steps

```bash
# 1. Build on production server
docker-compose -f docker-compose.yml build

# 2. Start services
docker-compose -f docker-compose.yml up -d

# 3. Run migrations
docker-compose -f docker-compose.yml exec api alembic upgrade head

# 4. Verify services
docker-compose -f docker-compose.yml ps

# 5. Check logs
docker-compose -f docker-compose.yml logs -f
```

### Production docker-compose Override

Create `docker-compose.prod.yml`:

```yaml
version: '3.9'

services:
  api:
    restart: always
    environment:
      ENVIRONMENT: production
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '1'
          memory: 1G

  db:
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_backup:/var/lib/postgresql/backup

  redis:
    command: redis-server --appendonly yes
```

Run with: `docker-compose -f docker-compose.yml -f docker-compose.prod.yml up`

---

## Troubleshooting

### Services Won't Start

```bash
# Check logs
docker-compose logs

# Check service status
docker-compose ps

# Rebuild images
docker-compose build --no-cache

# Remove dangling images
docker system prune
```

### Database Connection Issues

```bash
# Test database connection
docker-compose exec api psql postgresql://${DB_USER}:${DB_PASSWORD}@db:5432/${DB_NAME}

# Check database logs
docker-compose logs db

# Verify environment variables
docker-compose exec api env | grep DB_
```

### Memory/Performance Issues

```bash
# View resource usage
docker stats

# Increase Docker memory limit
# Docker Desktop > Preferences > Resources > Memory

# Or in docker-compose.yml:
services:
  db:
    deploy:
      resources:
        limits:
          memory: 2G
```

### Port Conflicts

```bash
# Check port usage
lsof -i :8000
lsof -i :5432

# Change port in .env
API_PORT=8001
DB_PORT=5433

# Restart services
docker-compose restart
```

### Volume Permission Issues

```bash
# Fix volume ownership
docker-compose exec db chown -R postgres:postgres /var/lib/postgresql/data

# For application volumes
docker-compose exec api chown -R appuser:appuser /app/data
```

### Clean Slate

```bash
# Remove everything (DESTRUCTIVE)
docker-compose down -v

# Rebuild and restart
docker-compose build --no-cache
docker-compose up -d

# Initialize database
docker-compose exec api alembic upgrade head
```

---

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [PostgreSQL Docker Image](https://hub.docker.com/_/postgres)
- [Redis Docker Image](https://hub.docker.com/_/redis)
- [pgAdmin Documentation](https://www.pgadmin.org/docs/)

---

## Support

For issues or questions:
1. Check logs: `docker-compose logs -f <service>`
2. Review error messages in troubleshooting section above
3. Check Docker and Docker Compose installation
4. Verify .env configuration

