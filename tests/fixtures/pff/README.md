# PFF HTML Test Fixtures

## Overview
These HTML fixtures represent realistic snapshots of PFF.com Draft Big Board pages, used for unit testing the scraper without requiring network access.

## Files

### page_1.html
**Purpose:** Test basic scraping functionality with standard prospects

**Contains:**
- 8 prospect cards
- 5 complete prospects with all fields (name, rank, position, school, class, grade)
- 2 edge cases:
  - Missing grade field
  - Missing school field
- 1 special character test (C.J. Stroud Jr.)

**Use Case:** Test basic parsing, field extraction, and graceful handling of missing data

### page_2.html
**Purpose:** Test edge cases, validation failures, and data quality issues

**Contains:**
- 7 prospect cards
- 3 valid prospects
- 4 edge/invalid cases:
  - Grade > 100 (invalid, should be filtered)
  - Negative grade (invalid, should be filtered)
  - International school name
  - Complex multi-part name
  - Empty prospect (no name, should be rejected)

**Use Case:** Test validation logic, error handling, and data quality filtering

## Testing Strategy

### Unit Tests Using Fixtures
```python
# Load fixture
with open('tests/fixtures/pff/page_1.html', 'r') as f:
    html = f.read()

# Parse with scraper
soup = BeautifulSoup(html, 'html.parser')
prospects = []
for div in soup.find_all("div", class_="card-prospects-box"):
    prospect = scraper.parse_prospect(div)
    if prospect:
        prospects.append(prospect)

# Assertions
assert len(prospects) == 5  # Only valid prospects
assert all(p['grade'] for p in prospects)  # All have grades
```

### Coverage Areas
- **Parsing:** Name, position, school, class, grade extraction
- **Validation:** Grade range (0-100), position codes, required fields
- **Edge Cases:** Missing fields, invalid data, special characters
- **Filtering:** Invalid records filtered out silently (logged as debug)

## Adding New Fixtures

When adding new fixtures:
1. Update this README
2. Document what scenario each fixture tests
3. Include both happy path and edge cases
4. Keep file sizes reasonable (<50KB)
5. Use realistic PFF.com HTML structure

## Real Page Reference

These fixtures match the PFF.com Draft Big Board structure as of February 2026:
- Container: `<div class="card-prospects-box">`
- Name: `<h3>` or `<h4>` tag
- Fields: `<span class="fieldname">` pattern
- Fields: rank, position, school, class, grade

Note: Actual PFF page uses JavaScript rendering. These fixtures represent the rendered HTML after JavaScript execution.
