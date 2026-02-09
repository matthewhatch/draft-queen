# ADR 0009: Data Sourcing Strategy - Public Web Scrapers vs API Integration

**Date:** 2026-02-09  
**Status:** Accepted  
**Decision Made By:** Product Manager

## Context

Original data ingestion strategy (US-005) assumed fetching from available APIs. However, NFL prospect data sources vary in availability:
- **NFL.com:** Public website, no official API, data scattered across pages
- **Yahoo Sports:** Public website, no official API
- **ESPN:** Public website, some API endpoints
- **Pro Football Reference:** Public data, limited real-time updates

We need to decide: build web scrapers for public sources vs. rely on APIs where available.

## Decision

We will **build web scrapers for public sources** (prioritizing NFL.com and Yahoo Sports) with the following strategy:

**Phase 1 (Sprint 1): NFL.com Scraper**
- Scrape NFL.com Scouting Combine results
- Scrape NFL.com Draft tracking pages
- Extract: name, position, college, height, weight, 40-time, vertical, broad jump
- Daily refresh at 3 AM
- Fallback to cached data if scraping fails

**Phase 2 (Sprint 2): Yahoo Sports Scraper (if needed)**
- Additional metrics not available from NFL.com
- College stats and production metrics
- Alternative data source for redundancy

**Phase 3 (Sprint 3): ESPN Integration (if available)**
- Injury reports and updates
- Breaking news and prospect status changes

## Technical Approach

**Web Scraping Libraries**
```python
# Core libraries
beautifulsoup4  # HTML parsing
requests        # HTTP requests
selenium        # JavaScript-rendered pages (if needed)
lxml            # Fast XML/HTML parsing

# Data extraction
pandas          # Data transformation
tenacity        # Retry logic
```

**Scraper Architecture**
```
scrapers/
├── nfl_com_scraper.py      # Combine results, draft tracking
├── yahoo_sports_scraper.py # College stats (phase 2)
├── espn_scraper.py         # Injury reports (phase 3)
├── base_scraper.py         # Common utilities, error handling
└── tests/
    ├── test_nfl_scraper.py
    ├── test_yahoo_scraper.py
    └── fixtures/           # HTML samples for testing
```

**Robustness Strategy**
- User-Agent rotation: Mimic real browser requests
- Rate limiting: Respectful 1-2s delays between requests
- Retry logic: Exponential backoff for timeouts
- Data validation: Verify scraped data matches expected schema
- Fallback caching: If scrape fails, use yesterday's data
- Error logging: Track all failures for debugging

**HTML Page Structure Examples**

NFL.com Combine Results:
```html
<table class="combine-results">
  <tr>
    <td>Player Name</td>
    <td>6'2"</td>  <!-- Height -->
    <td>215 lbs</td> <!-- Weight -->
    <td>4.89s</td>   <!-- 40-time -->
  </tr>
</table>
```

Data extraction:
```python
from bs4 import BeautifulSoup
import requests

def scrape_nfl_combine():
    url = "https://www.nfl.com/draft/2026/tracker"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0..."})
    soup = BeautifulSoup(resp.content, 'html.parser')
    
    prospects = []
    for row in soup.find_all('tr', class_='prospect-row'):
        prospect = {
            'name': row.find('td', class_='name').text,
            'position': row.find('td', class_='pos').text,
            'height': parse_height(row.find('td', class_='ht').text),
            'weight': parse_weight(row.find('td', class_='wt').text),
            'forty_time': float(row.find('td', class_='forty').text),
        }
        prospects.append(prospect)
    
    return prospects
```

## Data Quality Considerations

**Challenges with Web Scraping**
- HTML structure changes: Site updates break scrapers (monitored, quick fixes)
- Missing data: Some players may have incomplete measurements
- Duplicate detection: Same player may appear across multiple sources
- Data freshness: Updates may lag real-time changes by hours

**Mitigations**
- Version scrapers: Keep git history of page structures
- Unit tests: HTML fixtures snapshot page structure
- Duplicate detection: Fuzzy matching on name + position + college
- Data reconciliation: Cross-reference multiple sources
- Audit trail: Log all changes for verification

