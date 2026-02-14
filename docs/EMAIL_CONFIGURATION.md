# Email Configuration & Scheduling Guide

## Overview

This guide covers setting up the email alert system for Draft Queen's quality monitoring. The system sends:
1. **Daily Digest** - 9:00 AM EST: Complete summary of previous day's alerts
2. **Morning Summary** - 8:00 AM EST: Brief overview of current alert status

## Configuration

### 1. Environment Variables

Add these to your `.env` file:

```bash
# Email Configuration
EMAIL_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SENDER_EMAIL=noreply@draft-queen.local
SENDER_NAME=Draft Queen Alerts
USE_TLS=true
ALERT_RECIPIENTS=analyst1@company.com,analyst2@company.com,lead@company.com
DAILY_DIGEST_TIME=09:00
MORNING_SUMMARY_TIME=08:00
```

### 2. Gmail Configuration (Recommended)

For Gmail:

1. Enable 2-Factor Authentication
2. Create an App Password: https://myaccount.google.com/apppasswords
3. Use the 16-character password as `SMTP_PASSWORD`
4. Set `SMTP_HOST=smtp.gmail.com` and `SMTP_PORT=587`

### 3. Other Email Providers

**AWS SES**:
```
SMTP_HOST=email-smtp.{region}.amazonaws.com
SMTP_PORT=587
SMTP_USER=your-ses-user
SMTP_PASSWORD=your-ses-password
```

**Office 365**:
```
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=your-email@company.com
SMTP_PASSWORD=your-password
```

**Custom SMTP**:
```
SMTP_HOST=mail.yourdomain.com
SMTP_PORT=587  # or 25, 465
SMTP_USER=your-username
SMTP_PASSWORD=your-password
USE_TLS=true  # or false if using port 465
```

## Implementation Details

### EmailAlertScheduler Class

Located in `src/backend/email_scheduler.py`

**Key Methods**:

```python
# Initialize and start scheduler
scheduler = EmailAlertScheduler(session)
scheduler.start()

# Stop scheduler (cleanup)
scheduler.stop()

# Manual operations
scheduler.send_immediate_critical_alert("Alert message")
scheduler.cleanup_old_alerts()
```

**Configuration Loading**:

- Loads SMTP settings from environment variables via `settings` object
- Loads recipient list from `ALERT_RECIPIENTS` (comma-separated)
- Creates APScheduler tasks for daily jobs at specified times
- Runs in background thread (non-blocking)

### Scheduled Jobs

**Daily Digest (9:00 AM EST)**:
- Generates 24-hour alert digest
- Includes all alerts from previous day
- Filtered by severity/type
- Sent to all recipients
- Includes link to Quality Dashboard
- Error handling: Logs failures, continues if partial delivery

**Morning Summary (8:00 AM EST)**:
- Quick overview of alert statistics
- Critical count highlighted
- Doesn't resend yesterday's alerts
- Helps with morning status check
- Can be disabled by not configuring time

### Integration with FastAPI

In your `main.py`:

```python
from src.backend.email_scheduler import setup_email_scheduler
from sqlalchemy.orm import Session

# At app startup
@app.on_event("startup")
async def startup():
    db = SessionLocal()
    try:
        if settings.email_enabled and settings.scheduler_enabled:
            setup_email_scheduler(db)
    finally:
        db.close()

# At app shutdown
@app.on_event("shutdown")
async def shutdown():
    # Scheduler stops automatically when app exits
    pass
```

## Testing

### Manual Testing

**Test email sending**:

```python
from src.backend.email_scheduler import EmailAlertScheduler
from sqlalchemy.orm import Session

scheduler = EmailAlertScheduler(session)
scheduler.send_immediate_critical_alert("Test alert from Draft Queen")
```

**Test digest generation**:

```python
# Via API endpoint (created in Phase 5)
GET /api/quality/alerts/digest

# Returns email preview that would be sent
```

### Verify Configuration

```bash
# Check SMTP connectivity
python -c "
import smtplib
smtp = smtplib.SMTP('smtp.gmail.com', 587)
smtp.starttls()
smtp.login('{SMTP_USER}', '{SMTP_PASSWORD}')
print('✓ SMTP configuration valid')
smtp.quit()
"
```

