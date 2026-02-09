# NFL Draft Analysis Platform - Sprint 1 Setup

**Status:** Sprint 1 - Data Infrastructure Foundation (Feb 10 - Feb 23, 2026)

## Overview

This is the data engineering implementation for the **NFL Draft Analysis Internal Data Platform**. This Sprint establishes the foundation with a robust database, data ingestion pipeline, and quality monitoring system.

### Sprint 1 Objectives

- **US-004:** Database Schema Design - ✓ Complete
- **US-005:** Data Ingestion from NFL.com - ✓ Foundation  
- **US-006:** Data Quality Monitoring - ✓ Framework
- Supporting: Query API, CSV Export, Python Scripts

## Project Structure

```
draft-queen/
├── backend/                    # Backend API and database
│   ├── database/
│   │   ├── __init__.py        # Database connection manager
│   │   └── models.py          # SQLAlchemy ORM models
│   └── api/                    # FastAPI endpoints (future)
│
├── data_pipeline/              # ETL pipeline components
│   ├── models/                 # Pydantic validation schemas
│   ├── sources/                # Data connectors (NFL.com, etc)
│   ├── validators/             # Data validation logic
│   ├── loaders/                # Database loaders
│   ├── quality/                # Quality checks & monitoring
│   └── scheduler/              # Job scheduling
│
├── migrations/                 # Alembic database migrations
│   ├── env.py
│   └── versions/               # Migration scripts
│
├── tests/                      # Test suite
│   ├── unit/                   # Unit tests
│   └── integration/            # Integration tests
│
├── logs/                       # Runtime logs
├── config.py                   # Configuration management
├── main.py                     # Application entry point
├── requirements.txt            # Python dependencies
├── .env.example                # Environment template
└── README.md                   # This file
```

## Quick Start

### 1. Prerequisites

- Python 3.9+
- PostgreSQL 12+
- Poetry or pip/virtualenv

### 2. Install Dependencies

**Option A: Using Poetry (Recommended)**

```bash
cd /home/parrot/code/draft-queen

# Install Poetry (if not already installed)
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies and create virtual environment
poetry install

# Activate the virtual environment
poetry shell
```

**Option B: Using pip and virtualenv**

```bash
cd /home/parrot/code/draft-queen

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install packages
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your database credentials
nano .env
```

**Required settings:**
```
DB_HOST=localhost
DB_PORT=5432
DB_USERNAME=postgres
DB_PASSWORD=your_password
DB_DATABASE=nfl_draft
```

### 4. Initialize Database

```bash
# Create database
createdb nfl_draft

# Run migrations to create tables
python -m alembic upgrade head

# Verify tables
psql -U postgres -d nfl_draft -c "\dt"
```

### 5. Run Tests

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run with coverage
pytest tests/unit/ --cov=data_pipeline --cov-report=html
```

### 6. Run Application

```bash
# As standalone (runs scheduler in background)
python main.py

# With logging output
python main.py --debug

# Stop: Ctrl+C
```

## Data Pipeline Architecture

### Daily Execution Flow (2:00 AM UTC)

```
1. INGESTION (2:00 AM)
   └─ Fetch from NFL.com API
      └─ Extract prospect data
      └─ Parse & normalize

2. VALIDATION (immediate)
   └─ Schema validation (Pydantic)
   └─ Business rule checks
   └─ Duplicate detection
   └─ Outlier detection
   └─ Load to staging table

3. LOADING (immediate)
   └─ Idempotent upsert
   └─ Transaction management
   └─ Production database insert
   └─ Audit trail recording

4. QUALITY CHECKS (2:30 AM)
   └─ Completeness analysis
   └─ Duplicate verification
   └─ Validation error report
   └─ Data freshness check
   └─ Generate metrics

5. REPORTING & ALERTS
   └─ HTML report generation
   └─ CSV metrics export
   └─ Email notification (if issues)
   └─ Dashboard update
```

## Database Schema

### Core Tables

**prospects** - Main prospect data
- id (UUID)
- name, position, college
- height, weight, measurables
- draft_grade, round_projection
- Constraints: unique on (name, position, college)
- Indexes: position, college, height, weight

**prospect_measurables** - Physical test results
- FK to prospects
- 40-time, vertical, broad jump, 3-cone, shuttle
- test_type, test_date

**prospect_stats** - College performance
- FK to prospects
- season, games_played, stats by position
- offensive/defensive metrics

**prospect_injuries** - Injury history
- FK to prospects
- injury_type, body_part, dates, status

**prospect_rankings** - Rankings from sources
- FK to prospects
- source, grade, tier, confidence

### Pipeline Tables

**staging_prospects** - Data validation staging
- Copy of prospect data
- validation_status, validation_errors
- load_id for tracking

**data_load_audit** - Load history
- load_date, data_source
- record counts (received, validated, inserted, updated, failed)
- duration, status, errors

**data_quality_metrics** - Quality tracking
- metric_date, metric_name
- metric_value, thresholds
- status (pass/warning/fail)

**data_quality_report** - Daily reports
- report_date
- summary metrics
- completeness %, duplicates, errors
- alerts triggered

## Key Components

### Configuration (config.py)

All settings managed through environment variables with defaults:

```python
from config import settings

