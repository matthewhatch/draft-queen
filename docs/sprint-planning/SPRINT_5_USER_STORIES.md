# Sprint 5: Analytics & Launch Preparation - User Stories
**Duration:** Apr 7 - Apr 20 (2 weeks)
**Focus:** Analytics, predictive models, performance optimization, production launch

---

## US-043: Grade Conflict Resolution Dashboard

### User Story
As a **analyst**  
I want to **understand where PFF grades differ from other evaluations**  
So that **I can investigate discrepancies and understand different evaluation methodologies**

### Description
Create dashboard showing conflicts between PFF grades and other sources (ESPN, Yahoo consensus, NFL draft position).

### Acceptance Criteria
- [ ] Dashboard shows prospects with large grade discrepancies (> 10 points)
- [ ] Compares: PFF grade vs. ESPN grade vs. draft position vs. measurables
- [ ] Highlights outliers (prospects graded much higher/lower by PFF)
- [ ] Explains potential reasons for discrepancies
- [ ] Sortable by position, grade difference, name
- [ ] Historical comparison: PFF accuracy predicting draft position

### Technical Acceptance Criteria
- [ ] Calculate grade differences across sources
- [ ] Dashboard queries optimized
- [ ] HTML/JavaScript dashboard or Jupyter notebook
- [ ] Performance: loads in < 2 seconds

### Tasks
- **Backend:** Create grade comparison queries
- **Frontend:** Build dashboard interface

### Definition of Done
- [ ] Dashboard displaying grade conflicts
- [ ] Sortable and filterable
- [ ] Discrepancies clearly visible

### Effort
- **Backend:** 2 story points
- **Frontend:** 2 story points
- **Total:** 4 story points

---

## US-044: Enhanced Data Quality for Multi-Source Grades

### User Story
As a **data engineer**  
I want to **validate grade consistency across sources**  
So that **we detect potential data issues or source disagreements early**

### Description
Expand data quality checks to include cross-source grade validation and outlier detection for PFF grades.

### Acceptance Criteria
- [ ] Quality check: all prospects have at least one grade source
- [ ] Quality check: grades within valid range (0-100)
- [ ] Quality check: grade changes tracked daily (suspicious jumps flagged)
- [ ] Outlier detection: prospects with PFF grade > 2 std dev from position mean
- [ ] Quality dashboard shows grade completeness by source
- [ ] Alerts for suspicious grade patterns

### Technical Acceptance Criteria
- [ ] Query grade coverage by source
- [ ] Outlier detection algorithm
- [ ] Quality metrics table updated daily
- [ ] Alert thresholds configurable

### Tasks
- **Data:** Define grade quality rules
- **Backend:** Implement validation checks
- **Backend:** Build quality reporting

### Definition of Done
- [ ] Quality checks executing
- [ ] Grade coverage verified
- [ ] Outliers detected and logged

### Effort
- **Backend:** 3 story points
- **Data:** 1 story point
- **Total:** 4 story points

### ✅ SPECIFICATION (Clarified)

**Suspicious Grade Pattern Definition:**
- Grade change > 2 standard deviations from position group mean (outlier detection)
- Threshold is configurable per position via `quality_rules` table
- Default thresholds:
  - Position-specific: calculated from historical data
  - Example: If CBs avg grade is 75±5, any CB with grade >85 or <65 flagged

**Alert Escalation:**
- Dashboard: All alerts visible in quality dashboard
- Email: Send daily digest of critical alerts (> 3 std dev)
- Logging: All alerts logged to `quality_alerts` table with timestamp, prospect, rule, severity

**Implementation:**
See [SPRINT_5_REVIEW.md](../decisions/SPRINT_5_REVIEW.md) for detailed methodology.

---

## US-050: Position Trend Analysis Endpoint

### User Story
As a **analyst**  
I want to **analyze trends in measurables across positions year-over-year**  
So that **I can identify how player profiles are evolving**

