# Data Engineer Sprint 1 - Database Schema Design

## Prospect Database Schema

This schema supports US-004 (Database Schema Design) and the data pipeline requirements for US-005 and US-006.

### Core Tables

#### 1. prospects (Main Table)
```sql
CREATE TABLE prospects (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Basic Information
    name VARCHAR(255) NOT NULL,
    position VARCHAR(10) NOT NULL,  -- QB, RB, WR, TE, OL, DL, LB, DB, etc
    college VARCHAR(255) NOT NULL,
    
    -- Physical Attributes
    height DECIMAL(4, 2),  -- feet (e.g., 6.02)
    weight INT,             -- lbs
    arm_length DECIMAL(4, 2),
    hand_size DECIMAL(4, 2),
    
    -- Draft Information
    draft_grade DECIMAL(3, 1),  -- 5.0 to 10.0
    round_projection INT,       -- Projected round (1-7)
    grade_source VARCHAR(100),  -- Source of grade (team, analyst, consensus)
    
    -- Status Tracking
    status VARCHAR(50) DEFAULT 'active',  -- active, retired, injured, etc
    
    -- Audit Columns
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100) DEFAULT 'system',
    updated_by VARCHAR(100) DEFAULT 'system',
    data_source VARCHAR(100) DEFAULT 'nfl.com',  -- Where data came from
    
    -- Constraints
    CONSTRAINT valid_position CHECK (position IN 
        ('QB', 'RB', 'FB', 'WR', 'TE', 'OL', 'DL', 'EDGE', 'LB', 'DB', 'K', 'P')),
    CONSTRAINT valid_height CHECK (height BETWEEN 5.5 AND 7.0),
    CONSTRAINT valid_weight CHECK (weight BETWEEN 150 AND 350),
    CONSTRAINT valid_draft_grade CHECK (draft_grade BETWEEN 5.0 AND 10.0)
);

-- Indexes for performance
CREATE INDEX idx_prospects_position ON prospects(position);
CREATE INDEX idx_prospects_college ON prospects(college);
CREATE INDEX idx_prospects_height ON prospects(height);
CREATE INDEX idx_prospects_weight ON prospects(weight);
CREATE INDEX idx_prospects_status ON prospects(status);
CREATE INDEX idx_prospects_created_at ON prospects(created_at);
CREATE UNIQUE INDEX idx_prospects_unique ON prospects(LOWER(name), position, LOWER(college));
```

#### 2. prospect_measurables (Physical Test Results)
```sql
CREATE TABLE prospect_measurables (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prospect_id UUID NOT NULL REFERENCES prospects(id) ON DELETE CASCADE,
    
    -- 40-Yard Dash
    forty_time DECIMAL(4, 3),  -- seconds (e.g., 4.567)
    
    -- Bench Press
    bench_press_reps INT,
    
    -- Vertical Jump
    vertical_jump DECIMAL(4, 2),  -- inches
    
    -- Broad Jump
    broad_jump DECIMAL(5, 2),  -- inches
    
    -- 3-Cone Drill
    three_cone DECIMAL(4, 3),  -- seconds
    
    -- 20-Yard Shuttle
    shuttle DECIMAL(4, 3),  -- seconds
    
    -- Test Event Type
    test_type VARCHAR(50),  -- 'combine', 'pro_day', 'other'
    test_date DATE,
    
    -- Audit Columns
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT valid_forty CHECK (forty_time IS NULL OR forty_time BETWEEN 4.0 AND 5.5),
    CONSTRAINT valid_vertical CHECK (vertical_jump IS NULL OR vertical_jump BETWEEN 15 AND 55),
    CONSTRAINT valid_broad CHECK (broad_jump IS NULL OR broad_jump BETWEEN 80 AND 150)
);

CREATE INDEX idx_measurables_prospect_id ON prospect_measurables(prospect_id);
CREATE INDEX idx_measurables_test_date ON prospect_measurables(test_date);
```

#### 3. prospect_stats (College Performance)
```sql
CREATE TABLE prospect_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prospect_id UUID NOT NULL REFERENCES prospects(id) ON DELETE CASCADE,
    
    -- Season Information
    season INT NOT NULL,  -- e.g., 2023
    college VARCHAR(255),
    
    -- Games
    games_played INT,
    games_started INT,
    
    -- Offensive Stats (for applicable positions)
    passing_yards INT,
    passing_touchdowns INT,
    interceptions INT,
    rushing_yards INT,
    rushing_touchdowns INT,
    receptions INT,
    receiving_yards INT,
    receiving_touchdowns INT,
    
    -- Defensive Stats (for applicable positions)
    tackles INT,
    sacks DECIMAL(5, 2),
    forced_fumbles INT,
    interceptions_def INT,
    pass_breakups INT,
    
    -- Audit Columns
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_stats_prospect_id ON prospect_stats(prospect_id);
CREATE INDEX idx_stats_season ON prospect_stats(season);
```