# Access settings
db_url = settings.database.url
email_enabled = settings.email.enabled
load_hour = settings.scheduler.load_schedule_hour
```

### Database Connection (backend/database/__init__.py)

```python
from backend.database import db, get_db_session

# Use in functions
with db.session_scope() as session:
    result = session.query(Prospect).all()

# In FastAPI
@app.get("/api/prospects")
def get_prospects(session = Depends(get_db_session)):
    return session.query(Prospect).all()
```

### Validation Framework (data_pipeline/validators)

```python
from data_pipeline.validators import SchemaValidator, DuplicateDetector

# Validate single record
result = SchemaValidator.validate_prospect(data_dict)
if result.is_valid:
    # Load to database
else:
    logger.error(f"Validation errors: {result.errors}")

# Validate batch
total, valid, invalid, errors = SchemaValidator.validate_batch(data_list)

# Detect duplicates
dups = DuplicateDetector.detect_duplicates_in_batch(prospects)
```

### Data Ingestion (data_pipeline/sources)

```python
from data_pipeline.sources import NFLComConnector

connector = NFLComConnector()
prospects = connector.fetch_prospects()
measurables = connector.fetch_measurables()

# Check API health
if connector.health_check():
    # Proceed with fetch
```

### Scheduling (main.py)

```python
from main import initialize_app, scheduler

# Initialize application
initialize_app()

# Scheduler runs daily jobs
# - 2:00 AM: NFL.com data load
# - 2:30 AM: Quality checks
```

## Development Workflow

### Using Poetry (Recommended)

Poetry provides deterministic dependency management and virtual environment isolation:

```bash
# Activate Poetry virtual environment
poetry shell

# Add a new dependency
poetry add package_name

# Add a dev dependency
poetry add --group dev package_name

# Update all dependencies
poetry update

# Install project in editable mode
poetry install

# Run commands within Poetry environment
poetry run pytest tests/ -v
poetry run black data_pipeline/
poetry run mypy data_pipeline/
poetry run flake8 data_pipeline/
```

**Key Poetry files:**
- `pyproject.toml` - Project metadata, dependencies, tool configurations
- `poetry.lock` - Locked dependency versions (add to git)

### Adding a New Feature

1. **Create tests first** (TDD approach)
   ```bash
   # Create test file
   touch tests/unit/test_new_feature.py
   
   # Write tests
   # Then write code to pass tests
   ```

2. **Run tests locally**
   ```bash
   pytest tests/unit/test_new_feature.py -v
   ```

3. **Verify code quality**
   ```bash
   # Check types
   mypy data_pipeline/
   
   # Check style
   flake8 data_pipeline/
   
   # Format code
   black data_pipeline/
   
   # Sort imports
   isort data_pipeline/
   ```

4. **Test with full database**
   ```bash
   pytest tests/integration/ -v
   ```

### Database Changes

1. **Modify models.py**
   ```python
   # Add new column/table to backend/database/models.py
   ```

2. **Create migration**
   ```bash
   # Auto-generate migration from model changes
   alembic revision --autogenerate -m "Add new feature"
   
   # Review migration file
   # Make edits if needed
   
   # Apply migration
   alembic upgrade head
   ```

3. **Test migration**
   ```bash
   # Run migration
   alembic upgrade head
   
   # Test downgrade
   alembic downgrade -1
   
   # Run upgrade again
   alembic upgrade head
   ```

## Logging & Monitoring

### Log Files

All logs are written to `logs/pipeline.log` (rotated daily):

```bash
# View recent logs
tail -f logs/pipeline.log

# Search for errors
grep "ERROR" logs/pipeline.log

# Watch for a specific source
grep "NFL" logs/pipeline.log
```

### Log Format

Structured JSON format for easy parsing:

```json
{
  "timestamp": "2026-02-09 02:15:30,123",
  "level": "INFO",
  "logger": "data_pipeline.sources",
  "message": "Starting NFL.com prospect data fetch"
}
```

### Metrics Tracking

Quality metrics are stored in PostgreSQL:

```sql
-- Check recent metrics
SELECT metric_name, metric_value, status, created_at
FROM data_quality_metrics
WHERE metric_date = CURRENT_DATE
ORDER BY created_at DESC;

