# Phase 5 End-to-End Testing Guide

## Overview

This guide covers manual and automated end-to-end testing for US-044 Phase 5 (API Integration & Dashboard). These tests validate the complete workflow from alert generation through dashboard display and email delivery.

---

## 1. Manual E2E Testing

### 1.1 Alert Lifecycle Test

**Objective**: Verify alert flows from generation through acknowledgment and email.

**Steps**:

1. **Generate Test Alert**
   ```bash
   # Start Flask/FastAPI development server
   python main.py
   
   # In separate terminal, trigger alert manually
   python scripts/test_alert_generation.py
   # Or: POST http://localhost:8000/api/test/generate-alert
   ```

2. **Verify Database**
   ```bash
   # Check alert created in database
   psql -d nfl_draft -c "SELECT * FROM quality_alerts ORDER BY created_at DESC LIMIT 1;"
   ```
   - Alert should have status = 'pending'
   - Timestamp should be recent
   - All metadata present (position, source, etc.)

3. **Verify API Endpoint**
   ```bash
   # Check alert visible via API
   curl http://localhost:8000/api/quality/alerts
   ```
   - JSON response should include alert
   - Summary counts should include alert
   - Unacknowledged count should be > 0

4. **Check Dashboard**
   - Navigate to http://localhost:3000/quality
   - Alert should appear in AlertList
   - Summary statistics should update
   - Severity color coding correct

5. **Acknowledge Alert**
   - Click "Acknowledge" button on alert card
   - Dashboard should update immediately
   - Unacknowledged count should decrease

6. **Verify Acknowledgment Persisted**
   ```bash
   # Refresh page and verify acknowledged status
   curl http://localhost:8000/api/quality/alerts/acknowledged=true
   
   # Check database
   psql -d nfl_draft -c "SELECT * FROM quality_alerts WHERE id = '<alert_id>';"
   # Should show: acknowledged_by = 'user', acknowledged_at = timestamp
   ```

**Success Criteria**:
- ✅ Alert visible in database
- ✅ Alert returned by API
- ✅ Alert displayed on dashboard
- ✅ Acknowledgment persists across page refresh
- ✅ Summary counts updated correctly

---

### 1.2 Multi-Filter Test

**Objective**: Verify all dashboard filters work correctly.

**Steps**:

1. **Generate 20 Test Alerts** (mixed types)
   ```python
   for position in ['QB', 'RB', 'WR', 'TE', 'K']:
       for source in ['pff', 'nfl']:
           for severity in ['info', 'warning', 'critical']:
               # Generate alert with these attributes
   ```

2. **Test Individual Filters**
   - Filter by severity: "critical" → should show only critical alerts
   - Filter by position: "QB" → should show only QB alerts
   - Filter by source: "pff" → should show only PFF alerts
   - Filter by acknowledged: "false" → should show only unacknowledged

3. **Test Filter Combinations**
   - Severity: critical + Position: QB
   - Source: pff + Acknowledged: false
   - Severity: warning + Source: nfl + Position: RB

4. **Verify Counts**
   - Manual count matches displayed count
   - Summary totals sum to overall total

**Success Criteria**:
- ✅ Each filter individually works
- ✅ Multiple filters work together
- ✅ Counts match expectations
- ✅ Results update instantly

---

### 1.3 Email Delivery Test

**Objective**: Verify email is generated and can be sent.

**Steps**:

1. **Check Email Configuration**
   ```bash
   # Verify environment variables set
   echo $SMTP_HOST $SMTP_PORT $SENDER_EMAIL $ALERT_RECIPIENTS
   
   # For testing, use MailHog (local SMTP server)
   docker run -d --name mailhog -p 1025:1025 -p 8025:8025 mailhog/mailhog
   ```

2. **Test Email Preview Endpoint**
   ```bash
   # Get email digest preview
   curl http://localhost:8000/api/quality/alerts/digest
   
   # Response should include:
   # - subject: "📊 Daily Quality Alert Digest - YYYY-MM-DD"
   # - body_html: "<html>...</html>"
   # - alert_count: number of alerts
   # - critical_count: number of critical
   ```