### Description
Create API endpoint analyzing position trends: changes in average height, weight, 40-time across recent years.

### Acceptance Criteria
- [ ] Endpoint: `GET /api/analytics/trends/:position`
- [ ] Compares 3 most recent years
- [ ] Shows: average, trend (↑/↓/→), percent change
- [ ] Includes: height, weight, 40-time, vertical, broad jump
- [ ] Year-over-year comparison visualization data
- [ ] Trends for round tiers (1st round avg, 2nd round avg, etc.)
- [ ] Response time < 1 second

### Technical Acceptance Criteria
- [ ] SQL window functions for year-over-year calculation
- [ ] Materialized view for performance
- [ ] Redis caching (1-day TTL)
- [ ] JSON response with trend data

### Tasks
- **Backend:** Create trends endpoint
- **Backend:** Write SQL window functions
- **Data:** Verify data completeness for historical years

### Definition of Done
- [ ] Trends calculated correctly
- [ ] Performance meets target
- [ ] Historical data validated
- [ ] Tests passing

### Effort
- **Backend:** 4 story points
- **Data:** 2 story points
- **Total:** 6 story points

---

## US-051: Injury Risk Assessment

### User Story
As a **analyst**  
I want to **assess injury risk profiles for prospects**  
So that **I can factor injury history into evaluations**

### Description
Create endpoint aggregating injury data: injury frequency, history summaries, positional injury patterns.

### Acceptance Criteria
- [ ] Endpoint: `GET /api/analytics/injury-risk/:prospect_id`
- [ ] Shows: reported injuries, severity, position-specific patterns
- [ ] Risk percentile: where does this player fall vs position group
- [ ] Historical comparison: injury frequency by position
- [ ] Injury recurrence risk (if multiple injuries)
- [ ] Related prospects with similar injury history

### Technical Acceptance Criteria
- [ ] Injury data model expansion
- [ ] Calculation of injury risk percentiles
- [ ] Positional injury pattern database
- [ ] Related prospect queries

### Tasks
- **Data:** Analyze injury data, create patterns
- **Backend:** Create injury risk endpoint
- **Backend:** Implement percentile calculations

### Definition of Done
- [ ] Injury data modeled
- [ ] Risk assessments calculated
- [ ] Endpoint working
- [ ] Tests passing

### Effort
- **Backend:** 4 story points
- **Data:** 3 story points
- **Total:** 7 story points

### ✅ SPECIFICATION (From INJURY_RISK_METHODOLOGY.md)

**Risk Percentile Calculation:**
- Percentile rank vs position group (0-100, where 100 = most injured)
- Injury Burden Score formula:
  ```
  Score = (Base Injuries × 0.25) + (Severity Weighted × 0.35) + 
           (Recurrence Penalty × 0.20) + (Days Missed × 0.20)
  
  Where:
  - Base injuries: count × 10 points each
  - Severity: Severe=3, Moderate=2, Minor=1 (weighted × 10)
  - Recurrence: +20 per recurrence (same injury within 12 months)
  - Days missed: (total_days / 365) × 20, capped at 100
  ```

**Recurrence Definition:**
- Same injury type within 12 months
- Example: ACL in 2023 + ACL in 2024 = 1 recurrence
- Different injuries: not counted as recurrence

**Related Prospects:**
- Top 5 prospects with similar injury history
- Filter by: same position + similar injury profile
- Sort by: injury similarity score (highest match first)

**Data Availability:**
- Use available ESPN injury data from Sprint 3
- Document gaps in sample size per position
- Flag for data enrichment in future sprints

**Response Example:**
```json
{
  "prospect_id": "12345",
  "injury_history": [
    {"year": 2024, "injury": "ACL", "status": "recovered"},
    {"year": 2023, "injury": "ACL", "status": "recovered"}
  ],
  "position": "WR",
  "risk_percentile": 65,
  "risk_percentile_description": "65th percentile for WR (higher = more injuries)",
  "recurrence_risk": "high",
  "related_prospects": [
    {"id": "67890", "name": "Similar Player 1", "injuries": "ACL x2"},
    {"id": "67891", "name": "Similar Player 2", "injuries": "ACL x2"}
  ]
}
```

