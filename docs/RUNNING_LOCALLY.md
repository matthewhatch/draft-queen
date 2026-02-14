# Running Locally - Quick Guide

TL;DR version of getting Draft Queen running on your machine in 5 minutes.

---

## Prerequisites

- Python 3.11+
- Docker Desktop
- Git

---

## 5-Minute Setup

### 1. Clone & Navigate
```bash
git clone <repo-url>
cd draft-queen
```

### 2. Activate Python Environment
```bash
python3.11 -m venv env
source env/bin/activate  # Windows: env\Scripts\activate
pip install -r requirements.txt
```

### 3. Setup Environment
```bash
cp .env.example .env
# Edit .env if needed (usually defaults work fine)
```

### 4. Start Services
```bash
docker-compose up -d
```

### 5. Initialize Database
```bash
alembic upgrade head
```

### 6. Run API
```bash
python main.py
```

✅ **Done!** API is running at http://localhost:8000

---

## Verify It Works

### Check API
```bash
# In browser:
http://localhost:8000/docs

# Or terminal:
curl http://localhost:8000/health
```

### Check Database
```bash
psql -U postgres -d nfl_draft -c "SELECT COUNT(*) FROM prospects;"
```

### Check Redis
```bash
redis-cli ping
```

---

## Common Commands

```bash
# View API documentation
open http://localhost:8000/docs

# See API docs in terminal
curl http://localhost:8000/docs

# Check quality alerts endpoint
curl http://localhost:8000/api/quality/alerts

# Connect to database
psql -U postgres -d nfl_draft

# View Docker logs
docker-compose logs -f

# Stop everything
docker-compose down

# Reset everything
docker-compose down -v && docker-compose up -d && alembic upgrade head

# Run tests
pytest

# Run specific test
pytest tests/unit/test_quality_api.py -v
```

---

## Troubleshooting

### Can't connect to database?
```bash
# Make sure Docker is running
docker-compose ps

# Restart PostgreSQL
docker-compose restart postgres
```

### Port already in use?
```bash
# Change port in docker-compose.yml or .env
# Default ports: API=8000, Postgres=5432, Redis=6379
```

### API won't start?
```bash
# Check Python syntax
python -m py_compile src/main.py

# Check dependencies installed
pip install -r requirements.txt

# Run with verbose output
python main.py --log-level DEBUG
```

### Need fresh start?
```bash
# Stop everything
docker-compose down -v

# Start fresh
docker-compose up -d
alembic upgrade head
python main.py
```

---

## Frontend (Optional)

```bash
# In separate terminal
cd frontend
npm install
npm run dev

# Available at: http://localhost:3000
```

---

## File Structure (Key Files)

```
draft-queen/
├── main.py                ← Start API here
├── src/main.py           ← FastAPI app
├── src/backend/          ← Backend code
├── frontend/             ← React dashboard
├── docker-compose.yml    ← Docker services
├── .env.example          ← Copy to .env
├── requirements.txt      ← Python dependencies
├── alembic/              ← Database migrations
├── migrations/           ← Migration versions
├── tests/                ← Test files
└── docs/                 ← Documentation
```

---

## Need More Details?

- **Full Setup Guide**: See [DEPLOYMENT.md](DEPLOYMENT.md)
- **Getting Started**: See [GETTING_STARTED.md](GETTING_STARTED.md)
- **API Documentation**: http://localhost:8000/docs
- **Email Config**: See [EMAIL_CONFIGURATION.md](EMAIL_CONFIGURATION.md)

---

## API Quick Reference

```bash
# Get all alerts
curl http://localhost:8000/api/quality/alerts

# Get critical alerts only
curl "http://localhost:8000/api/quality/alerts?severity=critical"

# Get QB alerts
curl "http://localhost:8000/api/quality/alerts?position=QB"

# Get alert summary
curl http://localhost:8000/api/quality/alerts/summary

# Get email preview
curl http://localhost:8000/api/quality/alerts/digest

# Acknowledge alert
curl -X POST http://localhost:8000/api/quality/alerts/1/acknowledge \
  -H "Content-Type: application/json" \
  -d '{"acknowledged_by": "me"}'
```

---

**Last Updated**: February 21, 2026  
**Maintained by**: Development Team
