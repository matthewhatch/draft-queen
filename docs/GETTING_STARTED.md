# Getting Started - NFL Draft Analytics Platform

Quick setup guide for new team members. Takes ~30 minutes.

---

## Prerequisites

- Python 3.11+
- Docker & Docker Compose
- PostgreSQL 15+ (managed by Docker)
- Git

---

## Quick Setup (5 minutes)

### 1. Clone & Navigate
```bash
cd /home/parrot/code/draft-queen
```

### 2. Environment Setup
```bash
# Copy template
cp .env.example .env

# (Edit .env with your settings if needed)
```

### 3. Start Services
```bash
docker-compose up -d
```

Services running:
- ✅ PostgreSQL (port 5432)
- ✅ Redis (port 6379)

### 4. Initialize Database
```bash
# Run migrations
alembic upgrade head

# (Optional) Seed initial data
python scripts/seed_prospects.py
```

### 5. Start API
```bash
python main.py
```

API running at: `http://localhost:8000`

---

## Project Structure

```
/home/parrot/code/draft-queen/
├── backend/              ← FastAPI application
│   ├── api/             ← Endpoints
│   ├── models/          ← SQLAlchemy models
│   └── schemas/         ← Pydantic schemas
├── data_pipeline/        ← ETL & scrapers
│   ├── scrapers/        ← Web scrapers (NFL, Yahoo, ESPN, PFF)
│   ├── reconciliation/  ← Data conflict resolution
│   └── orchestration/   ← Daily pipeline scheduler
├── cli/                  ← Command-line tools
├── notebooks/            ← Jupyter analytics notebooks
├── tests/                ← Test suite
├── scripts/              ← Operational scripts
├── migrations/           ← Alembic database migrations
├── docker/               ← Docker configurations
└── docs/                 ← Documentation (you are here)
```

---

## By Role

### Backend Engineer

**First day tasks:**
1. Read: `docs/guides/AGENT_INSTRUCTIONS_BACKEND.md`
2. Architecture: `docs/architecture/0001-technology-stack.md`, `0003-api-design.md`
3. Run: Backend server (see above)
4. Test: `curl http://localhost:8000/api/prospects`
5. Check current sprint: `docs/sprint-planning/SPRINT_PLANS.md`

**Key files:**
- API: `/backend/api/main.py`
- Models: `/backend/models/prospect.py`
- Tests: `/tests/test_api.py`

### Data Engineer

**First day tasks:**
1. Read: `docs/guides/AGENT_INSTRUCTIONS_DATA_PIPELINE.md`
2. Setup guide: `docs/guides/DATA_ENGINEER_IMPLEMENTATION_GUIDE.md`
3. Architecture: `docs/architecture/0002-data-architecture.md`, `0009-data-sourcing.md`
4. Test pipeline: `python scripts/run_yahoo_scraper.py`
5. Check current sprint: `docs/sprint-planning/SPRINT_PLANS.md`

**Key files:**
- Pipeline: `/data_pipeline/orchestration/pipeline.py`
- Scrapers: `/data_pipeline/scrapers/`
- Reconciliation: `/data_pipeline/reconciliation/`

### Frontend/DevTools Engineer

**First day tasks:**
1. Read: `docs/guides/AGENT_INSTRUCTIONS_FRONTEND.md`
2. Docker setup: `docs/guides/DOCKER_SETUP.md`
3. Launch Jupyter: `jupyter lab notebooks/`
4. Explore data: Open sample notebooks
5. Check current sprint: `docs/sprint-planning/SPRINT_PLANS.md`

**Key files:**
- Notebooks: `/notebooks/`
- Docker config: `/docker/` & `docker-compose.yml`

---

## Common Commands

### Database
```bash
# Start database
docker-compose up -d

# Run migrations
alembic upgrade head

# Reset database
python scripts/clean_database.py

# Seed test data
python scripts/seed_prospects.py
```

### Development
```bash
# Start API server
python main.py

# Run tests
pytest tests/ -v

# Check code quality
pylint backend/ data_pipeline/

# Start Jupyter
jupyter lab notebooks/
```

### Data Pipeline
```bash
# Test PFF scraper
python scripts/test_pff_scraper.py

# Test Yahoo Sports scraper
python scripts/run_yahoo_scraper.py

# Run full pipeline
python data_pipeline/orchestration/pipeline.py
```

---

## API Quick Reference

### Check API Status
```bash
curl http://localhost:8000/health
```

### Get All Prospects
```bash
curl http://localhost:8000/api/prospects | python -m json.tool | head -20
```

### Get Prospect by ID
```bash
curl http://localhost:8000/api/prospects/1 | python -m json.tool
```

### Query by Position
```bash
curl "http://localhost:8000/api/prospects?position=QB" | python -m json.tool
```

---

## Database Access

### Connect via CLI
```bash
docker exec -it draft-queen-db psql -U draft_user -d draft_db
```

### Common Queries
```sql
-- Show all tables
\dt

-- Count prospects
SELECT COUNT(*) FROM prospects;

-- Show columns in a table
\d prospects

-- Query prospects
SELECT id, name, position, college FROM prospects LIMIT 10;
```

---

## Troubleshooting

### Services won't start
```bash
# Check if ports are in use
lsof -i :5432   # PostgreSQL
lsof -i :6379   # Redis
lsof -i :8000   # API

# Kill conflicting process and try again
kill -9 <PID>
docker-compose up -d
```

### Database connection error
```bash
# Check database logs
docker-compose logs db

# Verify connection in .env
# Should have: DATABASE_URL=postgresql://draft_user:draft_pass@localhost:5432/draft_db
```

### Scraper failing
```bash
# Check logs
tail -f logs/pipeline.log

# Test scraper directly
python scripts/run_yahoo_scraper.py
```

### Tests failing
```bash
# Run tests with verbose output
pytest tests/ -v -s

# Run specific test
pytest tests/test_scrapers.py::TestNFLScraper -v
```

---

## Documentation

All documentation is in `/docs/`:

- **Architecture:** `/docs/architecture/` - 10 ADRs covering all major decisions
- **Sprint Planning:** `/docs/sprint-planning/` - User stories and roadmap
- **Guides:** `/docs/guides/` - Agent instructions and setup
- **Decisions:** `/docs/decisions/` - Historical sprint reports and outcomes

**Start here:** `/docs/README.md` for navigation

---

## Next Steps

1. **Read your role's agent instructions** (`docs/guides/AGENT_INSTRUCTIONS_*.md`)
2. **Understand architecture** (start with ADR-0001, ADR-0002)
3. **Check current sprint** (`docs/sprint-planning/SPRINT_PLANS.md`)
4. **Join standup** (daily 10 AM)
5. **Pick first task** from current sprint user stories

---

## Support

- **Questions?** Check the relevant ADR or guide first
- **Bug found?** Create an issue in the issue tracker
- **Need help?** Reach out on team Slack or in standup

---

**Last Updated:** February 13, 2026