## Consequences

### Positive
- **No API dependency:** Doesn't rely on external API availability
- **Public data:** No licensing or authentication concerns
- **Current information:** Access to most recent prospect data
- **Comprehensive:** Can scrape multiple sources for data triangulation
- **Cost:** Free (just development time)

### Negative
- **Fragility:** Scraping breaks when website structure changes
- **Ethical concerns:** Must respect robots.txt and rate limits
- **Legal gray area:** Terms of service typically forbid scraping
- **Maintenance burden:** Ongoing monitoring and fixes needed
- **Slower than API:** HTML parsing slower than structured data
- **No guarantees:** Websites can block scrapers

### Acceptable Risks?
- Yes: Prospect data is public information
- Yes: Respectful scraping (slow, user-agent headers) unlikely to cause problems
- Yes: If blocked, can pivot to manual data entry or partner APIs
- Yes: Internal tool (not commercial resale)

## Legal & Ethical Considerations

**robots.txt Compliance**
- Respect robots.txt disallowance
- Check sites before implementation:
  - `https://www.nfl.com/robots.txt`
  - `https://sports.yahoo.com/robots.txt`

**Terms of Service**
- Most prohibit scraping; however, we're:
  - Using public data (not proprietary)
  - Internal use (not commercial)
  - Respectful rate limiting (1-2s between requests)
  - Not reproducing copyrighted content (just factual data)

**Risk Mitigation**
- If cease-and-desist received: Stop immediately, pivot to partner APIs
- Alternative: Reach out to leagues for official data partnerships
- Fallback: Manual data entry or crowdsourced data

## Implementation Plan

**Sprint 1 Deliverable (US-005 Updated)**
- NFL.com Combine scraper (working prototype)
- Tests with sample HTML
- Integrated into daily pipeline
- Data validation before database load
- Error handling and logging

**Sprint 2 (if needed)**
- Yahoo Sports scraper for additional metrics
- Redundancy: validate NFL.com data against Yahoo Sports
- Data quality improvements

**Sprint 3 (if needed)**
- ESPN injury reports
- Real-time alerts for roster changes

## Alternatives Considered

### Official NFL Data API
- Better: Reliable, supported, legal
- Worse: Not publicly available; may require partnerships
- Decision: Research partnerships for future

### Manual Data Entry
- Better: Reliable, no scraping concerns
- Worse: Requires full-time person; slow; error-prone
- Decision: Not viable for 2,000+ prospects

### Crowdsourced Data (Google Forms, etc.)
- Better: Community involvement
- Worse: Quality variable, slow to populate
- Decision: Possible long-term; not viable for MVP

### Partner APIs (Stats Inc, Next Gen Stats)
- Better: Official, reliable, comprehensive
- Worse: Costly; licensing restrictions
- Decision: Consider for 2.0 if budget allows

### Data Vendors (PFF, Sportradar, etc.)
- Better: Professional-grade data
- Worse: Expensive, licensing restrictions
- Decision: Not justified for internal MVP tool

## Related Decisions
- ADR-0002: Data Architecture (pipeline design accommodates scrapers)
- ADR-0001: Technology Stack (Python ideal for web scraping)

## Future Decisions Needed

1. **Data Accuracy:** How often validate against external sources?
2. **Update Frequency:** Daily at 3 AM or real-time monitoring?
3. **Source Prioritization:** Which source is authoritative if conflicts?
4. **Backup Strategy:** What if all sources fail simultaneously?
5. **Archive Strategy:** Keep historical scrapes for trend analysis?

---

## Product Manager Notes

This decision enables us to build a data-driven platform without external data partnerships. However, we should:

1. **Plan for contingency:** Have a pivot strategy if scraping becomes problematic
2. **Monitor risk:** Check for legal/ethical issues quarterly
3. **Evaluate partnerships:** As we grow, explore official data channels
4. **User transparency:** Be clear that data comes from public web sources (not official NFL data)

The trade-off is acceptable for an MVP internal tool, but long-term we should pursue official partnerships if this becomes production-critical.
