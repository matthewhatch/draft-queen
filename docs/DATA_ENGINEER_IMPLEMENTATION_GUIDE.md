# Data Engineer Sprint 1 - Implementation Quick Reference

## Quick Links to User Stories
- **US-005:** Data Ingestion from NFL.com (9 SP)
- **US-006:** Data Quality Monitoring (4 SP)

---

## Critical Data Engineering Tasks - Prioritized

### Week 1: Foundation & Setup

#### Task 1.1: Database Schema (Collaborate with Backend)
- [ ] Prospects table (id, name, position, college, height, weight, age, etc.)
- [ ] Measurables columns (40-time, vertical, broad jump, 3-cone, shuttle)
- [ ] Draft grade and round projection fields
- [ ] Created_at, updated_at, created_by audit columns
- [ ] Indexes on: position, college, height, weight, 40time

#### Task 1.2: Staging Tables (for US-005)
- [ ] staging_prospects table (identical schema to prospects)
- [ ] staging_load_audit table (load_id, record_count, inserted, updated, skipped, errors, status, timestamp)
- [ ] Validation status column to track validation results

#### Task 1.3: Quality Metrics Tables (for US-006)
- [ ] quality_metrics table (metric_date, metric_name, value, threshold, status, details)
- [ ] quality_report table (report_date, total_prospects, null_count_by_field, duplicates_found, errors)
- [ ] Index on metric_date and metric_name for historical queries

### Week 1-2: Validation Framework

#### Task 2.1: Pydantic Schema Validation (US-005)
```python
class ProspectData(BaseModel):
    name: str  # required, non-empty
    position: str  # required, must be in valid positions
    college: str  # required, non-empty
    height: float  # required, 5.5-7.0 feet
    weight: int  # required, 150-350 lbs
    forty_time: float  # optional, 4.3-5.5 seconds
    vertical: float  # optional, 20-50 inches
    # ... etc
```

#### Task 2.2: Validation Rules Engine
- [ ] Required field checks
- [ ] Data type validation
- [ ] Range validation (height, weight, times)
- [ ] Enum validation (positions)
- [ ] Duplicate detection (name + position + college)
- [ ] Outlier detection (impossible measurements)

#### Task 2.3: Error Handling & Logging
- [ ] Structured logging (json format with timestamp, level, message)
- [ ] Rotation handlers (daily, 7-day retention)
- [ ] Error details with full stack traces
- [ ] Load metrics tracking (counts, timing, errors)

### Week 2: ETL Pipeline Implementation

#### Task 3.1: NFL.com Connector (US-005)
- [ ] Analyze NFL.com endpoint structure
- [ ] Build HTTP client with:
  - Connection pooling
  - Rate limiting (respectful)
  - User-agent headers
  - Timeout handling
- [ ] Extraction logic for all prospect fields
- [ ] Error handling with exponential backoff (max 3 retries)
- [ ] Response parsing and normalization

#### Task 3.2: Idempotent Load Logic (US-005)
- [ ] Upsert implementation (insert new, update existing)
- [ ] Unique key: name + position + college
- [ ] Update strategy: only update if newer data
- [ ] Batch insert (not row-by-row) for performance
- [ ] Transaction management: all-or-nothing

#### Task 3.3: Staging & Validation Pipeline (US-005)
1. Extract from NFL.com → staging_prospects table
2. Validate data against Pydantic schema
3. Duplicate detection
4. Outlier detection
5. If all pass → merge into production prospects table
6. If failures → log errors, send alert, skip
7. Record audit trail in staging_load_audit

### Week 2-3: Quality Monitoring

#### Task 4.1: Data Quality Checks (US-006)
- [ ] Completeness check (% non-null per column)
  ```sql
  SELECT column_name, 
         COUNT(*) as total,
         COUNT(column_value) as non_null,
         ROUND(100.0 * COUNT(column_value) / COUNT(*), 2) as pct_complete
  FROM prospects
  GROUP BY column_name
  ```

- [ ] Duplicate detection
  ```sql
  SELECT name, position, college, COUNT(*) as count
  FROM prospects
  GROUP BY name, position, college
  HAVING COUNT(*) > 1
  ```

- [ ] Validation errors (out-of-range measurables)
  ```sql
  SELECT * FROM prospects
  WHERE height < 5.5 OR height > 7.0
     OR weight < 150 OR weight > 350
     OR forty_time < 4.3 OR forty_time > 5.5
  ```

- [ ] Outlier detection (statistical)
  - Z-score for measurables (> 3 SD from mean)

#### Task 4.2: Report Generation (US-006)
- [ ] HTML report with:
  - Summary metrics (total prospects, completeness %)
  - Duplicate count
  - Error count
  - Outlier chart
  - Trend visualization (historical quality)
  - Alert summary (issues found)
  
- [ ] CSV export of quality metrics

#### Task 4.3: Alerting (US-006)
- [ ] Email setup (AWS SES or SMTP)
- [ ] Alert conditions:
  - Completeness < 98%
  - Duplicates detected > 5
  - Any load errors
  - Data freshness > 24 hours
- [ ] Alert recipients: data analyst + team lead
- [ ] Alert frequency: daily summary or immediate for critical

### Week 3: Scheduling & Testing

