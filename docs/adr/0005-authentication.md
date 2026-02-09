# ADR 0005: Authentication & Authorization - Simple Internal Access

**Date:** 2026-02-09  
**Status:** Accepted

## Context

Original design included OAuth2 for multi-tenant public platform. However, strategic pivot changed requirements:
- Target users: 5-10 internal analysts/researchers
- Deployment: Single organization, private network
- No external public access
- Data sensitivity: Moderate (internal use only)
- User management overhead: Not justified for small team

We must decide: full OAuth2 implementation vs. simplified internal access control.

## Decision

We implement **simplified internal access control** (no OAuth2):

**Authentication Methods**

1. **Development/Staging (No Authentication)**
   - Open API: anyone with network access can query
   - Rationale: Internal network; risk acceptable
   - Use: local development, staging environment

2. **Production (API Key + TLS)**
   - All requests require API key in Authorization header
   - Keys managed by administrator
   - Each analyst gets unique key for audit logging
   - TLS/HTTPS enforces encrypted transport
   - Implementation: FastAPI middleware checks `Authorization: Bearer {key}`

**Authorization Model**

```
API Keys Table:
  id, key_hash, analyst_name, created_date, last_used, status

All analysts have same permissions:
  - Read all prospect data
  - Read all analytics
  - Export data
  - No write access (only backend updates data)
  - No admin access

Future expansion if needed:
  - Read-only role (current default)
  - Admin role (manage API keys, trigger refresh)
```

**Implementation**

```python
# Simple API key middleware
@app.middleware("http")
async def verify_api_key(request: Request, call_next):
    if request.url.path in ["/health", "/docs"]:
        return await call_next(request)
    
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse({"error": "Missing API key"}, status_code=401)
    
    key = auth_header.split(" ")[1]
    if not verify_key(key):
        return JSONResponse({"error": "Invalid API key"}, status_code=401)
    
    request.state.analyst_id = get_analyst_for_key(key)
    return await call_next(request)
```

## Consequences

### Positive
- Simple: no OAuth provider setup, no redirect flows
- Fast: verification is single database lookup
- Internal: sufficient for closed organization
- Auditable: each key tied to individual analyst
- Secure enough: TLS + API key protects against casual access
- Low operational overhead: no user management UI needed

### Negative
- No fine-grained permissions: all analysts have full read access
- Key rotation manual: administrator must rotate keys periodically
- No delegation: can't grant temporary access
- Vulnerable to key leaks: compromised key is full access
- Not standard: doesn't follow OAuth2 industry patterns
- No refresh tokens: keys valid indefinitely

### Security Assumptions
- Assumes: network is trusted (private internal network)
- Assumes: analysts are trusted employees
- Assumes: keys handled carefully (not committed to repos)
- Assumes: TLS certificates properly managed

### Key Management Procedure
```
Setup (First Time):
  1. Admin generates key for new analyst
  2. Key delivered via secure channel (in-person, encrypted email)
  3. Analyst stores in secure location (password manager)

Rotation (Quarterly):
  1. Admin generates new key
  2. Old key marked for deactivation (7-day grace period)
  3. Analysts update their tools
  4. Old key deactivated after grace period

Compromise:
  1. Admin immediately deactivates compromised key
  2. Generate new key for affected analyst
  3. Audit logs reviewed for suspicious access
```

## Alternatives Considered

### Full OAuth2 (Google, Okta, Auth0)
- Better: industry standard; fine-grained permissions; delegation
- Worse: significant implementation overhead; requires external provider
- Decision: Rejected for internal-only use case; overkill complexity

### Kerberos/LDAP (Corporate Directory)
- Better: integrates with corporate security; centralized management
- Worse: requires corporate infrastructure; deployment complexity
- Decision: Possible future upgrade if company has LDAP
- Current decision: API keys simpler for MVP

### Mutual TLS (mTLS)
- Better: certificate-based authentication
- Worse: certificate distribution and rotation overhead
- Decision: API key simpler to manage initially

### No Authentication (Public Access)
- Rejected: Even internal tool needs basic audit trail

## Migration Path

If organization grows or security requirements change:
1. Phase 1: Add fine-grained roles (read-only, admin, analyst-specific views)
2. Phase 2: Integrate with corporate LDAP/Okta if available
3. Phase 3: Migrate to OAuth2 if public API needed later

## Related Decisions
- ADR-0001: Technology Stack (FastAPI handles auth middleware)
- ADR-0006: Audit Logging (logs track which analyst accessed what)