3. **Manually Trigger Daily Digest**
   ```python
   from src.backend.email_scheduler import EmailAlertScheduler
   scheduler = EmailAlertScheduler(session)
   scheduler._send_daily_digest()  # Sends immediately
   ```

4. **Verify Email Received**
   - Check MailHog web interface: http://localhost:8025
   - Email should appear in inbox
   - Subject should be: "📊 Daily Quality Alert Digest - YYYY-MM-DD"
   - Body should contain HTML with alert statistics

5. **Verify Email Content**
   - Total alert count correct
   - By-severity breakdown accurate
   - Links to dashboard present
   - Formatting is clean HTML

**Success Criteria**:
- ✅ Email preview endpoint returns valid JSON
- ✅ Email sent to all recipients
- ✅ Email HTML is valid and renders
- ✅ Email content matches database

---

### 1.4 Dashboard Real-Time Update Test

**Objective**: Verify dashboard updates in real-time with new alerts.

**Steps**:

1. **Open Dashboard**
   - Navigate to http://localhost:3000/quality
   - Note current alert count

2. **Generate New Alert** (in another terminal)
   ```bash
   python scripts/test_alert_generation.py
   ```

3. **Verify Dashboard Updates**
   - Without page refresh, new alert should appear
   - Alert count should increment
   - Severity distribution should update

4. **Enable Auto-Refresh**
   - Verify auto-refresh timer is running
   - Check "Auto-refresh: 60s" indicator

5. **Disable Auto-Refresh**
   - Toggle off auto-refresh
   - Generate another alert
   - Alert should NOT appear until manual refresh

**Success Criteria**:
- ✅ Dashboard updates automatically
- ✅ Auto-refresh can be toggled
- ✅ Manual refresh works
- ✅ Real-time updates accurate

---

## 2. Automated Integration Testing

### 2.1 Running Integration Tests

```bash
# Run all integration tests
python -m pytest tests/integration/test_email_scheduler.py -v

# Run specific test class
python -m pytest tests/integration/test_email_scheduler.py::TestEmailAlertScheduler -v

# Run with coverage
python -m pytest tests/integration/test_email_scheduler.py --cov=src/backend/email_scheduler
```

**Current Status**: 23/23 tests passing ✅

### 2.2 Phase 5 Integration Test Suite (Template)

Located in: `tests/integration/test_phase5_integration.py`

**Note**: These are test stubs that require:
- Running FastAPI application
- Database with test data
- React testing library for component tests

**Test Categories**:
- API endpoint integration (alert lifecycle, filtering, etc.)
- Dashboard component integration (data flow, user interactions)
- Email system integration (digest generation, delivery)
- End-to-end workflows (generation → display → email)
- Performance benchmarks
- Data validation

---

## 3. Performance Validation

### 3.1 API Response Time Benchmarks

**Test Setup**:
```python
import time
from src.main import app
from fastapi.testclient import client

client = TestClient(app)
```

**Benchmarks**:

| Endpoint | Expected | Measured | Status |
|----------|----------|----------|--------|
| GET /api/quality/alerts | <100ms | — | — |
| GET /api/quality/alerts/summary | <50ms | — | — |
| POST /api/quality/alerts/{id}/acknowledge | <50ms | — | — |
| GET /api/quality/alerts/digest | <200ms | — | — |

**Run Benchmark**:
```bash
# Create test alerts
python scripts/seed_test_data.py

# Run benchmark
python -m pytest tests/performance/test_api_benchmarks.py -v
```

### 3.2 Dashboard Performance

**Metrics to Track**:
- Initial page load: <2 seconds
- AlertList render: <500ms
- AlertSummary render: <300ms
- Filter apply: <200ms
- Alert acknowledgment: <1 second

**Test with Chrome DevTools**:
1. Open http://localhost:3000/quality
2. Open Chrome DevTools → Performance tab
3. Click "Record"
4. Perform action (filter, acknowledge, etc.)
5. Click "Stop"
6. Review: Frame rate >30fps, no janky drops

---

## 4. Error Scenario Testing

### 4.1 Database Connection Loss

**Test**: What happens when database unavailable?

**Steps**:
1. Stop PostgreSQL: `docker stop postgres`
2. Try to access dashboard
3. Expected: Error message, no crash
4. Restart PostgreSQL: `docker start postgres`
5. Dashboard should recover