## Production Deployment

### Recommended Setup

1. **Email Service**: AWS SES (highly reliable, good pricing)
2. **Recipients**: Team distribution list email address
3. **Timezone**: Set to your team's timezone in `daily_digest_time`
4. **Schedule**: Adjust times based on team preferences

### Monitoring

Add to your monitoring dashboard:

```python
# Check scheduled jobs
scheduler.scheduler.get_jobs()

# Monitor email sending failures in logs
grep "Failed to send digest" logs/app.log
```

### Error Handling

The email scheduler handles:
- ✅ Invalid SMTP credentials (logs error, continues)
- ✅ Network timeouts (retry logic in APScheduler)
- ✅ No recipients configured (logs warning, skips)
- ✅ Database connection errors (logs error, continues)
- ✅ Partial delivery failures (sends to remaining recipients)

## API Integration

### Email Preview Endpoint

```
GET /api/quality/alerts/digest?days_back=1

Returns:
{
  "subject": "📊 Daily Quality Alert Digest - 2024-02-21",
  "body_html": "<html>...</html>",
  "recipient_count": 3,
  "alert_count": 12,
  "critical_count": 2,
  "generated_at": "2024-02-21T14:30:00Z"
}
```

This endpoint lets you preview what the email will contain before it's sent.

## Advanced Configuration

### Custom Alert Templates

Modify `_format_summary_email()` method to customize email appearance:

```python
def _format_summary_email(self, summary: dict) -> str:
    # Your custom HTML template here
    pass
```

### Per-Recipient Configuration

To send different alerts to different recipients:

```python
# Modify _send_daily_digest to check recipient preferences
for recipient_email in self.recipient_list:
    # Load recipient preferences from database
    prefs = load_recipient_preferences(recipient_email)
    
    # Filter alerts based on preferences
    if prefs.include_info:
        # include info alerts
```

### Critical Alert Escalation

```python
# Send immediate SMS for critical production issues
scheduler.send_immediate_critical_alert(alert_message)

# Could integrate Twilio for SMS escalation:
from twilio.rest import Client
client = Client(account_sid, auth_token)
client.messages.create(to="+1234567890", from_="+0987654321", body=alert_message)
```

## Troubleshooting

### Emails not sending

1. **Check if enabled**:
   ```bash
   echo $EMAIL_ENABLED
   # Should be: true
   ```

2. **Check SMTP credentials**:
   ```bash
   # Test SMTP connection
   python scripts/test_smtp.py
   ```

3. **Check APScheduler logs**:
   ```bash
   grep "daily_alert_digest\|morning_alert_summary" logs/app.log
   ```

4. **Verify recipients configured**:
   ```bash
   echo $ALERT_RECIPIENTS
   # Should have at least one email
   ```

### Emails going to spam

1. Add SPF record to DNS: `v=spf1 include:mail.google.com ~all`
2. Add DKIM record (Gmail provides automatically)
3. Use branded domain in `SENDER_EMAIL`
4. Include unsubscribe link in email template

### Scheduler not starting

1. Check if `SCHEDULER_ENABLED=true`
2. Check database connection at startup
3. Verify APScheduler installed: `pip install apscheduler`
4. Check logs for startup errors

## Testing with Docker

```dockerfile
# docker-compose.yml
services:
  app:
    environment:
      - EMAIL_ENABLED=true
      - SMTP_HOST=mailhog  # Local SMTP for testing
      - SMTP_PORT=1025
      - ALERT_RECIPIENTS=test@example.com
```

Then access emails at: http://localhost:8025

## Phase 5 Completion Checklist

- [x] Email configuration in settings.py
- [x] EmailAlertScheduler class created
- [x] APScheduler integration
- [x] Daily digest job
- [x] Morning summary job
- [ ] Integration tests
- [ ] End-to-end testing
- [ ] Production deployment guide

## Next Steps

After this is deployed:

1. Run integration tests to verify API + Email system
2. Test end-to-end workflow: Alert generated → Email sent → Dashboard updated
3. Monitor first week for any issues
4. Adjust email schedule based on team feedback
5. Consider adding SMS escalation for critical alerts

