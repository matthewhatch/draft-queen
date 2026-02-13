# Documentation Index

Welcome to the NFL Draft Analytics Platform documentation. This guide helps you navigate all project materials.

---

## 📋 Quick Navigation

### 🚀 Getting Started
- **[REQUIREMENTS.md](REQUIREMENTS.md)** - Product specification and MVP scope
- **[GETTING_STARTED.md](GETTING_STARTED.md)** - Setup instructions and first steps

### 🏗️ Architecture & Design Decisions
All architecture decisions are documented in [architecture/README.md](architecture/README.md)

**Key ADRs:**
- [ADR-0001: Technology Stack](architecture/0001-technology-stack.md) - Python/FastAPI/PostgreSQL/Redis
- [ADR-0002: Data Architecture](architecture/0002-data-architecture.md) - Event-driven ETL pipeline
- [ADR-0003: API Design](architecture/0003-api-design.md) - REST API patterns
- [ADR-0004: Caching Strategy](architecture/0004-caching-strategy.md) - Redis caching approach
- [ADR-0005: Authentication](architecture/0005-authentication.md) - API key authentication
- [ADR-0006: Deployment](architecture/0006-deployment.md) - Single Docker container
- [ADR-0007: Monitoring](architecture/0007-monitoring.md) - Prometheus monitoring
- [ADR-0008: Export Formats](architecture/0008-export-formats.md) - JSON, CSV, Parquet
- [ADR-0009: Data Sourcing](architecture/0009-data-sourcing.md) - Web scraper strategy
- [ADR-0010: PFF Data Source](architecture/0010-pff-data-source.md) - PFF.com integration

### 📅 Sprint Planning
All sprint documentation is in [sprint-planning/](sprint-planning/)

**Sprint Overview:**
- [SPRINT_PLANS.md](sprint-planning/SPRINT_PLANS.md) - Master sprint roadmap (10 weeks, 5 sprints)
- [SPRINT_1_USER_STORIES.md](sprint-planning/SPRINT_1_USER_STORIES.md) - Foundation & Data Infrastructure
- [SPRINT_2_USER_STORIES.md](sprint-planning/SPRINT_2_USER_STORIES.md) - Advanced Querying & Reporting
- [SPRINT_3_USER_STORIES.md](sprint-planning/SPRINT_3_USER_STORIES.md) - Data Ingestion from Real Sources
- [SPRINT_4_USER_STORIES.md](sprint-planning/SPRINT_4_USER_STORIES.md) - PFF Data Integration & Premium Analytics
- [SPRINT_5_USER_STORIES.md](sprint-planning/SPRINT_5_USER_STORIES.md) - Analytics & Launch Preparation

### 👨‍💻 Implementation Guides
All setup and implementation guides are in [guides/](guides/)

**Agent Instructions (by role):**
- [AGENT_INSTRUCTIONS_BACKEND.md](guides/AGENT_INSTRUCTIONS_BACKEND.md) - Backend engineer instructions
- [AGENT_INSTRUCTIONS_DATA_PIPELINE.md](guides/AGENT_INSTRUCTIONS_DATA_PIPELINE.md) - Data engineer instructions
- [AGENT_INSTRUCTIONS_FRONTEND.md](guides/AGENT_INSTRUCTIONS_FRONTEND.md) - Frontend/DevTools engineer instructions

**Setup & Implementation:**
- [DOCKER_SETUP.md](guides/DOCKER_SETUP.md) - Docker configuration and deployment
- [DATA_ENGINEER_README.md](guides/DATA_ENGINEER_README.md) - Data pipeline overview
- [DATA_ENGINEER_IMPLEMENTATION_GUIDE.md](guides/DATA_ENGINEER_IMPLEMENTATION_GUIDE.md) - Step-by-step data pipeline setup
- [POETRY_SETUP.md](guides/POETRY_SETUP.md) - Python environment setup with Poetry

### 📊 Decisions & Outcomes
Historical decisions, sprint completions, and QA reports in [decisions/](decisions/)

**Sprint Completions:**
- Sprint 1 completion and QA reports
- Sprint 2 QA reports
- Sprint 3 completion reports
- PFF scraper implementation reports (US-040, US-045)

**Project Decisions:**
- PROJECT_PIVOT_SUMMARY.md - Strategic pivot to internal analytics
- Pipeline refactoring documentation
- Bug fix and QA fix reports

---

## 📁 Directory Structure

```
docs/
├── README.md                 ← You are here
├── REQUIREMENTS.md           ← Product spec
├── GETTING_STARTED.md        ← Setup guide
├── architecture/             ← All ADRs (10 decision records)
├── sprint-planning/          ← Roadmap and user stories (5 sprints)
├── guides/                   ← Agent instructions and setup
└── decisions/                ← Historical completions, QA, outcomes
```

---

## 🎯 By Role