**Validation**:
- ✅ Error message displayed to user
- ✅ API returns 500 with message
- ✅ No data corruption
- ✅ System recovers automatically

### 4.2 SMTP Configuration Error

**Test**: What happens when SMTP unavailable?

**Steps**:
1. Stop MailHog: `docker stop mailhog`
2. Trigger email send
3. Expected: Error logged, non-blocking

**Validation**:
- ✅ Error logged to application logs
- ✅ Email scheduler continues running
- ✅ Retries attempted
- ✅ User notified (via dashboard or log)

### 4.3 Missing Configuration

**Test**: What happens when ALERT_RECIPIENTS not set?

**Steps**:
1. Unset ALERT_RECIPIENTS env var
2. Try to trigger email send
3. Expected: Graceful handling

**Validation**:
- ✅ No error crash
- ✅ Warning logged
- ✅ Email skipped
- ✅ System continues

---

## 5. Data Integrity Tests

### 5.1 Alert Count Verification

**Test**: Summary statistics match individual alert count.

```python
def test_alert_count_accuracy():
    # Get summary
    summary = GET /api/quality/alerts/summary
    
    # Get individual alerts
    alerts = GET /api/quality/alerts?limit=1000
    
    # Verify
    assert summary['total_alerts'] == len(alerts['alerts'])
    assert summary['by_severity']['critical'] == count(critical alerts)
    assert summary['by_position']['QB'] == count(QB alerts)
```

### 5.2 Acknowledgment Persistence

**Test**: Acknowledgment data persists across operations.

```python
def test_acknowledgment_persists():
    # Create alert
    alert = create_test_alert()
    
    # Acknowledge
    POST /api/quality/alerts/{alert.id}/acknowledge
    
    # Refresh database connection
    reconnect_db()
    
    # Verify still acknowledged
    fresh_alert = GET /api/quality/alerts/{alert.id}
    assert fresh_alert['acknowledged'] == True
    assert fresh_alert['acknowledged_by'] == 'test_user'
```

### 5.3 Email Content Accuracy

**Test**: Email content matches database.

```python
def test_email_content_matches_db():
    # Generate alerts
    create_test_alerts(count=10)
    
    # Get email preview
    digest = GET /api/quality/alerts/digest
    
    # Verify content
    assert digest['alert_count'] == 10
    assert digest['body_html'] contains all alert positions
    assert digest['body_html'] contains all alert sources
```

---

## 6. Load Testing

### 6.1 Concurrent User Test

**Test**: Dashboard handles multiple concurrent users.

```bash
# Using Apache Bench
ab -n 100 -c 10 http://localhost:8000/api/quality/alerts

# Using wrk
wrk -t4 -c100 -d30s http://localhost:8000/api/quality/alerts
```

**Expected Results**:
- Response time: <500ms p95
- Success rate: >99%
- No timeouts

### 6.2 High Alert Volume Test

**Test**: System handles 1000+ alerts.

```python
def test_high_volume():
    # Create 1000 alerts
    for i in range(1000):
        create_test_alert()
    
    # Benchmark retrieval
    start = time.time()
    alerts = GET /api/quality/alerts?limit=100
    elapsed = time.time() - start
    
    assert elapsed < 0.5  # Should complete in <500ms
```

---

## 7. Security Testing

### 7.1 Authentication Test

**Test**: API endpoints require proper authentication.

```bash
# Try without auth token
curl http://localhost:8000/api/quality/alerts  # Should fail

# With auth token
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/quality/alerts  # Should work
```

### 7.2 Authorization Test

**Test**: Users can only access their own data.

```python
def test_user_data_isolation():
    # User A creates alert with position=QB
    # User B tries to access alert
    # Expected: Success (alerts are public) OR only own alerts visible
```

### 7.3 SQL Injection Test

**Test**: Filters are properly sanitized.

```bash
# Try SQL injection in filter
curl "http://localhost:8000/api/quality/alerts?position=QB'; DROP TABLE alerts; --"

# Expected: Either sanitized OR error, NOT executed
```

---

## 8. Documentation Testing

### 8.1 API Documentation