See [INJURY_RISK_METHODOLOGY.md](../decisions/INJURY_RISK_METHODOLOGY.md) for full methodology.

---

## US-052: Production Readiness Prediction

### User Story
As a **analyst**  
I want to **predict which prospects are ready for immediate NFL production**  
So that **I can identify immediate impact players vs. development prospects**

### Description
Implement scoring algorithm predicting production readiness based on measurables and college performance.

### Acceptance Criteria
- [ ] Endpoint: `GET /api/analytics/production-readiness/:prospect_id`
- [ ] Returns: 0-100 score, confidence level, key factors
- [ ] Factors: age, experience (college years), production metrics
- [ ] Breakout by position (edge, DB, QB different criteria)
- [ ] Comparison to peers (percentile)
- [ ] Historical accuracy: show accuracy for past years
- [ ] Explanations for top/bottom factors

### Technical Acceptance Criteria
- [ ] Score calculation based on weighted factors
- [ ] Position-specific scoring models
- [ ] Feature engineering from raw data
- [ ] Historical model validation

### Tasks
- **Backend:** Design scoring algorithm
- **Backend:** Create endpoint
- **Data:** Validate with historical data

### Definition of Done
- [ ] Scoring working
- [ ] Explanations clear
- [ ] Historical accuracy verified
- [ ] Endpoint tested

### Effort
- **Backend:** 3 story points
- **Data:** 3 story points
- **Total:** 6 story points

### ✅ SPECIFICATION (From PRODUCTION_READINESS_SCORING.md)

**Scoring Formula:**
```
Score = (Measurables × 0.40) + (College Production × 0.40) + (Age/Experience × 0.20) + Position Adjustment
```

**Score Range Interpretation:**
- **80-100:** Ready for immediate NFL impact
  - Excellent measurables for position
  - Strong college production
  - Likely Day 1-2 pick, high usage expected
- **60-79:** Ready with coaching/development
  - Good measurables, solid production
  - May need technique refinement or scheme fit
  - Day 2-3 picks, solid contributors
- **40-59:** Developmental prospect
  - Measurables OR production lags
  - Upside potential but needs NFL coaching
  - Day 3+ picks, need time to develop
- **Below 40:** Significant concerns for NFL readiness
  - Multiple factors below position norms
  - Major gaps in measurables or production

**Position-Specific Adjustments:**
- QB: Emphasis on completion %, TD:INT ratio, college level (P5 vs G5)
- RB: Yards per carry, yards per game, receiving role
- WR: Catch percentage, yards per game, consistency
- Edge: Sacks per game, pressures per game, consistency
- DB: Interceptions, pass breakups, yards allowed inverse

See [PRODUCTION_READINESS_SCORING.md](../decisions/PRODUCTION_READINESS_SCORING.md) for detailed formulas and position-specific metrics.

---

## US-053: Batch Analytics Report Generation

### User Story
As a **analyst**  
I want to **generate comprehensive analytics reports**  
So that **I can share analysis with stakeholders**

### Description
Create reports combining multiple analyses: position summaries, trend analysis, comparative rankings.

### Acceptance Criteria
- [ ] Report generation endpoint: `POST /api/reports/generate`
- [ ] Report types: position summary, prospect comparison, trend analysis
- [ ] Output formats: PDF, Excel, HTML
- [ ] Includes: tables, charts, executive summary
- [ ] Can customize: which positions, which metrics, date ranges
- [ ] Saved reports: retrieve historical reports
- [ ] Generation time < 30 seconds

### Technical Acceptance Criteria
- [ ] ReportLab or similar for PDF generation
- [ ] Excel generation with openpyxl
- [ ] HTML templates for reports
- [ ] Async report generation (queue for large reports)