#### 4. prospect_injuries (Medical History)
```sql
CREATE TABLE prospect_injuries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prospect_id UUID NOT NULL REFERENCES prospects(id) ON DELETE CASCADE,
    
    -- Injury Details
    injury_type VARCHAR(100),  -- ACL, MCL, Concussion, Fracture, etc
    injured_body_part VARCHAR(100),  -- Knee, Shoulder, Head, etc
    injury_date DATE,
    
    -- Status
    recovery_status VARCHAR(50),  -- 'healed', 'recovering', 'chronic', 'unknown'
    recovery_time_days INT,
    
    -- Additional Info
    notes TEXT,
    source VARCHAR(100),  -- Where info came from
    
    -- Audit Columns
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_injuries_prospect_id ON prospect_injuries(prospect_id);
CREATE INDEX idx_injuries_injury_type ON prospect_injuries(injury_type);
```

#### 5. prospect_rankings (Grades from Multiple Sources)
```sql
CREATE TABLE prospect_rankings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prospect_id UUID NOT NULL REFERENCES prospects(id) ON DELETE CASCADE,
    
    -- Source Information
    source VARCHAR(100),  -- 'nfl_dot_com', 'espn', 'analyst_name', 'consensus', etc
    grader_name VARCHAR(255),  -- Optional: specific analyst
    
    -- Grade
    grade DECIMAL(3, 1),  -- 5.0 to 10.0
    tier VARCHAR(50),  -- '1st round', '2nd round', '3rd round', etc
    
    -- Positioning
    position_rank INT,  -- Rank within position group
    overall_rank INT,   -- Overall prospect rank
    
    -- Ranking Date
    ranking_date DATE,
    
    -- Confidence Level
    confidence_level VARCHAR(50),  -- 'high', 'medium', 'low'
    
    -- Audit Columns
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_rankings_prospect_id ON prospect_rankings(prospect_id);
CREATE INDEX idx_rankings_source ON prospect_rankings(source);
CREATE INDEX idx_rankings_date ON prospect_rankings(ranking_date);
```

---

### Data Pipeline Support Tables

#### 6. staging_prospects (For US-005 - Data Validation)
```sql
CREATE TABLE staging_prospects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Identical structure to prospects table
    name VARCHAR(255),
    position VARCHAR(10),
    college VARCHAR(255),
    height DECIMAL(4, 2),
    weight INT,
    draft_grade DECIMAL(3, 1),
    round_projection INT,
    
    -- Validation Status
    validation_status VARCHAR(50),  -- 'pending', 'validated', 'failed'
    validation_errors JSONB,  -- List of validation errors
    
    -- Load Information
    load_id UUID,  -- References data_load_audit.id
    source_row_id VARCHAR(255),  -- ID from source system
    
    -- Audit Columns
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_source VARCHAR(100)
);

CREATE INDEX idx_staging_validation_status ON staging_prospects(validation_status);
CREATE INDEX idx_staging_load_id ON staging_prospects(load_id);
```

#### 7. data_load_audit (For Auditing - US-005)
```sql
CREATE TABLE data_load_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Load Information
    load_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_source VARCHAR(100),  -- 'nfl.com', 'espn', 'combine', etc
    
    -- Counts
    total_records_received INT,
    records_validated INT,
    records_inserted INT,
    records_updated INT,
    records_skipped INT,
    records_failed INT,
    
    -- Performance
    duration_seconds DECIMAL(6, 2),
    
    -- Status
    status VARCHAR(50),  -- 'success', 'partial', 'failed'
    error_summary TEXT,  -- Summary of errors
    error_details JSONB,  -- Detailed error log
    
    -- Operator
    operator VARCHAR(100) DEFAULT 'scheduler',
    
    -- Audit Columns
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_load_audit_date ON data_load_audit(load_date);
CREATE INDEX idx_load_audit_source ON data_load_audit(data_source);
CREATE INDEX idx_load_audit_status ON data_load_audit(status);
```

#### 8. data_quality_metrics (For US-006 - Quality Monitoring)
```sql
CREATE TABLE data_quality_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Metric Information
    metric_date DATE NOT NULL,
    metric_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metric_name VARCHAR(100),  -- 'completeness', 'duplicates', 'outliers', etc
    
    -- Measurements
    total_records INT,
    metric_value DECIMAL(10, 4),
    threshold_lower DECIMAL(10, 4),
    threshold_upper DECIMAL(10, 4),
    
    -- Status
    status VARCHAR(50),  -- 'pass', 'warning', 'fail'
    
    -- Details
    details JSONB,  -- Additional context specific to metric type
    
    -- Audit Columns
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_quality_metrics_date ON data_quality_metrics(metric_date);
CREATE INDEX idx_quality_metrics_name ON data_quality_metrics(metric_name);
CREATE INDEX idx_quality_metrics_status ON data_quality_metrics(status);
```

