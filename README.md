# NFL Draft Analytics Platform

Internal data analytics platform for NFL draft evaluation. Built with Python, FastAPI, PostgreSQL, and Redis.

**Status:** 🚀 Sprint 3 In Progress (Feb 13, 2026)  
**Timeline:** 10 weeks (Feb 10 - Apr 20, 2026)  
**Team:** 3 engineers (backend, data, frontend)

---

## 📚 Quick Links

- **📖 [Documentation](docs/)** - All project docs, guides, and architecture decisions
- **🚀 [Getting Started](docs/GETTING_STARTED.md)** - Setup in 5 minutes
- **📅 [Sprint Plans](docs/sprint-planning/SPRINT_PLANS.md)** - Roadmap and user stories
- **🏗️ [Architecture](docs/architecture/)** - 10 Architecture Decision Records (ADRs)
- **👨‍💻 [Team Guides](docs/guides/)** - Role-specific implementation guides

---

## 🚀 Quick Start

### 1. Setup (5 minutes)
```bash
# Copy environment config
cp .env.example .env

# Start services
docker-compose up -d

# Initialize database
alembic upgrade head
```

### 2. Run API
```bash
python main.py
```

API: `http://localhost:8000`

### 3. View Data
```bash
# Check API status
curl http://localhost:8000/health

# Get prospects
curl http://localhost:8000/api/prospects | python -m json.tool
```

**Full setup guide:** [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)

---

## 📁 Project Structure

```
/
├── docs/                     ← All documentation
│   ├── README.md            ← Documentation index
│   ├── GETTING_STARTED.md   ← Setup guide
│   ├── architecture/        ← 10 Architecture Decision Records
│   ├── sprint-planning/     ← Sprint roadmap & user stories
│   ├── guides/              ← Agent instructions & setup guides
│   └── decisions/           ← Historical sprint outcomes
│
├── src/                      ← Application code
│   ├── backend/             ← FastAPI REST API
│   ├── data_pipeline/       ← ETL & web scrapers
│   ├── cli/                 ← Command-line tools
│   └── config.py            ← Configuration
│
├── notebooks/               ← Jupyter analytics notebooks
├── tests/                   ← Test suite
├── scripts/                 ← Operational scripts
├── migrations/              ← Database migrations (Alembic)
├── docker/                  ← Docker configurations
├── docker-compose.yml       ← Local development setup
└── pyproject.toml           ← Python dependencies
```

---

## 🎯 Project Overview

**Goal:** Build an internal analytics platform for evaluating NFL draft prospects using data from multiple sources.

**MVP Scope:** 6 weeks → 10 weeks (expanded for premium data)

**Data Sources:**
- ✅ NFL.com (Combine measurements)
- ✅ Yahoo Sports (College statistics)
- ✅ ESPN (Injury data)
- 🔄 PFF.com (Industry grades) - Sprint 4
- 📊 Multi-source analytics - Sprint 5

**Core Features:**
- REST API for prospect queries
- Multi-source data reconciliation
- Daily ETL pipeline (3 AM refresh)
- Jupyter notebooks for analysis
- Redis caching for performance
- Prometheus monitoring
- JSON/CSV/Parquet export

---

## 👥 By Role

### Backend Engineer
- **Start:** [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)
- **Read:** [docs/guides/AGENT_INSTRUCTIONS_BACKEND.md](docs/guides/AGENT_INSTRUCTIONS_BACKEND.md)
- **Code:** `/src/backend/` - FastAPI application
- **Architecture:** [docs/architecture/0001-technology-stack.md](docs/architecture/0001-technology-stack.md), [0003-api-design.md](docs/architecture/0003-api-design.md)

### Data Engineer
- **Start:** [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)
- **Read:** [docs/guides/AGENT_INSTRUCTIONS_DATA_PIPELINE.md](docs/guides/AGENT_INSTRUCTIONS_DATA_PIPELINE.md)
- **Code:** `/src/data_pipeline/` - ETL & scrapers
- **Guide:** [docs/guides/DATA_ENGINEER_IMPLEMENTATION_GUIDE.md](docs/guides/DATA_ENGINEER_IMPLEMENTATION_GUIDE.md)

### Frontend/DevTools Engineer
- **Start:** [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)
- **Read:** [docs/guides/AGENT_INSTRUCTIONS_FRONTEND.md](docs/guides/AGENT_INSTRUCTIONS_FRONTEND.md)
- **Code:** `/notebooks/` - Jupyter analytics
- **Setup:** [docs/guides/DOCKER_SETUP.md](docs/guides/DOCKER_SETUP.md)

---

## 🏗️ Architecture Highlights

### Event-Driven ETL Pipeline
Daily batch process:
1. Scrapes 4 data sources (NFL, Yahoo, ESPN, PFF)
2. Validates and reconciles conflicts
3. Tracks changes in audit trail
4. Updates materialized views
5. Alerts on quality issues

