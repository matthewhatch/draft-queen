# Scraper QA Report

**Date:** February 12, 2026  
**Tester:** GitHub Copilot  
**Environment:** Local (Linux), Poetry virtualenv, Playwright installed  
**Objective:** Determine why each scraper fails to return real data and identify mock/fake data fallback paths

---

## Summary

| # | Scraper | File | Real Data? | Root Cause |
|---|---------|------|:----------:|------------|
| 1 | PFF Playwright | `data_pipeline/scrapers/pff_scraper_playwright.py` | ❌ | Wrong CSS selectors + silent fallback to hardcoded mock data |
| 2 | PFF Production | `data_pipeline/scrapers/pff_scraper.py` | ❌ | Wrong CSS selectors (`div.card-prospects-box` doesn't exist) |
| 3 | PFF PoC (requests) | `data_pipeline/scrapers/pff_scraper_poc.py` | ❌ | Uses `requests` only — page is JS-rendered, gets empty HTML |
| 4 | PFF Selenium | `data_pipeline/scrapers/pff_scraper_selenium.py` | ❌ | Wrong CSS selectors; generic h3/h4 parsing is fragile |
| 5 | ESPN Injury | `data_pipeline/sources/espn_injury_scraper.py` | ❌ | Wrong URL (trailing slash) + wrong CSS selectors |
| 6 | Yahoo Sports | `data_pipeline/sources/yahoo_sports_scraper.py` | ❌ | Wrong CSS selectors + hardcoded mock fallback in production path |
| 7 | NFL Draft Connector | `data_pipeline/sources/nfl_draft_connector.py` | ❌ | Wrong ESPN API URL (403) + hardcoded `MOCK_PROSPECTS` fallback |

**Verdict: 0 of 7 scrapers return real data. 3 of 7 silently return fake/mock data in their production code paths.**

---

## Detailed Findings

---

### 1. PFF Playwright Scraper — `data_pipeline/scrapers/pff_scraper_playwright.py`

**Test Command:**
```bash
poetry run python -c "
from data_pipeline.scrapers.pff_scraper_playwright import PFFScraperPlaywright
import asyncio
scraper = PFFScraperPlaywright(season=2026, headless=True)
prospects = asyncio.run(scraper.scrape_all_pages(max_pages=1))
print(f'{len(prospects)} prospects')
"
```

**Result:** Returns 3 prospects — **all hardcoded fake data** (Patrick Surtain III, Will Anderson Jr, Jalen Carter — names from the 2023 draft).

**Root Causes:**

1. **Wrong CSS selector:** Searches for `div.card-prospects-box` — this class does not exist on PFF.com. The actual prospect card container is `div.g-card.g-card--border-gray`.

2. **Silent mock data fallback (line 112–150):** When Playwright throws *any* exception (including `TimeoutError`), the `except` block calls `_demo_with_mock_data()` which injects 3 hardcoded fake prospects and returns them as if they were real. The error message actively misleads: *"This is an environment limitation, not a code issue."*

3. **Wrong field selectors:** Searches for `<span class="school">`, `<span class="position">`, etc. The actual PFF structure uses `<div class="g-label">` / `<div class="g-data">` pairs inside `<div class="m-stat">` containers.

**Actual PFF DOM structure (from live page capture):**
```
div.g-card.g-card--border-gray
├── div.m-ranking-header
│   ├── div.m-rank → div.m-rank__value (rank number)
│   ├── div.m-ranking-header__title → a (player name)
│   └── div.m-ranking-header__details
│       └── div.m-stat (×2: Position, Class)
│           ├── div.g-label ("Position" / "Class")
│           └── div.g-data ("QB" / "RS Jr.")
└── div.g-card__content
    ├── div.m-stat-cluster (School, Age, Height, Weight, Speed)
    │   └── div (×5)
    │       ├── div.g-label
    │       └── div.g-data
    └── table.g-table (Season, Snaps, Season Grade)
```

**Mock Data That Should Be Removed:**
- Lines 118–150: `_demo_with_mock_data()` method with hardcoded HTML containing fake prospects

---

### 2. PFF Production Scraper — `data_pipeline/scrapers/pff_scraper.py`

**Test Command:**
```bash
poetry run python -c "
from data_pipeline.scrapers.pff_scraper import PFFScraper
import asyncio
scraper = PFFScraper(season=2026, headless=True, cache_enabled=False)
prospects = asyncio.run(scraper.scrape_all_pages(max_pages=1))
print(f'{len(prospects)} prospects')
"
```

**Result:** Returns 0 prospects. Playwright successfully loads the page (1.4 MB HTML) but finds nothing.

**Root Causes:**

1. **Wrong CSS selector:** Uses `div.card-prospects-box` which doesn't exist. The actual container is `div.g-card`.

2. **Wrong field selectors:** `parse_prospect()` searches for `<h3>/<h4>` tags and `<span class="school/position/grade">` — none of these exist in PFF's actual HTML.

3. **Caches empty results:** After finding 0 prospects, the scraper *caches* the empty result to `data/cache/pff/season_2026_page_1.json`. On subsequent runs with caching enabled, it returns 0 prospects instantly from cache without ever retrying the real page.

4. **Debug HTML dump left in:** Line ~285 writes `page_1.html` to the working directory on every run — a debug artifact that shouldn't be in production.

**Verified from cache file:**
```json
{"timestamp": 1770850470.7, "season": 2026, "page": 1, "prospects": [], "count": 0}
```

---

### 3. PFF PoC Scraper (requests only) — `data_pipeline/scrapers/pff_scraper_poc.py`

**Result:** Returns 0 prospects.

**Root Cause:** Uses `requests.get()` with BeautifulSoup only. PFF's big board is **fully JavaScript-rendered** — the server returns a shell HTML page and all prospect data is loaded client-side via JS. This is acknowledged in the file's own docstring (*"Page IS JavaScript-rendered (NOT server-rendered)"*) but the code was never updated to handle this.

**Additional issue:** Even if the page were server-rendered, the CSS selectors (`div` with `string=re.compile(r"PFF Rank")` and sibling parsing) don't match PFF's actual DOM structure.

**Status:** This file is correctly marked as a PoC, but it should probably be removed or archived since it's confirmed non-functional and the Playwright version supersedes it.

---

### 4. PFF Selenium Scraper — `data_pipeline/scrapers/pff_scraper_selenium.py`

**Result:** Not tested (Selenium/ChromeDriver not installed), but code analysis shows it would fail.

**Root Causes:**

1. **Generic selector:** Uses `EC.presence_of_all_elements_located((By.CSS_SELECTOR, "h3, h4"))` — this matches *any* h3/h4 on the page (nav links, headers, etc.), not just prospect names.

2. **Fragile parsing:** `parse_prospect()` walks parent elements looking for text lines starting with "POSITION", "CLASS", "SCHOOL", etc. PFF uses `<div class="g-label">Position</div>` / `<div class="g-data">QB</div>` pattern, so text-line parsing won't extract clean fields.

3. **Superseded:** The file header itself recommends switching to Playwright. This scraper is obsolete.

---

### 5. ESPN Injury Scraper — `data_pipeline/sources/espn_injury_scraper.py`

**Test Command:**
```bash
poetry run python -c "
from data_pipeline.sources.espn_injury_scraper import ESPNInjuryConnector
c = ESPNInjuryConnector()
injuries = c.fetch_injuries()
print(f'{len(injuries)} injuries')
"
```

**Result:** Returns 0 injuries. HTTP 404 error.

**Root Causes:**

1. **Wrong URL:** `BASE_URL = "https://www.espn.com/nfl/injuries/"` — the trailing slash causes a 404. The correct URL is `https://www.espn.com/nfl/injuries` (no trailing slash). Verified:
   - `https://www.espn.com/nfl/injuries` → 200 OK (870 KB)
   - `https://www.espn.com/nfl/injuries/` → 404

2. **Wrong CSS selectors:** The scraper looks for `tr.injury-row`, `td.player-name`, `td.player-position`, `td.injury-type`, `td.injury-status`, `td.return-date`. None of these exist. ESPN's actual structure uses:
   - `tr.Table__TR` — row class
   - `td.col-name` — player name
   - `td.col-pos` — position
   - `td.col-date` — return date
   - `td.col-stat` → `span.TextStatus` — injury status
   - `td.col-desc` — comment

3. **No team extraction:** ESPN groups injuries by team using a header above each table, not within each row. The scraper expects a `td.player-team` column that doesn't exist.

**ESPN actual row example:**
```html
<tr class="Table__TR Table__TR--sm Table__even">
  <td class="col-name Table__TD"><a href="...">Jonah Williams</a></td>
  <td class="col-pos Table__TD">OT</td>
  <td class="col-date Table__TD">Mar 1</td>
  <td class="col-stat Table__TD"><span class="TextStatus TextStatus--yellow">Questionable</span></td>
  <td class="col-desc Table__TD"></td>
</tr>
```

**Note:** ESPN has 32 tables (one per team) with 569 total injury rows of real data available right now, so this is very fixable.

---

### 6. Yahoo Sports Scraper — `data_pipeline/sources/yahoo_sports_scraper.py`

**Test Command:**
```bash
poetry run python -c "
from data_pipeline.sources.yahoo_sports_scraper import YahooSportsConnector
c = YahooSportsConnector()
prospects = c.fetch_prospects()
print(f'{len(prospects)} prospects')
for p in prospects: print(f'  -> {p}')
"
```

**Result:** Returns 2 prospects — **both hardcoded fake data** ("Test Prospect 1", "Test Prospect 2").

**Root Causes:**

1. **Wrong CSS selectors:** Tries `div.player-card`, `div.player`, `article.player-card`, `tr.player-row`, etc. Yahoo Sports uses obfuscated Tailwind CSS class names (e.g., `_ys_1ejgpwy`, `_ys_u7h8d9`). No semantic class names exist.

2. **Hardcoded mock fallback in production path (lines ~300–315):** When no player elements are found, the `fetch_prospects()` method returns hardcoded mock data **directly in the production code path** — not in a test mock class. This means the scraper *always* silently returns fake data and appears to "work".

3. **Data IS available:** The Yahoo page returns 2.6 MB of server-rendered HTML containing real draft data (Cam Ward, Travis Hunter, Abdul Carter, etc.). The data is in the DOM but can only be extracted using the obfuscated CSS classes or by structural traversal (e.g., find text nodes matching player names, walk up to `<section>` containers).

**Mock Data That Should Be Removed:**
- Lines ~300–315 in `fetch_prospects()`: inline mock data return
- The `MockYahooSportsConnector` class at the bottom is fine (clearly labeled for testing)

---

### 7. NFL Draft Connector — `data_pipeline/sources/nfl_draft_connector.py`

**Test Command:**
```bash
poetry run python -c "
from data_pipeline.sources.nfl_draft_connector import NFLDraftConnector
c = NFLDraftConnector()
prospects = c.fetch_prospects()
print(f'{len(prospects)} prospects')
"
```

**Result:** Returns 10 prospects — **all hardcoded fake data** (Saquon Barkley II, Travis Hunter, Cam Ward, etc. — fabricated records with made-up grades).

**Root Causes:**

1. **Wrong API URL:** `_fetch_from_espn()` calls `https://site.api.espn.com/nfl/site/v2/draft` which returns **403 Forbidden**. This is not a valid ESPN API endpoint.

2. **Hardcoded `MOCK_PROSPECTS` (lines 15–25):** The class has 10 hardcoded fake prospects with invented data. After the ESPN API 403, `fetch_prospects()` falls back to this mock data and logs only a warning.

3. **Fake player data:** The mock data contains names that appear real but with fake stats (e.g., "Saquon Barkley II" — not a real prospect, "Jorrick Jones" — not a real player, grades are arbitrary).

4. **No real data source implemented:** Even the ESPN API parsing code (`_fetch_from_espn`) assumes a response format (`data["draft"]["players"]`) that was never verified against a real endpoint.

**Mock Data That Should Be Removed:**
- Lines 15–25: `MOCK_PROSPECTS` constant with 10 fake entries

---

## Cross-Cutting Issues

### 1. Mock Data in Production Code Paths
Three scrapers silently return fake data when they can't scrape real data, making failures invisible:

| Scraper | Mock Mechanism | Appears to Work? |
|---------|---------------|:----------------:|
| PFF Playwright | `_demo_with_mock_data()` in except handler | ✅ (silently fake) |
| Yahoo Sports | Inline mock return in `fetch_prospects()` | ✅ (silently fake) |
| NFL Draft Connector | `MOCK_PROSPECTS` fallback | ✅ (silently fake) |

**Recommendation:** Remove all mock/fake data from production code. Mock data should only exist in dedicated `Mock*` classes (like `MockESPNInjuryConnector` and `MockYahooSportsConnector` which are properly separated) or in test fixtures.

### 2. Every Scraper Uses Wrong CSS Selectors
All scrapers were written against *assumed* HTML structures rather than the *actual* DOM. Key corrections needed:

| Site | Scraper Expects | Actual Structure |
|------|----------------|-----------------|
| PFF | `div.card-prospects-box`, `span.school` | `div.g-card`, `div.g-label` + `div.g-data` |
| ESPN | `tr.injury-row`, `td.player-name` | `tr.Table__TR`, `td.col-name` |
| Yahoo | `div.player-card`, `h3.player-name` | `section._ys_*` (obfuscated Tailwind classes) |

### 3. Obsolete/Duplicate Scraper Files
There are 4 PFF scraper variants. Only `pff_scraper.py` (production) should remain:

| File | Status | Recommendation |
|------|--------|---------------|
| `pff_scraper.py` | Production (broken) | Fix selectors |
| `pff_scraper_playwright.py` | PoC with mock fallback | Remove or archive |
| `pff_scraper_poc.py` | Confirmed non-functional (requests only) | Remove |
| `pff_scraper_selenium.py` | Superseded by Playwright | Remove |

### 4. PFF Scraper Caches Empty Results
`pff_scraper.py` caches 0-prospect results. After one failed run, all subsequent cached runs return empty silently. The cache file currently contains:
```json
{"timestamp": 1770850470.7, "season": 2026, "page": 1, "prospects": [], "count": 0}
```
**Recommendation:** Never cache empty/zero results. Add a guard like `if len(prospects) > 0` before caching.

---

## What Real Data IS Available (verified)

| Source | URL | Data Available | Rendering |
|--------|-----|---------------|-----------|
| PFF Big Board | `pff.com/draft/big-board?season=2026` | 25 prospects per page (rank, name, position, class, school, height, weight, age, speed, snaps, grade) | JS-rendered, Playwright required, **data confirmed in captured HTML** |
| ESPN Injuries | `espn.com/nfl/injuries` (no trailing slash) | 32 team tables, 569 injury rows (name, position, return date, status, comment) | Server-rendered, `requests` works |
| Yahoo Draft Order | `sports.yahoo.com/nfl/draft/` | Full mock draft with player name, position, college, height, weight, class, age | Server-rendered, `requests` works, but uses obfuscated CSS classes |

---

## Priority Fix Order

1. **🔴 PFF Production Scraper** (`pff_scraper.py`) — Fix CSS selectors to match real DOM. Real data confirmed available in captured HTML. This is the primary data source.
2. **🔴 Remove mock data from production paths** — All 3 scrapers with inline mock fallbacks.
3. **🟠 ESPN Injury Scraper** — Fix URL (remove trailing slash) and update CSS selectors. Data is server-rendered and readily available.
4. **🟡 Yahoo Sports Scraper** — Challenging due to obfuscated CSS. May need structural/text-based parsing or an alternative approach.
5. **🟡 NFL Draft Connector** — Needs a valid API endpoint or should be replaced with a scraper approach.
6. **⚪ Cleanup** — Remove `pff_scraper_poc.py`, `pff_scraper_selenium.py`, and `pff_scraper_playwright.py` (PoC).

---

## Appendix A: Complete PFF DOM Selector Map

**Source:** Captured live HTML (`page_1.html`, 1.4 MB, saved in project root as debug artifact by `pff_scraper.py` line ~285)

This file contains the real PFF page HTML with 25 prospect cards. It can be used as a test fixture.

### Card Container

```
div.g-card.g-card--border-gray
```

### Header Section (`div.m-ranking-header`)

| Field | Selector | Example Value |
|-------|----------|---------------|
| Rank | `div.m-ranking-header__rank-container` → `div.m-rank__value` | `1` |
| Name | `div.m-ranking-header__main-details` → `h3.m-ranking-header__title` → `a` | `Fernando Mendoza` |
| Position | `div.m-ranking-header__details` → `div.m-stat:nth-child(1)` → `div.g-data` | `QB` |
| Class | `div.m-ranking-header__details` → `div.m-stat:nth-child(2)` → `div.g-data` | `RS Jr.` |

### Body Section (`div.g-card__content`)

Layout: `div.g-grid` with two columns:

**Left Column** (`div.g-span-12.g-span-6-lg.g-span-8-xl` → `div.m-content-section` → `div.m-stat-cluster`)

Each stat is a `div` child of the cluster containing:
```html
<div class="g-label g-mb-1">School</div>
<div class="g-data">
  <svg class="g-icon g-icon--team">...</svg>
  <span>Indiana</span>
</div>
```

| Field | Pattern | Example |
|-------|---------|---------|
| School | `div.g-label` text = "School" → sibling `div.g-data` → `span` | `Indiana` |
| Age | `div.g-label` text = "Age" → sibling `div.g-data` | `—` (may be missing) |
| Height | `div.g-label` text = "Height" → sibling `div.g-data` | `6' 5"` |
| Weight | `div.g-label` text = "Weight" → sibling `div.g-data` | `225` |
| Speed | `div.g-label` text = "Speed" → sibling `div.g-data` | `—` (may be missing) |

**Extraction strategy:** Iterate `div.m-stat-cluster > div` children. Each child contains a `div.g-label` and `div.g-data`. Use the label text to identify the field.

**Right Column** (`div.g-span-12.g-span-6-lg.g-span-4-xl` → `table.g-table`)

Grade table with 3 columns:

| Column | Header `<th>` | Cell selector | Example |
|--------|--------------|---------------|---------|
| Season | `Season` | `td[data-cell-label="Season"]` | `2025` |
| Snaps | `Snaps` | `td[data-cell-label="Snaps"]` (class `u-text-right`) | `976` |
| Grade | `Season Grade` | `td[data-cell-label="Season Grade"]` → `div.kyber-grade-badge` → `div.kyber-grade-badge__info-text` | `91.6` |

**Grade badge structure:**
```html
<td data-cell-label="Season Grade">
  <div class="d-flex flex-row align-items-center justify-content-start">
    <div class="kyber-grade-badge">
      <div class="kyber-grade-badge__info">
        <div class="kyber-grade-badge__info-badge" style="background: rgb(2, 127, 164);"></div>
        <div class="kyber-grade-badge__info-bg" style="background: rgb(2, 127, 164);"></div>
        <div class="kyber-grade-badge__info-text">91.6</div>  <!-- ← GRADE VALUE -->
      </div>
    </div>
    <span class="g-ml-2 g-py-1 g-pill"><span>9<sup>th</sup> / 315</span> QB</span>
  </span>
</td>
```

**⚠️ Paywalled rows:** Only the most recent season row has visible snaps/grade. Older seasons show a lock icon (`button.pff-plus-badge` → `svg.kyber-svg-lock-solid`). The scraper should only extract the first `<tbody> <tr>` data.

### Verified Prospect Data (first 3 from `page_1.html`)

| Rank | Name | Position | Class | School | Height | Weight | Snaps | Grade |
|------|------|----------|-------|--------|--------|--------|-------|-------|
| 1 | Fernando Mendoza | QB | RS Jr. | Indiana | 6' 5" | 225 | 976 | 91.6 |
| 2 | Rueben Bain Jr. | EDGE | — | — | — | — | — | — |
| 3 | Arvell Reese | LB | — | — | — | — | — | — |

---

## Appendix B: Complete ESPN Injury DOM Selector Map

**Source:** Live request to `https://www.espn.com/nfl/injuries` (no trailing slash), verified June 2025

### Page Structure

```
div.ResponsiveTable (×32, one per team)
├── div.Table__Title
│   └── div.flex.flex-row → text = team name (e.g., "Arizona Cardinals")
└── div.flex
    └── div.Table__ScrollerWrapper
        └── table.Table
            ├── thead
            │   └── tr → th.Table__TH (×5: NAME, POS, EST. RETURN DATE, STATUS, COMMENT)
            └── tbody
                └── tr.Table__TR.Table__TR--sm (×N per team)
                    ├── td.col-name.Table__TD → a[href] (player name + link)
                    ├── td.col-pos.Table__TD (position text)
                    ├── td.col-date.Table__TD (return date text)
                    ├── td.col-stat.Table__TD → span.TextStatus (status text)
                    └── td.col-desc.Table__TD (comment text)
```

### Team Name Extraction

The team name is **NOT** in each row — it's in a header **above** each team's table:

```python
wrapper = soup.find_all('div', class_='ResponsiveTable')  # 32 wrappers
for w in wrapper:
    team_name = w.find(class_='Table__Title').get_text(strip=True)
    rows = w.find_all('tr', class_='Table__TR')
    for row in rows:
        # Each row inherits team_name from its wrapper
```

### Status Classes (for color-coded status)

| Status | CSS Class | Example |
|--------|-----------|---------|
| Questionable | `TextStatus--yellow` | `<span class="TextStatus TextStatus--yellow">Questionable</span>` |
| Out | `TextStatus--red` | `<span class="TextStatus TextStatus--red">Out</span>` |
| Injured Reserve | `TextStatus--red` | `<span class="TextStatus TextStatus--red">Injured Reserve</span>` |

### Verified Data (first team)

**Arizona Cardinals** (25 rows):

| Name | POS | EST. RETURN DATE | STATUS |
|------|-----|------------------|--------|
| Jonah Williams | OT | Mar 1 | Questionable |
| Mack Wilson | — | — | — |

Total across all 32 teams: **569 injury rows** available.

---

## Appendix C: Complete Yahoo Sports DOM Selector Map

**Source:** Live request to `https://sports.yahoo.com/nfl/draft/`, verified June 2025

### Key Challenge: Obfuscated CSS Classes

Yahoo uses Tailwind-generated CSS class names (e.g., `_ys_1ejgpwy`, `_ys_u7h8d9`). These are **NOT stable** — they may change on any Yahoo deployment. A robust scraper must use **structural/text-based parsing**, not CSS class selectors.

### Page Structure

```
ul._ys_6oxte4 (prospect list — 257 items)
└── li (one per prospect)
    └── section._ys_1vv413w (prospect card)
        ├── div._ys_1ceho82 (header: pick + player info)
        │   └── div._ys_g5dbmv
        │       ├── div._ys_18jhnv0 (pick info)
        │       │   ├── span._ys_1pbxhfo._ys_1dnwiv5 → "RD1, PK2" (short form)
        │       │   ├── span._ys_1pbxhfo._ys_52mm7a → "Round 1, Pick 2" (long form)
        │       │   └── span._ys_zbzk5p → "(from Browns)" (trade note, optional)
        │       ├── img._ys_1bamtqw (player headshot)
        │       └── div._ys_u7h8d9 (name + position + school)
        │           ├── div._ys_1ejgpwy → "Travis Hunter" (player name)
        │           └── ul._ys_jprp27
        │               ├── li._ys_jkbrcc → "CB" (position)
        │               └── li._ys_jkbrcc → "Colorado" (school)
        └── div._ys_18pih1k (expandable detail section)
            └── div._ys_1vv4mez
                └── div (measurables + analysis)
                    ├── span._ys_1j0j0k → "6' 1"" (value)
                    ├── span._ys_blfih4 → "Height" (label)
                    ├── span._ys_1j0j0k → "185" (value)
                    ├── span._ys_blfih4 → "Weight" (label)
                    ├── span → "JR" (class value, no consistent class)
                    ├── span._ys_blfih4 → "Class" (label)
                    ├── span._ys_1j0j0k → "21" (value)
                    ├── span._ys_blfih4 → "Age" (label)
                    ├── h4._ys_uns4xu → "Draft Grade: B+" (Yahoo's grade)
                    ├── span._ys_uns4xu → "The Jaguars have made the first bold..." (analysis text)
                    ├── h4._ys_uns4xu → "Player Comparisons"
                    ├── h4._ys_uns4xu → "Attributes"
                    └── div (×N) → "💨 Speed Demon", "🔧 Jack of all trades", etc.
```

### Recommended Extraction Strategy (CSS-class-independent)

Since Yahoo's classes are obfuscated and unstable, the scraper should use **structural navigation**:

```python
# 1. Find the prospect list  
prospect_list = soup.find('ul', recursive=True)  # Find the <ul> containing <li> with <section> children

# 2. For each prospect
for li in prospect_list.find_all('li', recursive=False):
    section = li.find('section')
    if not section:
        continue
    
    # 3. Extract from stripped_strings pattern
    texts = list(section.stripped_strings)
    # texts pattern: ["RD1, PK2", "Round 1, Pick 2", "(from Browns)", "Travis Hunter", "CB", "Colorado", ...]
    
    # 4. Or use structural position:
    #    - Player name: section's first div._ys_1ejgpwy (deepest div in header containing just name text)
    #    - Position + School: the <ul> inside the name's parent div → <li> children (1st = position, 2nd = school)
    #    - Measurables: find all <span> pairs in detail section where label span has known text
```

### Verified Data (first 3 from live page)

| Pick | Name | Position | School | Height | Weight | Class | Age | Draft Grade |
|------|------|----------|--------|--------|--------|-------|-----|-------------|
| RD1, PK1 | Cam Ward | QB | Miami (FL) | 6' 2" | 223 | SR | 22 | — |
| RD1, PK2 | Travis Hunter | CB | Colorado | 6' 1" | 185 | JR | 21 | B+ |
| RD1, PK3 | Abdul Carter | EDGE | — | — | — | — | — | — |

Total prospects in list: **257**

---

## Appendix D: Unit Test Dependencies

**File:** `tests/unit/test_pff_scraper.py` (376 lines)

### Tests That Will Break When Selectors Are Fixed

The unit tests hardcode the **wrong** CSS selectors. When the production scraper is updated to use `div.g-card` instead of `div.card-prospects-box`, these tests must be updated simultaneously:

| Test | Line | Issue |
|------|------|-------|
| `test_parse_prospect_valid` | ~202 | Uses `<div class="card-prospects-box">` with `<h3>`, `<span class="school">`, etc. |
| `test_parse_prospect_missing_name` | ~222 | Same wrong structure |
| `test_parse_prospect_with_missing_fields` | ~237 | Same wrong structure |
| `test_parse_fixture_page1` | ~252 | Searches for `div.card-prospects-box` + expects fixture data with name "Patrick Surtain III" |
| `test_scraper_workflow` (integration) | ~345 | Same wrong selectors |

### Fixture Files Expected But Missing

The tests reference fixture files that don't exist:
- `tests/fixtures/pff/page_1.html` — **does not exist**
- `tests/fixtures/pff/page_2.html` — **does not exist**

**Recommendation:** Copy `page_1.html` (the debug artifact in project root, 1.4 MB of real PFF HTML) to `tests/fixtures/pff/page_1.html` and use it as the fixture. Update `test_parse_fixture_page1` to search for `div.g-card` and expect real prospect names (Fernando Mendoza, Rueben Bain Jr., etc.) instead of "Patrick Surtain III".

### Validator Tests (OK — No Changes Needed)

These tests are independent of CSS selectors and will continue to work:
- `TestGradeValidator` — validates grade value ranges
- `TestPositionValidator` — validates position codes
- `TestProspectValidator` — validates prospect dictionaries
- `TestProspectBatchValidator` — validates batch filtering
- `TestPFFProspectValidator` — validates embedded validator

---

## Appendix E: Debug Artifacts to Clean Up

| File | Size | Origin | Action |
|------|------|--------|--------|
| `page_1.html` (project root) | 1.4 MB | `pff_scraper.py` line ~285 debug dump | Move to `tests/fixtures/pff/page_1.html`, remove debug dump code |
| `data/cache/pff/season_2026_page_1.json` | ~100 B | Cached empty results | Delete (contains `"prospects": [], "count": 0`) |
| `debug_output.txt` (project root) | — | Debug artifact | Delete |
| `debug_yahoo.py` (project root) | — | Debug script | Delete or move to `examples/` |