#### 9. data_quality_report (For US-006 - Quality Reports)
```sql
CREATE TABLE data_quality_report (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Report Information
    report_date DATE NOT NULL,
    report_generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Summary Metrics
    total_prospects INT,
    new_prospects_today INT,
    updated_prospects_today INT,
    
    -- Completeness
    completeness_pct DECIMAL(5, 2),
    missing_required_fields_count INT,
    
    -- Data Quality Issues
    duplicate_records INT,
    outlier_records INT,
    validation_errors INT,
    
    -- Measurables Status
    records_with_measurables INT,
    records_with_stats INT,
    records_with_rankings INT,
    
    -- Data Freshness
    oldest_record_days_ago INT,
    newest_record_today_count INT,
    
    -- Issues to Alert On
    has_alerts BOOLEAN,
    alert_summary TEXT,
    alert_details JSONB,
    
    -- Audit Columns
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_quality_report_date ON data_quality_report(report_date);
```

---

### Views for Common Queries

#### View 1: Prospect Summary (US-001)
```sql
CREATE VIEW v_prospect_summary AS
SELECT 
    p.id,
    p.name,
    p.position,
    p.college,
    p.height,
    p.weight,
    p.draft_grade,
    p.round_projection,
    m.forty_time,
    m.vertical_jump,
    m.broad_jump,
    COUNT(DISTINCT s.id) as stat_years,
    MAX(s.season) as latest_season,
    COUNT(DISTINCT i.id) as injury_count
FROM prospects p
LEFT JOIN prospect_measurables m ON p.id = m.prospect_id AND m.test_type = 'combine'
LEFT JOIN prospect_stats s ON p.id = s.prospect_id
LEFT JOIN prospect_injuries i ON p.id = i.prospect_id
WHERE p.status = 'active'
GROUP BY p.id, m.id;
```

#### View 2: Position Group Stats (US-002)
```sql
CREATE VIEW v_position_benchmarks AS
SELECT 
    position,
    COUNT(*) as prospect_count,
    ROUND(AVG(height)::numeric, 2) as avg_height,
    ROUND(AVG(weight)::numeric, 2) as avg_weight,
    ROUND(AVG(draft_grade)::numeric, 2) as avg_grade,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY height) as median_height,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY weight) as median_weight,
    MIN(height) as min_height,
    MAX(height) as max_height,
    MIN(weight) as min_weight,
    MAX(weight) as max_weight
FROM prospects
WHERE status = 'active'
GROUP BY position
ORDER BY position;
```

---

### Materialized Views for Performance

#### Materialized View: Recent Load Status
```sql
CREATE MATERIALIZED VIEW mv_recent_load_status AS
SELECT 
    data_source,
    MAX(load_date) as last_load_time,
    (CURRENT_TIMESTAMP - MAX(load_date)) as time_since_load,
    SUM(records_inserted) as total_inserted_today,
    SUM(records_updated) as total_updated_today,
    CASE 
        WHEN MAX(load_date) > CURRENT_TIMESTAMP - interval '24 hours' THEN 'Fresh'
        WHEN MAX(load_date) > CURRENT_TIMESTAMP - interval '48 hours' THEN 'Stale'
        ELSE 'Very Stale'
    END as data_freshness,
    COUNT(*) as load_count
FROM data_load_audit
WHERE load_date > CURRENT_TIMESTAMP - interval '7 days'
GROUP BY data_source;

-- Refresh after each load
-- REFRESH MATERIALIZED VIEW mv_recent_load_status;
```

---

## Key Performance Considerations

### Indexes Strategy
- **Hot columns:** position, college, height, weight (most frequently filtered)
- **Temporal:** created_at, updated_at, ranking_date (for time-based queries)
- **Foreign keys:** prospect_id (for joins)
- **Unique:** name + position + college (for duplicate detection)

### Query Optimization
1. Always use indexes on WHERE clauses
2. Use EXPLAIN ANALYZE to verify query plans
3. Limit result sets with LIMIT/OFFSET
4. Use materialized views for complex aggregations

### Maintenance
- Vacuum and analyze tables weekly: `VACUUM ANALYZE prospects;`
- Monitor index bloat and rebuild if necessary
- Archive old data (> 5 years) to separate table
- Monitor table sizes: `SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) FROM pg_tables;`

---

## Data Retention & Archival

```sql
-- Archive old data (> 5 years) to separate schema
CREATE SCHEMA archive;

-- Create archive tables
CREATE TABLE archive.prospects AS SELECT * FROM prospects WHERE created_at < CURRENT_DATE - interval '5 years';

-- Delete from main table
DELETE FROM prospects WHERE created_at < CURRENT_DATE - interval '5 years';

-- Update indexes
VACUUM ANALYZE prospects;
```

---

## Migration Strategy (for Database Versioning)

Use Flyway or Alembic for migrations:

```
migrations/
├── V001__Create_prospects_table.sql
├── V002__Create_measurables_table.sql
├── V003__Create_stats_table.sql
├── V004__Create_staging_tables.sql
├── V005__Create_quality_metrics_tables.sql
└── README.md
```

---

**This schema supports high-volume data ingestion, efficient querying, and comprehensive quality monitoring for Sprint 1 and beyond!**