**Details:** [docs/architecture/0002-data-architecture.md](docs/architecture/0002-data-architecture.md)

### Technology Stack
- **Language:** Python 3.11
- **API:** FastAPI (async REST)
- **Database:** PostgreSQL + SQLAlchemy
- **Cache:** Redis
- **Analytics:** Jupyter notebooks
- **Monitoring:** Prometheus
- **Deployment:** Docker (single container)

**Details:** [docs/architecture/0001-technology-stack.md](docs/architecture/0001-technology-stack.md)

### Multi-Source Data Reconciliation
Handles conflicts when same prospect has data from:
- NFL.com: Official combine measurements
- Yahoo Sports: College production
- ESPN: Injury history
- PFF.com: Industry grades (upcoming)

**Details:** [docs/architecture/0009-data-sourcing.md](docs/architecture/0009-data-sourcing.md)

---

## 📅 Sprint Timeline

| Sprint | Duration | Focus | Status |
|--------|----------|-------|--------|
| 1 | Feb 10-23 | Foundation & Data Infrastructure | ✅ Complete |
| 2 | Feb 24 - Mar 9 | Advanced Querying & Reporting | ✅ Complete |
| 3 | Mar 10-23 | Data Ingestion from Real Sources | 🔄 In Progress |
| 4 | Mar 24 - Apr 6 | PFF Data Integration & Premium Analytics | 📅 Planned |
| 5 | Apr 7 - Apr 20 | Analytics & Launch Preparation | 📅 Planned |

**Full Roadmap:** [docs/sprint-planning/SPRINT_PLANS.md](docs/sprint-planning/SPRINT_PLANS.md)

---

## 🛠️ Common Commands

### Database
```bash
docker-compose up -d         # Start PostgreSQL & Redis
alembic upgrade head         # Run migrations
python scripts/seed_prospects.py  # Load test data
python scripts/clean_database.py  # Reset database
```

### Development
```bash
python main.py               # Start API server
pytest tests/ -v             # Run tests
jupyter lab notebooks/       # Open analytics environment
```

### Data Pipeline
```bash
python scripts/test_pff_scraper.py      # Test PFF scraper
python scripts/run_yahoo_scraper.py     # Test Yahoo scraper
python src/data_pipeline/orchestration/pipeline.py  # Run full pipeline
```

---

## 📊 API Examples

```bash
# Health check
curl http://localhost:8000/health

# Get all prospects
curl http://localhost:8000/api/prospects

# Get prospect by ID
curl http://localhost:8000/api/prospects/1

# Filter by position
curl "http://localhost:8000/api/prospects?position=QB"

# Get position statistics
curl http://localhost:8000/api/analytics/stats/position/QB
```

**Full API Docs:** `http://localhost:8000/docs` (Swagger UI)

---

## 🔍 Key Features

- ✅ Multi-source prospect database (5 sources)
- ✅ REST API for queries and analytics
- ✅ Data reconciliation framework
- ✅ Historical snapshots (temporal queries)
- ✅ Quality monitoring & alerts
- ✅ Jupyter analytics notebooks
- ✅ Export to JSON/CSV/Parquet
- ✅ Redis caching (< 500ms responses)
- ✅ Daily automated pipeline
- ✅ Production monitoring (Prometheus)

---

## 📚 Documentation

**Full documentation is in [docs/](docs/)**

**Quick navigation:**
- [Documentation Index](docs/README.md) - Start here for navigation
- [Getting Started](docs/GETTING_STARTED.md) - Setup guide
- [Sprint Plans](docs/sprint-planning/SPRINT_PLANS.md) - Roadmap
- [Architecture](docs/architecture/) - 10 Design Decision Records
- [Implementation Guides](docs/guides/) - Agent instructions & setup
- [Decision History](docs/decisions/) - Sprint completions & outcomes

---

## ❓ Support

**Questions?**
1. Check the [documentation index](docs/README.md)
2. Read the relevant [guide](docs/guides/)
3. Review the [Architecture Decision](docs/architecture/)
4. Ask on team Slack or in standup

**Found a bug?**
- Create an issue in the issue tracker
- Check [docs/decisions/](docs/decisions/) for known issues

---

## 🔗 Development

**Local Setup:** [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)  
**Docker Setup:** [docs/guides/DOCKER_SETUP.md](docs/guides/DOCKER_SETUP.md)  
**Data Pipeline:** [docs/guides/DATA_ENGINEER_IMPLEMENTATION_GUIDE.md](docs/guides/DATA_ENGINEER_IMPLEMENTATION_GUIDE.md)

---

**Last Updated:** February 13, 2026  
**Timeline:** Sprint 3 In Progress (Feb 13 - Feb 23)  
**Next Milestone:** Sprint 3 completion → Sprint 4 kickoff (Mar 24)
