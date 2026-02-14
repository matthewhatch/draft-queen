# Deployment & Running Guide

Complete guide for running Draft Queen locally and deploying to production.

---

## Table of Contents

1. [Local Development](#local-development)
2. [Production Deployment](#production-deployment)
3. [Docker Deployment](#docker-deployment)
4. [Environment Configuration](#environment-configuration)
5. [Database Management](#database-management)
6. [Troubleshooting](#troubleshooting)

---

## Local Development

### Prerequisites

- **Python**: 3.11+
- **PostgreSQL**: 14+ (can use Docker)
- **Redis**: 6+ (can use Docker)
- **Docker & Docker Compose**: For running services

### Quick Start (5 minutes)

#### Step 1: Clone Repository
```bash
git clone <repository-url>
cd draft-queen
```

#### Step 2: Create Python Virtual Environment
```bash
# Create virtual environment
python3.11 -m venv env

# Activate it
source env/bin/activate  # On Windows: env\Scripts\activate
```

#### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

#### Step 4: Setup Environment Variables
```bash
# Copy template
cp .env.example .env

# Edit with your settings (if needed)
nano .env  # or use your editor
```

**Key variables for local development:**
```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_USERNAME=postgres
DB_PASSWORD=postgres
DB_DATABASE=nfl_draft

# API
DEBUG=true
ENVIRONMENT=development
ADMIN_API_KEY=your-test-key-here

# Email (optional for local)
EMAIL_ENABLED=false

# Scheduler
SCHEDULER_ENABLED=true
```

#### Step 5: Start Database Services
```bash
# Start PostgreSQL and Redis with Docker Compose
docker-compose up -d
```

Verify services:
```bash
# Check if containers are running
docker-compose ps

# Test PostgreSQL connection
psql -U postgres -d nfl_draft -c "SELECT version();"

# Test Redis connection
redis-cli ping
```

#### Step 6: Initialize Database
```bash
# Run migrations
alembic upgrade head

# (Optional) Seed test data
python scripts/seed_prospects.py
```

#### Step 7: Start API Server
```bash
# Development server (auto-reload on changes)
python main.py

# Or with hot reload
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

API available at: **http://localhost:8000**

#### Step 8: Start Frontend (Optional)
```bash
# In separate terminal
cd frontend
npm install
npm run dev

# Frontend available at: http://localhost:3000
```

### Verify Installation

```bash
# Check API health
curl http://localhost:8000/health

# Check API docs
open http://localhost:8000/docs

# Check quality endpoints
curl http://localhost:8000/api/quality/alerts

# Check Redis
redis-cli INFO
```

### Common Local Development Tasks

#### Restart Services
```bash
# Stop everything
docker-compose down

# Start again
docker-compose up -d

# Restart just PostgreSQL
docker-compose restart postgres
```

#### View Database
```bash
# Connect to PostgreSQL
psql -U postgres -d nfl_draft

# Common queries
SELECT * FROM prospects LIMIT 5;
SELECT * FROM quality_alerts LIMIT 5;
\dt  -- List all tables
\q   -- Exit
```

#### View Logs
```bash
# API logs (from running terminal)
# Ctrl+C to stop

# Docker logs
docker-compose logs -f postgres
docker-compose logs -f redis

# Specific container
docker-compose logs -f postgres --tail 20
```

#### Reset Database
```bash
# Drop all data and restart
docker-compose down -v
docker-compose up -d
alembic upgrade head
python scripts/seed_prospects.py
```

#### Run Tests Locally
```bash
# All tests
pytest

# Specific test file
pytest tests/unit/test_quality_api.py -v

# With coverage
pytest --cov=src tests/

# Watch mode (requires pytest-watch)
ptw
```

---

## Production Deployment

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Production Environment                                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Web Server (Nginx or similar)                        │   │
│  │ - TLS/SSL termination                                │   │
│  │ - Load balancing (if needed)                         │   │
│  │ - Reverse proxy to API                               │   │
│  └──────────────────────────────────────────────────────┘   │
│                           │                                  │
│  ┌────────────────────────▼──────────────────────────────┐  │
│  │ API Container (Docker)                               │  │
│  │ - FastAPI application                                │  │
│  │ - Gunicorn WSGI server                               │  │
│  │ - 4 workers for concurrency                          │  │
│  └────────────────────────▼──────────────────────────────┘  │
│                           │                                  │
│  ┌────────────────────────┴──────────────────────────────┐  │
│  │ PostgreSQL Database                                  │  │
│  │ - Production-grade instance                          │  │
│  │ - Automated backups (daily)                          │  │
│  │ - Read replicas (optional)                           │  │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Redis Cache                                          │   │
│  │ - Session storage                                    │   │
│  │ - APScheduler job store                              │   │
│  │ - Alert cache                                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Monitoring & Logging                                 │   │
│  │ - Application logs (structured)                      │   │
│  │ - Performance metrics                                │   │
│  │ - Error tracking                                     │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Pre-Deployment Checklist

- [ ] All tests passing (`pytest`)
- [ ] Environment variables configured for production
- [ ] Database backups configured
- [ ] TLS certificates obtained (Let's Encrypt)
- [ ] Email SMTP credentials configured
- [ ] Monitoring/alerting configured
- [ ] Deployment procedure reviewed
- [ ] Rollback procedure tested

### Deployment Steps

#### Step 1: Prepare Code
```bash
# Pull latest code
git fetch origin
git checkout main
git pull origin main

# Verify build
python -m py_compile src/main.py
pytest
```

#### Step 2: Build Docker Image
```bash
# Build image
docker build -f docker/Dockerfile.api -t draft-queen:latest .

# Tag for registry (if using Docker Hub or similar)
docker tag draft-queen:latest yourregistry/draft-queen:latest
docker push yourregistry/draft-queen:latest
```

#### Step 3: Stop Current Service
```bash
# Gracefully stop current container
docker-compose -f docker-compose.prod.yml down

# Or with zero downtime: keep old container while new starts
```

#### Step 4: Run Database Migrations
```bash
# Update database schema if needed
docker run --rm \
  -e DB_HOST=prod-db \
  -e DB_USER=postgres \
  -e DB_PASSWORD=$DB_PASSWORD \
  draft-queen:latest \
  alembic upgrade head
```

#### Step 5: Start New Service
```bash
# Start with production compose file
docker-compose -f docker-compose.prod.yml up -d

# Verify it's running
docker-compose -f docker-compose.prod.yml ps
```

#### Step 6: Verify Deployment
```bash
# Check API health
curl https://your-domain.com/health

# Check logs
docker-compose -f docker-compose.prod.yml logs api

# Run smoke tests
./scripts/smoke_tests.sh
```

#### Step 7: Monitor
```bash
# Watch logs for errors
docker-compose -f docker-compose.prod.yml logs -f api

# Check system resources
docker stats

# Monitor application metrics
# (Point your monitoring tool at /metrics endpoint)
```

### Rollback Procedure

If deployment has critical issues:

```bash
# Stop new version
docker-compose -f docker-compose.prod.yml down

# Start previous version from registry
docker-compose -f docker-compose.prod.yml up -d

# Or restore from snapshot:
# 1. Restore database from backup
# 2. Start API from previous container image
```

### Zero-Downtime Deployment

For critical services:

```bash
# Keep old container running while new starts
docker run -d \
  --name draft-queen-new \
  -p 8001:8000 \
  draft-queen:latest

# Test new container
curl http://localhost:8001/health

# If good: switch traffic via load balancer/nginx
# If bad: kill new container, keep old running
```

---

## Docker Deployment

### Docker Compose Files

**Development** (`docker-compose.yml`):
```yaml
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: nfl_draft
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

**Production** (`docker-compose.prod.yml`):
```yaml
version: '3.8'
services:
  api:
    image: yourregistry/draft-queen:latest
    ports:
      - "8000:8000"
    environment:
      ENVIRONMENT: production
      DB_HOST: postgres
      REDIS_URL: redis://redis:6379
    depends_on:
      - postgres
      - redis
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    image: postgres:15
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: nfl_draft
    volumes:
      - postgres_prod_data:/var/lib/postgresql/data
    restart: always

  redis:
    image: redis:7
    restart: always

volumes:
  postgres_prod_data:
```

### Build Docker Image

```dockerfile
# Dockerfile.api
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Run migrations and start app
CMD ["sh", "-c", "alembic upgrade head && gunicorn --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 src.main:app"]
```

Build and run:
```bash
# Build
docker build -f docker/Dockerfile.api -t draft-queen:latest .

# Run
docker run -d \
  -e DB_HOST=localhost \
  -e DB_PASSWORD=postgres \
  -p 8000:8000 \
  draft-queen:latest
```

---

## Environment Configuration

### Development (.env)

```bash
# App
APP_NAME="Draft Queen"
ENVIRONMENT=development
DEBUG=true
ADMIN_API_KEY=dev-key-only-for-testing-12345678

# Database
DB_HOST=localhost
DB_PORT=5432
DB_USERNAME=postgres
DB_PASSWORD=postgres
DB_DATABASE=nfl_draft

# Email
EMAIL_ENABLED=false
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=noreply@draft-queen.local
USE_TLS=true

# Scheduler
SCHEDULER_ENABLED=true

# Logging
LOGGING_LEVEL=DEBUG
LOGGING_FORMAT=json
```

### Production (.env)

```bash
# App
APP_NAME="Draft Queen"
ENVIRONMENT=production
DEBUG=false
ADMIN_API_KEY=your-secure-key-here-very-long-and-random

# Database
DB_HOST=prod-postgres.example.com
DB_PORT=5432
DB_USERNAME=prod_user
DB_PASSWORD=your-secure-password-here
DB_DATABASE=nfl_draft_prod

# Email
EMAIL_ENABLED=true
SMTP_HOST=smtp.aws.amazon.com
SMTP_PORT=587
SMTP_USER=your-ses-user
SMTP_PASSWORD=your-ses-password
SENDER_EMAIL=alerts@company.com
ALERT_RECIPIENTS=team@company.com
USE_TLS=true

# Scheduler
SCHEDULER_ENABLED=true

# Logging
LOGGING_LEVEL=INFO
LOGGING_FORMAT=json
LOGGING_LOG_DIR=/var/log/draft-queen

# Security
ALLOWED_HOSTS=quality.company.com
CORS_ORIGINS=https://quality.company.com
```

### Environment Variable Reference

| Variable | Default | Purpose |
|----------|---------|---------|
| `ENVIRONMENT` | development | Env: development, staging, production |
| `DEBUG` | false | Enable debug mode (never in production) |
| `DB_HOST` | localhost | Database host |
| `DB_PORT` | 5432 | Database port |
| `EMAIL_ENABLED` | false | Enable email notifications |
| `SCHEDULER_ENABLED` | true | Enable APScheduler jobs |
| `LOGGING_LEVEL` | INFO | Log level: DEBUG, INFO, WARNING, ERROR |

---

## Database Management

### Migrations

#### Create New Migration
```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "Add new column to alerts"

# Manual migration
alembic revision -m "Manual migration description"

# Edit the file in migrations/versions/
```

#### Apply Migrations
```bash
# Apply all pending migrations
alembic upgrade head

# Apply specific migration
alembic upgrade abc123def456

# Rollback one migration
alembic downgrade -1

# Rollback all migrations
alembic downgrade base
```

#### Check Migration Status
```bash
# Show current version
alembic current

# Show all migrations
alembic history --verbose
```

### Backups

#### Manual Backup
```bash
# Backup PostgreSQL
pg_dump -U postgres -d nfl_draft > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore from backup
psql -U postgres -d nfl_draft < backup_20240214_120000.sql
```

#### Automated Backups (Production)
```bash
# Add to cron job (runs daily at 2 AM)
0 2 * * * pg_dump -U postgres -d nfl_draft > /backups/db_$(date +\%Y\%m\%d).sql

# Keep last 30 days
0 3 * * * find /backups -name "db_*.sql" -mtime +30 -delete
```

### Performance

#### Check Slow Queries
```bash
# In PostgreSQL
SELECT * FROM pg_stat_statements 
ORDER BY total_time DESC LIMIT 10;

# Analyze query plan
EXPLAIN ANALYZE SELECT * FROM quality_alerts WHERE severity='critical';
```

#### Create Indexes
```bash
# Manually in psql
CREATE INDEX idx_alerts_severity ON quality_alerts(severity);
CREATE INDEX idx_alerts_position ON quality_alerts(position);
CREATE INDEX idx_alerts_created ON quality_alerts(created_at DESC);
```

---

## Troubleshooting

### Common Issues

#### Database Connection Failed
```bash
# Check if PostgreSQL is running
docker-compose ps

# Verify connection string
echo $DB_HOST $DB_PORT $DB_USERNAME

# Test connection manually
psql -U postgres -h localhost -d nfl_draft

# Check logs
docker-compose logs postgres
```

#### API Not Starting
```bash
# Check Python syntax
python -m py_compile src/main.py

# Check imports
python -c "from src.main import app; print('OK')"

# Run with verbose logging
python main.py --log-level DEBUG

# Check logs
docker-compose logs api
```

#### Email Not Sending
```bash
# Test SMTP connection
python -c "
import smtplib
smtp = smtplib.SMTP('$SMTP_HOST', $SMTP_PORT)
smtp.starttls()
smtp.login('$SMTP_USER', '$SMTP_PASSWORD')
print('✓ SMTP OK')
smtp.quit()
"

# Check email scheduler logs
grep -i email logs/app.log

# Test with MailHog (local testing)
docker run -d -p 1025:1025 -p 8025:8025 mailhog/mailhog
```

#### High Memory Usage
```bash
# Check container memory
docker stats draft-queen

# If high, check what's using memory
ps aux | head -20

# Restart container
docker-compose restart api

# If persistent, review connection pool settings
# Reduce worker count in Gunicorn config
```

#### Slow API Responses
```bash
# Check database performance
psql -U postgres -d nfl_draft -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 5;"

# Create missing indexes (see Database Management section)

# Monitor API performance
curl -w "Total: %{time_total}s\n" http://localhost:8000/api/quality/alerts
```

### Getting Help

1. **Check Logs**: Most issues visible in application logs
   ```bash
   docker-compose logs -f api
   ```

2. **Check Health Endpoint**:
   ```bash
   curl http://localhost:8000/health
   ```

3. **Review Documentation**:
   - [Getting Started](GETTING_STARTED.md)
   - [Email Configuration](EMAIL_CONFIGURATION.md)
   - [Architecture](architecture/)

4. **Check Git Issues**: Look for similar issues reported

---

## Quick Reference

### Start Services
```bash
docker-compose up -d
```

### Start API
```bash
python main.py
```

### Run Tests
```bash
pytest
```

### Access API Docs
```
http://localhost:8000/docs
```

### View Database
```bash
psql -U postgres -d nfl_draft
```

### Stop All Services
```bash
docker-compose down
```

### View Logs
```bash
docker-compose logs -f
```

### Reset Everything
```bash
docker-compose down -v
docker-compose up -d
alembic upgrade head
python scripts/seed_prospects.py
```

---

**Last Updated**: February 21, 2026  
**Version**: 1.0  
**Maintained by**: Development Team