**Verify**:
- [x] OpenAPI docs available at /docs
- [x] All endpoints documented
- [x] Request/response schemas shown
- [x] Example values provided
- [x] All parameters documented

**Access**: http://localhost:8000/docs

### 8.2 Dashboard Documentation

**Verify**:
- [x] Component prop types documented
- [x] Usage examples provided
- [x] Styling guide complete
- [x] API integration documented
- [x] Performance tips included

**File**: `frontend/QUALITY_DASHBOARD_GUIDE.md`

---

## 9. Pre-Launch Checklist

### Backend Validation
- [ ] All 31 Phase 5 tests passing
- [ ] API endpoints respond correctly
- [ ] Database migrations applied
- [ ] Email scheduler configured
- [ ] Error handling comprehensive
- [ ] Logging configured
- [ ] Configuration externalized

### Frontend Validation
- [ ] Dashboard components render
- [ ] All filters work correctly
- [ ] Auto-refresh functioning
- [ ] Responsive design verified
- [ ] Error states handled
- [ ] Loading states shown
- [ ] No TypeScript errors

### Integration Validation
- [ ] Alert lifecycle works end-to-end
- [ ] Dashboard + API integration verified
- [ ] Email generation + sending works
- [ ] Performance meets benchmarks
- [ ] Data integrity verified
- [ ] Security checks passed
- [ ] Documentation complete

### Deployment Readiness
- [ ] Environment variables documented
- [ ] Database backups tested
- [ ] SMTP credentials secured
- [ ] API keys configured
- [ ] Monitoring configured
- [ ] Logging centralized
- [ ] Rollback plan documented

---

## 10. Test Execution Summary

### Current Status (Commit: ef2090c)

| Component | Tests | Status | Notes |
|-----------|-------|--------|-------|
| Email Scheduler | 23 | ✅ PASSING | Mock-based unit tests |
| REST API | 8 | ✅ PASSING | Service layer tests |
| Dashboard | — | — | Manual testing required |
| Integration | — | — | Test stubs created |
| E2E | — | — | Manual procedures documented |
| Performance | — | — | Benchmarks defined |

### Next Steps

1. **Immediate** (30 min):
   - Run Phase 5 integration test stubs
   - Manual E2E testing of alert lifecycle
   - Email delivery testing

2. **Before Launch** (2 hours):
   - Complete remaining integration tests
   - Performance validation
   - Security testing
   - Pre-launch checklist

3. **Post-Launch**:
   - Monitor error logs
   - Gather user feedback
   - Performance optimization
   - Scalability testing

---

## Appendix: Useful Commands

### Database
```bash
# Connect to PostgreSQL
psql -d nfl_draft

# View recent alerts
SELECT id, position, source, severity, acknowledged FROM quality_alerts ORDER BY created_at DESC LIMIT 10;

# View alert count by severity
SELECT severity, COUNT(*) as count FROM quality_alerts GROUP BY severity;
```

### API Testing
```bash
# Get all alerts
curl http://localhost:8000/api/quality/alerts

# Get critical alerts
curl "http://localhost:8000/api/quality/alerts?severity=critical"

# Acknowledge alert
curl -X POST "http://localhost:8000/api/quality/alerts/1/acknowledge" \
  -H "Content-Type: application/json" \
  -d '{"acknowledged_by": "test_user"}'

# Get summary
curl http://localhost:8000/api/quality/alerts/summary

# Get email preview
curl http://localhost:8000/api/quality/alerts/digest
```

### Email Testing
```bash
# Check MailHog
open http://localhost:8025

# View email logs
grep -i "email\|smtp" logs/app.log

# Test SMTP connection
python -c "
import smtplib
smtp = smtplib.SMTP('smtp.gmail.com', 587)
smtp.starttls()
print('✓ SMTP connected')
"
```

### Dashboard Testing
```bash
# React Dev Tools: Chrome Extension
# Vue Dev Tools: Chrome Extension (if using Vue)
# Lighthouse: DevTools → Lighthouse → Generate report
# Performance: DevTools → Performance → Record
```

---

**Document Version**: 1.0  
**Last Updated**: February 21, 2026  
**Phase**: 5 (API Integration & Dashboard)  
**Status**: Testing procedures documented, tests 60% complete
