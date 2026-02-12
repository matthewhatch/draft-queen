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