### Backend Engineer
1. Start: [GETTING_STARTED.md](GETTING_STARTED.md)
2. Read: [AGENT_INSTRUCTIONS_BACKEND.md](guides/AGENT_INSTRUCTIONS_BACKEND.md)
3. Architecture: [ADR-0001](architecture/0001-technology-stack.md), [ADR-0003](architecture/0003-api-design.md), [ADR-0004](architecture/0004-caching-strategy.md)
4. Current Sprint: Check [sprint-planning/SPRINT_PLANS.md](sprint-planning/SPRINT_PLANS.md) for active sprint
5. API Design: [ADR-0003](architecture/0003-api-design.md)

### Data Engineer
1. Start: [GETTING_STARTED.md](GETTING_STARTED.md)
2. Read: [AGENT_INSTRUCTIONS_DATA_PIPELINE.md](guides/AGENT_INSTRUCTIONS_DATA_PIPELINE.md)
3. Pipeline Setup: [DATA_ENGINEER_IMPLEMENTATION_GUIDE.md](guides/DATA_ENGINEER_IMPLEMENTATION_GUIDE.md)
4. Architecture: [ADR-0002](architecture/0002-data-architecture.md), [ADR-0009](architecture/0009-data-sourcing.md), [ADR-0010](architecture/0010-pff-data-source.md)
5. Data Sourcing: [ADR-0009](architecture/0009-data-sourcing.md)

### Frontend/DevTools Engineer
1. Start: [GETTING_STARTED.md](GETTING_STARTED.md)
2. Read: [AGENT_INSTRUCTIONS_FRONTEND.md](guides/AGENT_INSTRUCTIONS_FRONTEND.md)
3. Setup: [DOCKER_SETUP.md](guides/DOCKER_SETUP.md)
4. Current Sprint: Check [sprint-planning/SPRINT_PLANS.md](sprint-planning/SPRINT_PLANS.md) for active sprint

---

## 🚦 Project Status

**Timeline:** February 10 - April 20, 2026 (10 weeks)
**Total Sprints:** 5
**Team Size:** 3 engineers (backend, data, frontend)
**Status:** Sprint 1 & 2 complete, Sprint 3 in progress (Feb 13, 2026)

**Data Sources:**
- ✅ NFL.com (Combine data) - Sprint 1
- ✅ Yahoo Sports (College stats) - Sprint 3
- ✅ ESPN (Injury data) - Sprint 3
- 🔄 PFF.com (Industry grades) - Sprint 4 (pending)
- 📊 Multi-source analytics - Sprint 5

---

## 📚 Key Concepts

### Event-Driven ETL Pipeline
Daily refresh process (3 AM) that:
1. Scrapes multiple data sources
2. Validates and reconciles data
3. Tracks changes in audit trail
4. Updates materialized views for analytics
5. Alerts on data quality issues

**Details:** [ADR-0002](architecture/0002-data-architecture.md)

### Multi-Source Data Reconciliation
Handles conflicts when same prospect has different data from multiple sources:
- NFL.com: Official combine measurements
- Yahoo Sports: College production metrics
- ESPN: Injury history
- PFF.com: Industry-standard grades

**Approach:** Source-aware conflict resolution with audit trail

### API-First Architecture
- REST API for all data access
- Redis caching for performance
- Materialized views for analytics
- Jupyter notebooks for exploratory analysis

**Details:** [ADR-0003](architecture/0003-api-design.md), [ADR-0004](architecture/0004-caching-strategy.md)

---

## 🔗 Related Resources

### Code Organization
- **Backend:** `/backend/` - FastAPI application
- **Data Pipeline:** `/data_pipeline/` - ETL orchestration
- **CLI:** `/cli/` - Command-line tools
- **Notebooks:** `/notebooks/` - Jupyter analytics
- **Tests:** `/tests/` - Test suite
- **Scripts:** `/scripts/` - Operational scripts

### Configuration
- `pyproject.toml` - Python dependencies
- `.env` - Environment variables
- `docker-compose.yml` - Local development
- `docker-compose.prod.yml` - Production deployment

---

## ❓ Common Questions

**Q: Where do I find the current sprint tasks?**
A: [sprint-planning/SPRINT_PLANS.md](sprint-planning/SPRINT_PLANS.md) has all sprint details and current status.

**Q: How do I set up the local environment?**
A: Start with [GETTING_STARTED.md](GETTING_STARTED.md), then follow [DOCKER_SETUP.md](guides/DOCKER_SETUP.md).

**Q: What are the data sources?**
A: See [ADR-0009](architecture/0009-data-sourcing.md) for scraper details and [ADR-0010](architecture/0010-pff-data-source.md) for PFF integration.

**Q: How is authentication handled?**
A: See [ADR-0005](architecture/0005-authentication.md).

**Q: What's the monitoring strategy?**
A: See [ADR-0007](architecture/0007-monitoring.md).

---

**Last Updated:** February 13, 2026  
**Next Review:** After Sprint 3 completion