#### Task 5.1: Automated Scheduling (US-005 & US-006)
- [ ] APScheduler setup
- [ ] Schedule 1: Daily NFL.com load at 2 AM UTC
- [ ] Schedule 2: Daily quality checks at 2:30 AM UTC
- [ ] Schedule 3: Weekly quality summary report
- [ ] Error notifications on schedule failures

#### Task 5.2: Testing (US-005 & US-006)
- [ ] Unit tests for validation logic
  - Valid data passes
  - Invalid data caught with clear errors
  - Duplicates detected correctly
  - Outliers identified
  
- [ ] Integration tests with test database
  - Full load cycle
  - Data integrity
  - Transaction rollback on errors
  - Idempotency (run twice, same result)
  
- [ ] Performance tests
  - Load time < 5 minutes
  - Quality checks < 2 minutes
  - Query performance < 500ms

#### Task 5.3: Documentation (US-005 & US-006)
- [ ] Data dictionary (all columns, definitions)
- [ ] ETL process documentation
- [ ] Validation rules documentation
- [ ] Quality metrics definitions
- [ ] Troubleshooting guide (common issues)
- [ ] Operator playbook (how to rerun, fix errors)

---

## Key Files to Create

```
data_pipeline/
├── models/
│   ├── __init__.py
│   └── prospect.py          # Pydantic schema
├── sources/
│   ├── __init__.py
│   └── nfl_com.py          # NFL.com connector
├── validators/
│   ├── __init__.py
│   ├── schema_validator.py # Pydantic validation
│   ├── business_rules.py   # Range, duplicate, outlier checks
│   └── error_handler.py    # Error logging
├── loaders/
│   ├── __init__.py
│   ├── staging_loader.py   # Load to staging table
│   └── production_loader.py # Merge to production
├── quality/
│   ├── __init__.py
│   ├── quality_checks.py   # Completeness, duplicates, etc
│   ├── report_generator.py # HTML/CSV reports
│   └── alerting.py         # Email notifications
├── scheduler/
│   ├── __init__.py
│   └── jobs.py             # APScheduler tasks
├── database/
│   ├── __init__.py
│   ├── models.py           # SQLAlchemy ORM models
│   └── migrations/         # Database migrations
├── tests/
│   ├── __init__.py
│   ├── test_validators.py
│   ├── test_loader.py
│   └── test_quality.py
├── logs/
│   └── pipeline.log        # Runtime logs
├── config.py              # Configuration (DB, email, etc)
├── main.py                # Entry point
└── requirements.txt       # Python dependencies
```

---

## Python Dependencies

```txt
# requirements.txt
fastapi==0.104.0          # API framework
sqlalchemy==2.0.0         # ORM
psycopg2-binary==2.9.9    # PostgreSQL driver
pydantic==2.4.0           # Schema validation
requests==2.31.0          # HTTP client
httpx==0.25.0             # Alternative HTTP client
apscheduler==3.10.4       # Task scheduling
python-dotenv==1.0.0      # Environment variables
python-logging-loki==0.3.2  # Optional: centralized logging
```

---

## Performance Targets

| Task | Target | Acceptance |
|------|--------|-----------|
| NFL.com load | < 5 minutes | 100% of records |
| Quality checks | < 2 minutes | Daily execution |
| Database query | < 500ms | For 2,000+ records |
| Data freshness | < 24 hours | During season |
| Data completeness | ≥ 99% | Key fields only |
| Duplicate rate | < 1% | Of all records |

---

## Common Pitfalls to Avoid

❌ **Mistake 1:** Row-by-row inserts instead of batch → **Use bulk_insert_mappings()**  
❌ **Mistake 2:** No idempotency → Same data loaded twice → **Use upsert logic**  
❌ **Mistake 3:** No validation before production load → Bad data in database → **Use staging table**  
❌ **Mistake 4:** Logging to stdout only → Can't debug issues later → **Use rotating file handlers**  
❌ **Mistake 5:** Hardcoded thresholds → Can't adjust alerting → **Use config file**  
❌ **Mistake 6:** No transaction management → Partial loads on error → **Use database transactions**  
❌ **Mistake 7:** Slow quality queries → Analysts wait for reports → **Use proper indexes**  

---

## Sprint Success Checklist

- [ ] Database schema created with all prospect fields
- [ ] Staging tables created and tested
- [ ] Pydantic validation schema built
- [ ] NFL.com connector working and tested
- [ ] Duplicate detection logic implemented
- [ ] Idempotent upsert logic working
- [ ] Full audit trail recording all changes
- [ ] Transaction management prevents partial loads
- [ ] Quality checks implemented and automated
- [ ] Alert system sending emails correctly
- [ ] Scheduling runs daily without manual intervention
- [ ] Unit tests passing (90%+ coverage)
- [ ] Integration tests passing
- [ ] Performance tests meet targets
- [ ] Documentation complete
- [ ] Initial data load successful (2,000+ prospects)
- [ ] Quality metrics show > 99% completeness
- [ ] Team trained on monitoring and operations

---

## Resources & References

- **Pydantic:** https://docs.pydantic.dev/
- **SQLAlchemy:** https://docs.sqlalchemy.org/
- **APScheduler:** https://apscheduler.readthedocs.io/
- **PostgreSQL Best Practices:** https://wiki.postgresql.org/wiki/Performance_Optimization
- **Data Quality Metrics:** https://en.wikipedia.org/wiki/Data_quality

---

**Ready to build! Let's establish the best data pipeline foundation.** 🚀