### Tasks
- **Backend:** Create report generation endpoint
- **Backend:** Implement PDF generation
- **Backend:** Implement Excel generation
- **Frontend:** Create report customization UI (Jupyter)

### Definition of Done
- [ ] Reports generating correctly
- [ ] All formats working
- [ ] Customization functional
- [ ] Performance acceptable

### Effort
- **Backend:** 5 story points
- **Frontend:** 2 story points
- **Total:** 7 story points

---

## US-054: API Performance Optimization

### User Story
As a **system administrator**  
I want to **optimize API response times**  
So that **analysts have fast data access**

### Description
Profile, identify bottlenecks, and optimize API endpoints for production performance.

### Acceptance Criteria
- [ ] All endpoints: response time < 1 second (p95)
- [ ] Complex queries: < 2 seconds
- [ ] Analytics endpoints: < 500ms with caching
- [ ] Database queries optimized (EXPLAIN analysis)
- [ ] Proper indexing on all query columns
- [ ] Connection pooling configured
- [ ] Load testing: supports 10 concurrent users

### Technical Acceptance Criteria
- [ ] Query profiling and optimization
- [ ] Database index strategy
- [ ] Connection pool tuning
- [ ] Caching layer optimization
- [ ] Load testing script

### Tasks
- **Backend:** Profile queries
- **Backend:** Create missing indexes
- **Backend:** Optimize slow queries
- **Backend:** Load testing

### Definition of Done
- [ ] Performance targets met
- [ ] Load test passing
- [ ] Indexes documented
- [ ] Monitoring alerts set

### Effort
- **Backend:** 5 story points
- **Total:** 5 story points

---

## US-055: Monitoring and Alerting

### User Story
As a **system administrator**  
I want to **monitor system health and receive alerts**  
So that **issues are caught quickly**

### Description
Implement monitoring for API health, database performance, data quality, and error rates.

### Acceptance Criteria
- [ ] Dashboard showing: uptime, response times, error rates
- [ ] Database monitoring: query times, connection count
- [ ] Data quality monitoring: record counts, completeness
- [ ] Error tracking and alerting
- [ ] Alerts: email on critical issues
- [ ] Performance trends: identify degradation
- [ ] Health check endpoint: `GET /health`

### Technical Acceptance Criteria
- [ ] Prometheus for metrics collection
- [ ] Health check endpoint
- [ ] Email alerting configuration
- [ ] Logging aggregation
- [ ] Simple dashboard (HTML)

### Tasks
- **Backend:** Implement health monitoring
- **Backend:** Set up alerting
- **Backend:** Create dashboard

### Definition of Done
- [ ] Monitoring operational
- [ ] Alerts working
- [ ] Dashboard accessible
- [ ] Issues being tracked

### Effort
- **Backend:** 4 story points
- **Total:** 4 story points

---

## US-057: WhatsApp Notification Service

### User Story
As a **team member**  
I want to **receive WhatsApp notifications about pipeline execution, data quality issues, and admin alerts**  
So that **I can monitor system health and respond to critical issues in real-time**

### Description
Implement WhatsApp notification service for pipeline events, data quality alerts, and admin operations. Support configurable alert types, team member notification lists, and alert thresholds.

### Use Cases
1. **Pipeline Execution Status** - Success/failure notifications for daily pipeline runs
2. **Data Quality Alerts** - Notify when quality metrics fall below thresholds
3. **Admin Operations** - Alert when admin performs migrations, backups, pipeline triggers
4. **Analyst Notifications** - Notify when new data is ready for analysis
5. **Error Alerts** - Notify on critical API errors or system issues

