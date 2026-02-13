# Security Audit Findings - Bug Tracking

**Date:** February 13, 2026  
**Status:** Triaged - Awaiting Sprint Assignment  
**Audit Report:** [docs/guides/SECURITY_REPORT.md](../guides/SECURITY_REPORT.md)

---

## Overview

This document tracks security issues identified in the February 13, 2026 security audit. Three critical issues were immediately fixed:
- ✅ Hardcoded credentials (FIXED in commit 0a4f109)
- ✅ CORS misconfiguration (FIXED in this commit)
- ✅ Missing authentication (FIXED in this commit)

Two additional issues require planning and assignment to sprints.

---

## BUG-001: Subprocess Call Without Validation Logging

**Severity:** Medium  
**Status:** Under Review  
**Component:** `src/backend/api/routes.py`, line 595-605

### Issue
While the subprocess call for database migrations is currently secure (hardcoded command, no shell injection), it lacks validation logging and should be documented for future maintainers.

```python
@admin_router.post("/admin/db/migrate")
async def run_migrations(admin_token: str = Depends(verify_admin_token)):
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
        timeout=60
    )
```

### Current Status
✅ **Secure** - No user input in command, list-based args prevent injection, has timeout

### Recommended Fix
- Add inline comment documenting security rationale
- Consider moving migration endpoint to CLI instead of HTTP (better for production)
- Add validation that alembic executable exists before running

### Code Example
```python
# SECURE: List format prevents shell injection, no user input
result = subprocess.run(
    ["alembic", "upgrade", "head"],  # Hardcoded command
    capture_output=True,
    text=True,
    timeout=60
)
```

### Priority
**Low** - Current implementation is safe, but should be documented for team knowledge

### Suggested Sprint
Sprint 5 or later (post-launch tech debt)

---

## BUG-002: Admin Operations Missing Audit Logging

**Severity:** Medium  
**Status:** Partially Fixed (logging added, needs review)  
**Component:** `src/backend/api/routes.py` - all admin endpoints

### Issue
Administrative operations (migrations, backups, pipeline execution) lack comprehensive audit logging. This prevents tracking who performed what actions and when.

### Scope
- POST `/admin/db/migrate` - Database migrations
- POST `/admin/db/backup` - Database backups
- POST `/pipeline/run` - Pipeline execution
- Other admin endpoints

### Current Status
⚠️ **Partially Fixed** - Basic audit logging added via `log_admin_action()` function
- Timestamp recorded
- Admin action name recorded
- Basic status recorded

### Recommended Enhancements

**1. User Identification**
```python
# Future: Add user information if using JWT/OAuth
log_admin_action("db_migrate", "success", {
    "user_id": current_user.id,  # TODO: Add when auth is JWT-based
    "user_email": current_user.email,
    "return_code": result.returncode
})
```

**2. Persistent Audit Log Table**
```python
# Consider creating an audit_log table instead of just logging
class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    action = Column(String(255))
    status = Column(String(50))
    user_id = Column(String(255))  # Future: foreign key when users table exists
    details = Column(JSON)
```

**3. Structured Logging Format**
```python
# Current: Uses Python logging (goes to log files)
logger.warning(f"ADMIN_ACTION: {log_data}")

# Recommended: Add structured logging to separate audit stream
audit_logger = logging.getLogger("audit")
audit_logger.warning(json.dumps(log_data))
```

### Priority
**Medium** - Necessary for compliance and security incident investigation

### Suggested Sprint
Sprint 5 or Sprint 6 (compliance requirement for production)

### Dependencies
- May need user/authentication system first (currently not implemented)
- May need audit_logs database table

### Acceptance Criteria
- [ ] All admin actions logged with timestamp
- [ ] Audit logs accessible for compliance review
- [ ] Logs show who performed what action and when
- [ ] Logs retained for 90+ days
- [ ] Test: Verify migration logged when run with admin key

---

## BUG-003: Missing Request Rate Limiting

**Severity:** Medium (Not in original audit, but related)  
**Status:** Not Started  
**Component:** `src/backend/api/routes.py` and `main.py`

### Issue
API endpoints lack rate limiting, making them vulnerable to:
- Brute force attacks on protected endpoints
- Denial of Service (DoS) attacks
- Resource exhaustion

### Example Attack
```bash
# No rate limiting = unlimited requests
for i in {1..10000}; do
  curl -X POST http://api.local/pipeline/run \
    -H "X-API-Key: $ADMIN_KEY"
done
```