-- View load history
SELECT data_source, load_date, total_records_received, 
       records_inserted, records_updated, status
FROM data_load_audit
ORDER BY load_date DESC
LIMIT 10;
```

## Testing

### Unit Tests

Test individual components in isolation:

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run specific test file
pytest tests/unit/test_validators.py -v

# Run specific test
pytest tests/unit/test_validators.py::TestSchemaValidator::test_valid_prospect -v

# Run with coverage
pytest tests/unit/ --cov=data_pipeline --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Integration Tests

Test components working together with real database:

```bash
# Requires test database setup
pytest tests/integration/ -v

# With verbose output
pytest tests/integration/ -vv
```

### Test Data

Mock data is provided in test fixtures:

```python
# In tests/conftest.py (create if needed)
import pytest

@pytest.fixture
def sample_prospect():
    return {
        "name": "Test Player",
        "position": "QB",
        "college": "Alabama",
    }
```

## Troubleshooting

### Database Connection Error

```
Error: could not connect to server: Connection refused
```

**Solution:**
```bash
# Check PostgreSQL is running
psql -U postgres -c "SELECT 1"

# Check database exists
psql -U postgres -l | grep nfl_draft

# Check connection string in .env
cat .env | grep DB_
```

### Migration Errors

```
Error: Can't find migration head
```

**Solution:**
```bash
# Check migration status
alembic current
alembic history

# Initialize if needed
alembic init migrations

# Verify versions folder exists
ls -la migrations/versions/
```

### Data Validation Failures

```
Validation errors: name: required field
```

**Solution:**
```python
# Check schema definition
from data_pipeline.models import ProspectDataSchema

# Debug validation
import json
data = json.loads(raw_data)
try:
    prospect = ProspectDataSchema(**data)
except ValidationError as e:
    print(e.json())
```

## Performance Tuning

### Database Queries

```bash
# Check slow queries
psql -U postgres -d nfl_draft -c "
  SELECT query, calls, mean_time
  FROM pg_stat_statements
  ORDER BY mean_time DESC
  LIMIT 10
"

# Analyze table
ANALYZE prospects;
ANALYZE prospect_measurables;

# Explain plan
EXPLAIN ANALYZE
SELECT * FROM prospects WHERE position = 'QB' AND college = 'Alabama';
```

### Connection Pooling

Configured in `config.py`:

```python
class DatabaseSettings:
    pool_size: int = 20          # Increase for high concurrency
    max_overflow: int = 40       # Additional connections
    pool_pre_ping: bool = True   # Verify connections alive
```

## Deployment

### Development

```bash
# Run with debug mode
export ENVIRONMENT=development
export DEBUG=true
python main.py
```

### Staging

```bash
# Connect to staging database
export DB_HOST=staging-db.internal
export DB_DATABASE=nfl_draft_staging
python main.py
```

### Production

```bash
# Use production credentials from secrets
export ENVIRONMENT=production
export DEBUG=false
# Run as daemon/service
systemctl start nfl-draft-pipeline
```

## Next Steps

### Sprint 1 Remaining

- [ ] Implement NFL.com connector (real API calls)
- [ ] Complete data loaders
- [ ] Implement quality checks
- [ ] Create FastAPI endpoints
- [ ] Load initial 2,000+ prospects
- [ ] Verify data quality > 99%

### Sprint 2

- [ ] Advanced filtering API
- [ ] Batch processing
- [ ] Analytics calculations
- [ ] Historical tracking

### Sprint 3

- [ ] Predictive models
- [ ] Dashboard visualization
- [ ] Team collaboration

## Resources

- **Database Schema:** [docs/DATABASE_SCHEMA_SPRINT1.md](docs/DATABASE_SCHEMA_SPRINT1.md)
- **Implementation Guide:** [docs/DATA_ENGINEER_IMPLEMENTATION_GUIDE.md](docs/DATA_ENGINEER_IMPLEMENTATION_GUIDE.md)
- **Architecture Review:** [docs/DATA_ENGINEER_SPRINT1_REVIEW.md](docs/DATA_ENGINEER_SPRINT1_REVIEW.md)
- **User Stories:** [sprint-planning/SPRINT_1_USER_STORIES.md](sprint-planning/SPRINT_1_USER_STORIES.md)

## Support

- **Issues/Questions:** Create GitHub issue with `[SPRINT1]` label
- **Documentation:** See [docs/](docs/) directory
- **Tests:** Check [tests/](tests/) for examples
- **Logging:** Review logs in [logs/pipeline.log](logs/pipeline.log)

---

**Sprint 1 Foundation Setup - COMPLETE ✅**

*Generated: February 9, 2026*  
*Next: Begin development on US-005 data ingestion*
