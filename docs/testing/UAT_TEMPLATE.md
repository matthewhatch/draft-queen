# UAT Checklist Template - Sprint Testing Guide
**Purpose:** Standardized verification process for all sprint user stories

---

## Pre-UAT Setup (Day 1 of Testing)

- [ ] All development code merged to main branch
- [ ] Code review completed and approved
- [ ] All unit tests passing (100% pass rate)
- [ ] No critical SonarQube/Bandit issues
- [ ] Test database populated with sample data
- [ ] Test environment matches production config
- [ ] UAT team has access to all systems
- [ ] Known issues documented

---

## UAT Process for Each User Story

### Step 1: Story Preparation
For each user story in the sprint:
1. Read entire user story (description + acceptance criteria)
2. Note any dependencies on other stories
3. Verify story-specific test environment setup
4. Gather test data/test accounts if needed

### Step 2: Acceptance Criteria Testing
For each acceptance criterion:
```markdown
- [ ] **AC-#:** [Criterion description]
  - **Test:** [What to do]
  - **Expected:** [What should happen]
  - **Result:** ✅ PASS / ❌ FAIL / ⚠️ PARTIAL
  - **Evidence:** [Screenshot/Log/Note]
  - **Blocker:** Yes/No
```

### Step 3: Non-Functional Requirements
- [ ] Performance targets met (response time, throughput)
- [ ] Error handling works correctly
- [ ] Logging captures important events
- [ ] Database queries optimized
- [ ] No memory leaks or resource issues
- [ ] Backward compatibility maintained

### Step 4: Edge Cases
- [ ] Empty/null data handling
- [ ] Boundary value testing
- [ ] Large data set testing
- [ ] Invalid input handling
- [ ] Concurrent request handling

### Step 5: Documentation
- [ ] Code comments clear and accurate
- [ ] README updated if needed
- [ ] API documentation accurate
- [ ] Configuration documented
- [ ] Known limitations noted

### Step 6: Sign-Off
```markdown
**Story:** US-###
**Tested By:** [Name]
**Date:** [Date]
**Status:** ✅ APPROVED / ⚠️ REWORK NEEDED / ❌ BLOCKED

**Issues Found:**
- [List any issues]

**Recommendations:**
- [Any suggestions]
```

---

## Common UAT Test Cases by Feature Type

### API Endpoints
```markdown
- [ ] Endpoint exists and responds with correct HTTP method
- [ ] Request validation works (invalid params return 400)
- [ ] Response schema matches documentation
- [ ] Response time < target (e.g., 500ms)
- [ ] Error responses include helpful messages
- [ ] Rate limiting works (if applicable)
- [ ] Authentication/authorization works
- [ ] CORS headers correct
```

### Database Operations
```markdown
- [ ] Create records successfully
- [ ] Read records with correct filtering
- [ ] Update records preserve other data
- [ ] Delete records cleanly
- [ ] Foreign key constraints enforced
- [ ] Unique constraints enforced
- [ ] Indexes improve performance
- [ ] NULL handling correct
```

### Data Export/Import
```markdown
- [ ] Exports all data correctly
- [ ] Exports maintain formatting
- [ ] Imports parse correctly
- [ ] Large file handling works
- [ ] Special characters encoded properly
- [ ] File headers/structure correct
- [ ] Can re-import exported data
```

### UI/Dashboard Features
```markdown
- [ ] Page loads within 3 seconds
- [ ] All interactive elements respond to clicks
- [ ] Forms validate input before submission
- [ ] Messages display success/error appropriately
- [ ] Responsive design works on mobile/tablet
- [ ] Dark mode (if applicable) functions
- [ ] Accessibility features work
- [ ] Cross-browser compatibility verified
```

### Background Jobs/Scheduled Tasks
```markdown
- [ ] Job triggers at correct time
- [ ] Job completes successfully
- [ ] Job handles errors gracefully
- [ ] Retry logic works on failure
- [ ] Logging captures execution details
- [ ] Job doesn't cause performance issues
- [ ] Can be manually triggered
- [ ] Can be paused/stopped
```

### Security Features
```markdown
- [ ] Authentication required where needed
- [ ] Invalid credentials rejected
- [ ] Authorization enforced by role
- [ ] Secrets not logged or exposed
- [ ] SQL injection prevented
- [ ] XSS attacks prevented
- [ ] CSRF tokens validated
- [ ] Rate limiting prevents abuse
```

---

## Performance Testing Checklist

For stories with performance acceptance criteria:

```markdown
**Load Test Scenarios:**

1. **Baseline Test** (Single User)
   - [ ] Response time recorded
   - [ ] No errors
   - [ ] Resource usage normal

2. **Normal Load Test** (10 concurrent users)
   - [ ] All requests succeed
   - [ ] Response time degradation < 20%
   - [ ] No timeouts

3. **Peak Load Test** (50 concurrent users)
   - [ ] Degradation acceptable
   - [ ] No cascading failures
   - [ ] Queue mechanism works if implemented

4. **Endurance Test** (8-hour run)
   - [ ] No memory leaks
   - [ ] Database connections stable
   - [ ] Logging doesn't cause bloat

5. **Spike Test** (Normal → 100 users instantly)
   - [ ] System recovers gracefully
   - [ ] Queuing works
   - [ ] Monitoring alerts trigger
```

---

## Data Quality Testing Checklist

For data-related stories:

```markdown
- [ ] Data completeness verified (no missing required fields)
- [ ] Data accuracy spot-checked (values are reasonable)
- [ ] Data consistency across related tables
- [ ] Duplicate detection/prevention works
- [ ] Data type conversions correct
- [ ] Date/time handling correct
- [ ] Null/empty handling documented
- [ ] Archival/retention policies work
```

---

## UAT Sign-Off Criteria

A user story is approved for production when:

1. ✅ All acceptance criteria tested and passed
2. ✅ No critical or high-priority bugs
3. ✅ Performance targets met
4. ✅ Error handling verified
5. ✅ Documentation complete and accurate
6. ✅ Security requirements met
7. ✅ Cross-platform/browser compatibility verified
8. ✅ Known limitations documented

---

## UAT Defect Severity Levels

### 🔴 Critical (BLOCKER)
- Complete feature failure
- Data loss or corruption
- Security vulnerability
- System crash
- **Action:** Return to dev immediately

### 🟠 High (MAJOR)
- Significant functionality broken
- Performance well below targets
- Workaround difficult/impossible
- **Action:** Developer fixes before production

### 🟡 Medium (MINOR)
- Minor functionality issue
- Workaround available
- Performance slightly below targets
- **Action:** Can be approved with dev note

### 🟢 Low (NICE-TO-HAVE)
- Cosmetic issues
- Suggestions for improvement
- **Action:** Can proceed, noted for future

---

## Post-UAT Activities

### If All Tests Pass ✅
1. [ ] Generate UAT report
2. [ ] Get stakeholder sign-off
3. [ ] Merge code to production branch
4. [ ] Tag release in git
5. [ ] Update deployment checklist
6. [ ] Prepare production deployment

### If Issues Found ⚠️
1. [ ] Categorize issues by severity
2. [ ] Log defects in issue tracker
3. [ ] Assign to developers
4. [ ] Set target fix dates
5. [ ] Schedule re-test after fixes
6. [ ] Document workarounds if needed

---

## UAT Report Template

```markdown
# UAT Report - [Sprint #]
**Sprint:** Sprint # ([Date])  
**Duration:** [Start - End dates]  
**Total Stories:** [#]  
**Stories Passed:** [#] ✅  
**Stories Failed:** [#] ❌  
**Stories Blocked:** [#] 🔒  

## Results
| Story | Points | Status | Notes |
|-------|--------|--------|-------|
| US-### | # | ✅ PASS | [Brief note] |

## Issues Found
| ID | Severity | Description | Status |
|---|---|---|---|
| BUG-001 | 🔴 Critical | [Description] | Assigned to [Dev] |

## Sign-Off
- QA Lead: [Name]
- Product Owner: [Name]
- DevOps: [Name]

**Approved for Production:** ✅ YES / ❌ NO

Date: [Date]
```

---

## Best Practices for UAT

1. **Test as a User** - Think like the end user, not a developer
2. **Follow Happy Path First** - Then test edge cases
3. **Document Everything** - Screenshots, logs, timestamps
4. **Test on Latest Code** - Don't test outdated branches
5. **Test in Production-Like Environment** - Not just local dev
6. **Test with Real Data** - Not just sample data
7. **Test with Different User Roles** - Admin, analyst, basic user
8. **Be Thorough but Efficient** - Don't waste time, focus on value
9. **Communicate Issues Clearly** - Provide steps to reproduce
10. **Sign Off Formally** - Use consistent sign-off process

---

## Tools & Resources

- **API Testing:** Postman, Insomnia, curl
- **Database Testing:** psql, pgAdmin, DBeaver
- **Performance:** Apache JMeter, wrk, ab
- **Automation:** pytest, Selenium, Cypress
- **Logging:** tail, grep, ELK stack
- **Monitoring:** Prometheus, Grafana, New Relic
- **Screenshots:** Gyroflow Toolbox, ScreenFlow, Snagit

---

**Last Updated:** February 14, 2026  
**Next Review:** After each sprint