### Acceptance Criteria
- [ ] WhatsApp integration via Twilio API
- [ ] Configurable notification types (can enable/disable each alert type)
- [ ] Team member phone number management
- [ ] Notification templates for each alert type
- [ ] Endpoint: `POST /admin/notifications/configure` (set notification preferences)
- [ ] Endpoint: `POST /admin/notifications/test` (send test message)
- [ ] Log all notifications sent (audit trail)
- [ ] Rate limiting on notifications (don't spam team)
- [ ] Error handling (failed sends logged, retried)

### Technical Acceptance Criteria
- [ ] Twilio account setup and API integration
- [ ] Phone number validation (E.164 format)
- [ ] Message templating system
- [ ] Notification queue (handle async sending)
- [ ] Notification logging to database
- [ ] Configuration stored in database
- [ ] Secure credential storage (Twilio API key)
- [ ] Max 2 notifications per person per alert type per hour (rate limit)

### Notification Types

**1. Pipeline Execution (US-057-1)**
```
✅ Pipeline execution completed successfully
Execution ID: exec_20260414_020000
Duration: 2m 34s
Prospects processed: 500
New records: 23
Updated: 45
```

**2. Data Quality Alert (US-057-2)**
```
⚠️ Data quality warning
Metric: Prospect completeness
Current: 87% (threshold: 95%)
Missing data: Height (12 records), Weight (5 records)
Action needed: Review and reconcile
```

**3. Admin Operation (US-057-3)**
```
🔧 Admin operation performed
Action: Database migration
User API Key: ***abc123
Status: Success
Timestamp: 2026-04-14 02:15 UTC
```

**4. Error Alert (US-057-4)**
```
❌ Critical error detected
Error: Pipeline execution failed
Component: PFF scraper
Message: Connection timeout
Timestamp: 2026-04-14 02:10 UTC
Action: Check logs and retry manually
```

**5. Data Ready Alert (US-057-5)**
```
📊 New data available
Type: Position trends analysis
Prospects: 500
Ready time: 2m 45s
Data from: NFL.com, PFF.com, ESPN
```

### Configuration

**Database Schema:**
```sql
CREATE TABLE notification_config (
    id SERIAL PRIMARY KEY,
    team_member_id VARCHAR(255),
    phone_number VARCHAR(20),  -- E.164 format: +1234567890
    alerts_enabled BOOLEAN DEFAULT true,
    
    -- Alert types (bitmask or individual booleans)
    alert_pipeline BOOLEAN DEFAULT true,
    alert_data_quality BOOLEAN DEFAULT true,
    alert_admin BOOLEAN DEFAULT true,
    alert_errors BOOLEAN DEFAULT true,
    alert_analyst BOOLEAN DEFAULT true,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE notification_log (
    id SERIAL PRIMARY KEY,
    team_member_id VARCHAR(255),
    phone_number VARCHAR(20),
    alert_type VARCHAR(50),
    message_text TEXT,
    status VARCHAR(50),  -- "sent", "failed", "queued"
    twilio_sid VARCHAR(255),
    error_message TEXT,
    sent_at TIMESTAMP DEFAULT NOW()
);
```

### Admin Configuration Endpoint

**Set notification preferences:**
```python
POST /admin/notifications/configure
Authorization: X-API-Key <ADMIN_API_KEY>
Content-Type: application/json

{
  "team_member_id": "john.doe",
  "phone_number": "+1234567890",
  "alerts_enabled": true,
  "alert_pipeline": true,
  "alert_data_quality": true,
  "alert_admin": true,
  "alert_errors": true,
  "alert_analyst": true
}

Response:
{
  "status": "configured",
  "team_member_id": "john.doe",
  "phone_number": "+1234567890",
  "alerts": {
    "pipeline": true,
    "data_quality": true,
    "admin": true,
    "errors": true,
    "analyst": true
  }
}
```

**Send test notification:**
```python
POST /admin/notifications/test
Authorization: X-API-Key <ADMIN_API_KEY>

{
  "phone_number": "+1234567890",
  "alert_type": "pipeline"  # or data_quality, admin, errors, analyst
}

Response:
{
  "status": "sent",
  "message": "Test WhatsApp notification sent successfully",
  "twilio_sid": "SM1234567890abcdef"
}
```

### Integration Points

1. **Pipeline Scheduler** - Send notification after pipeline completes
   ```python
   def _daily_load_job(self):
       result = load_nfl_com_data()
       notify_pipeline_execution(result)  # New
   ```

2. **Data Quality Checks** - Send alert if thresholds crossed
   ```python
   def run_quality_checks(self):
       result = check_data_completeness()
       if result['completeness'] < 95:
           notify_quality_alert(result)  # New
   ```

3. **Admin Operations** - Log and notify
   ```python
   @admin_router.post("/admin/db/migrate")
   async def run_migrations(admin_token: str = Depends(verify_admin_token)):
       result = subprocess.run(...)
       notify_admin_operation("db_migrate", result)  # New
   ```

### Tasks
- **Backend:** Set up Twilio account and API integration
- **Backend:** Create notification service module
- **Backend:** Build configuration endpoints
- **Backend:** Implement notification queue (async)
- **Backend:** Add notification logging
- **Backend:** Integrate with pipeline scheduler
- **Backend:** Integrate with quality checks
- **Backend:** Integrate with admin operations
- **Backend:** Write unit tests for notification service

### Definition of Done
- [ ] WhatsApp notifications sending successfully
- [ ] Configuration endpoints working
- [ ] Notifications logged to database
- [ ] Rate limiting working
- [ ] Admin can test notifications
- [ ] All alert types triggered correctly
- [ ] Error handling in place
- [ ] Tests passing
- [ ] Documentation complete

### Effort
- **Backend:** 8 story points
- **Total:** 8 story points

### Dependencies
- Twilio account with WhatsApp API enabled
- Team members provide phone numbers
- Admin configures notification preferences

### Future Enhancements
- Slack integration
- Email digest summaries
- SMS fallback
- Notification history dashboard
- Alert severity levels
- Snooze alerts temporarily

---

## US-056: Production Deployment and Launch

### User Story
As a **project lead**  
I want to **deploy the analytics platform to production**  
So that **the team can start using it for evaluations**

### Description
Final deployment: database migration, API deployment, Jupyter notebook setup, documentation.

### Acceptance Criteria
- [ ] Production database deployed and optimized
- [ ] API endpoints verified against checklist
- [ ] Jupyter notebooks available in production environment
- [ ] Documentation complete and accessible
- [ ] Team trained on platform usage
- [ ] Backup and recovery procedures documented
- [ ] Launch communication sent
- [ ] Initial user feedback collected

### Technical Acceptance Criteria
- [ ] Production database configured
- [ ] API deployed on production server
- [ ] SSL certificates installed
- [ ] Environment configuration locked
- [ ] Backup scripts tested
- [ ] Disaster recovery tested
- [ ] Monitoring active

### Tasks
- **Backend:** Production deployment
- **Backend:** Verify all endpoints
- **Frontend:** Finalize documentation
- **Data:** Database migration and optimization
- **Project:** User training

### Definition of Done
- [ ] Platform live and accessible
- [ ] All checks passed
- [ ] Team can access
- [ ] No critical issues

### Effort
- **Backend:** 3 story points
- **Data:** 2 story points
- **Frontend:** 1 story point
- **Total:** 6 story points

---

## Sprint 5 Summary

**Total Story Points:** ~54 points (46 analytics + 8 notifications)

**Key Outcomes:**
- ✅ Position trend analysis available
- ✅ Injury risk assessment functional
- ✅ Production readiness scoring active
- ✅ Batch reports generating
- ✅ API performance optimized
- ✅ WhatsApp notifications configured and operational
- ✅ Monitoring and alerting operational
- ✅ Platform launched to production
- ✅ Team trained and using platform

**Post-Sprint Activities:**
- Monitor system performance and notifications
- Gather user feedback
- Plan enhancements for 2.0 release (Slack, SMS, Email)