### Recommended Solution
```python
# Install: pip install slowapi

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# Protect admin endpoints
@admin_router.post("/admin/db/migrate")
@limiter.limit("5/hour")  # 5 requests per hour
async def run_migrations(admin_token: str = Depends(verify_admin_token)):
    ...

# Protect query endpoints
@query_router.post("/query")
@limiter.limit("60/minute")  # 60 requests per minute
async def query_prospects(filters: QueryFilterSchema):
    ...
```

### Priority
**Medium** - Should be implemented before production launch

### Suggested Sprint
Sprint 5 (before launch)

### Acceptance Criteria
- [ ] Admin endpoints: 5 requests/hour per IP
- [ ] Query endpoints: 60 requests/minute per IP
- [ ] Export endpoints: 10 requests/hour per IP
- [ ] Pipeline endpoints: 5 requests/day per IP
- [ ] Test: Verify rate limiting returns 429 status when exceeded

---

## BUG-004: Error Messages Reveal System Details

**Severity:** Low  
**Status:** Not Started  
**Component:** All endpoints

### Issue
Exception handlers return full error details to clients, potentially revealing system information that could aid attackers.

### Example Vulnerability
```python
# Current - reveals internal details
@query_router.post("/query")
async def query_prospects(filters: QueryFilterSchema):
    try:
        # ...query logic...
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))  # ❌ Shows internal error
```

### Attack Scenario
```bash
curl -X POST http://api.local/query -d '{invalid json}'
# Response: 500 Internal Server Error
# Body: "Traceback: line 123 in query_service.py: ValueError: Invalid prospect ID format"
# Attacker learns: System uses query_service.py, expects prospect IDs in specific format
```

### Recommended Fix
```python
# Generic error messages for clients
@query_router.post("/query")
async def query_prospects(filters: QueryFilterSchema):
    try:
        # ...query logic...
    except ValueError:
        # Log details for debugging
        logger.error(f"Query validation failed: {str(e)}", exc_info=True)
        # Return generic message
        raise HTTPException(
            status_code=400,
            detail="Invalid query parameters"  # Generic
        )
    except Exception as e:
        # Log full details
        logger.error(f"Query execution failed: {str(e)}", exc_info=True)
        # Return generic message
        raise HTTPException(
            status_code=500,
            detail="Query execution failed"  # Generic, not revealing
        )
```

### Priority
**Low** - Good security practice, but won't directly expose secrets

### Suggested Sprint
Sprint 5 or Sprint 6 (security hardening)

### Acceptance Criteria
- [ ] No system paths in error responses
- [ ] No internal stack traces in error responses
- [ ] No SQL query details in error responses
- [ ] All errors logged with full details for debugging
- [ ] Test: Verify client sees generic error, logs show detailed error

---

## Summary Table

| Bug ID | Title | Severity | Status | Sprint | Est. Points |
|--------|-------|----------|--------|--------|------------|
| BUG-001 | Subprocess validation logging | Medium | Under Review | Sprint 5+ | 3 |
| BUG-002 | Admin audit logging enhancements | Medium | Partially Fixed | Sprint 5-6 | 8 |
| BUG-003 | Missing rate limiting | Medium | Not Started | Sprint 5 | 5 |
| BUG-004 | Error message information leakage | Low | Not Started | Sprint 6 | 3 |

---

## Fixed Issues (No Further Action Required)

✅ **Issue #1: Hardcoded Credentials**
- Fixed in commit: 0a4f109
- File: `src/config.py`, `.env.example`
- Status: CLOSED

✅ **Issue #2: CORS Misconfiguration**
- Fixed in commit: (current)
- File: `main.py`
- Status: CLOSED

✅ **Issue #3: Missing Authentication on Admin Endpoints**
- Fixed in commit: (current)
- File: `src/backend/api/routes.py`
- Status: CLOSED

---

## Next Steps

1. **Immediate (Today):**
   - [ ] Review and merge these fixes to main
   - [ ] Update .env with new ADMIN_API_KEY setting
   - [ ] Test authentication on admin endpoints

2. **Before Sprint 5 Starts:**
   - [ ] Assign BUG-002 (audit logging) to Sprint 5
   - [ ] Assign BUG-003 (rate limiting) to Sprint 5
   - [ ] Create Jira/Linear issues for each bug

3. **Before Production Launch:**
   - [ ] Complete all Medium severity items
   - [ ] Review and consider Low severity items
   - [ ] Run security scan with Bandit
   - [ ] Penetration testing

---

**Prepared by:** GitHub Copilot  
**Last Updated:** February 13, 2026
