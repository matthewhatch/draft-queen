# PFF Scraper Test Script Guide

## Overview

The `test_pff_scraper.py` script provides comprehensive testing for the PFF.com Draft Big Board scraper with multiple test scenarios and rich terminal output.

## Quick Start

```bash
# Basic test (3 pages, with cache)
poetry run python test_pff_scraper.py

# Scrape 5 pages
poetry run python test_pff_scraper.py --pages 5

# Test only cache functionality
poetry run python test_pff_scraper.py --test cache

# Show browser window during scraping
poetry run python test_pff_scraper.py --no-headless
```

## Command-Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--pages N` | 3 | Number of pages to scrape |
| `--no-cache` | N/A | Disable cache (always fetch fresh) |
| `--headless` | True | Run browser in headless mode |
| `--no-headless` | N/A | Show browser window |
| `--test TYPE` | all | Test type: single, multi, cache, or all |
| `-h, --help` | N/A | Show help message |

## Test Types

### Single Page Test (`--test single`)
- Scrapes page 1 only
- Displays prospects in table format
- Useful for quick verification

```bash
poetry run python test_pff_scraper.py --test single
```

### Multi-Page Test (`--test multi`)
- Scrapes multiple pages (default 3)
- Shows progress bar
- Collects all prospects with summary

```bash
poetry run python test_pff_scraper.py --test multi --pages 5
```

### Cache Test (`--test cache`)
- Tests cache functionality
- Loads page twice (first hits scraper, second hits cache)
- Verifies cache is working correctly

```bash
poetry run python test_pff_scraper.py --test cache
```

### All Tests (`--test all`)
- Runs all three test types sequentially
- Default if no test type specified
- Most comprehensive option

```bash
poetry run python test_pff_scraper.py --test all --pages 3
```

## Output Sections

### 1. Test Results
- Shows prospects found during each test
- Displays data in formatted tables
- Lists sample prospects with details

### 2. Scrape Summary
- **Total Prospects**: Count of all scraped prospects
- **By Position**: Breakdown by player position (QB, WR, RB, etc.)
- **Top Schools**: Top 15 colleges by prospect count
- **Grade Statistics**: Average, max, and min prospect grades

### 3. Data Validation Report
- **Total**: All prospects scraped
- **Valid**: Prospects passing validation checks
- **Invalid**: Prospects with issues
- **Issues Found**: Details of any validation failures

## Example Usage Scenarios

### Scenario 1: Quick Verification
```bash
poetry run python test_pff_scraper.py --test single
# Tests single page scraping in ~10 seconds
```

### Scenario 2: Full Scrape with Caching
```bash
poetry run python test_pff_scraper.py --pages 10
# Scrapes 10 pages with caching, rate limiting
# Takes ~1-2 minutes depending on page load times
```

### Scenario 3: Debug Cache Issues
```bash
poetry run python test_pff_scraper.py --test cache --no-cache
# First load: scrapes from live site
# Second load: also scrapes (cache disabled)
# Shows cache behavior
```

### Scenario 4: Visual Inspection
```bash
poetry run python test_pff_scraper.py --no-headless --test single
# Opens browser window so you can see what's being scraped
# Useful for debugging selector issues
```

### Scenario 5: Large-Scale Test
```bash
poetry run python test_pff_scraper.py --pages 20 --test multi
# Scrapes first 20 pages with all prospects
# Generates comprehensive statistics
```

## Understanding the Output

### Prospect Table
```
Name                    │ Pos │ School              │ Class │ Ht/Wt       │ Grade
━━━━━━━━━━━━━━━━━━━━━━━╋━━━━╋━━━━━━━━━━━━━━━━━━━━╋━━━━━━╋━━━━━━━━━━━━╋━━━━━
Will Anderson Jr.       │ DL  │ Alabama             │ JR    │ 6'4"/243    │ 87.3
Bryce Young             │ QB  │ Alabama             │ SO    │ 6'0"/200    │ 84.1
```

### Summary Section
```
SCRAPE SUMMARY
✓ Total Prospects: 125

📊 By Position:
QB     10   ██
WR     24   ████████████
RB     15   ███████
...
```

### Validation Report
```
DATA VALIDATION REPORT
Total Prospects: 125
✓ Valid: 123 (98.4%)
✗ Invalid: 2 (1.6%)
```

## Troubleshooting

### Issue: No prospects found
- **Cause**: PFF website may have changed structure
- **Solution**: Run with `--no-headless` to see what's on page
- **Check**: Verify CSS selectors in PFF scraper code

### Issue: Slow performance
- **Cause**: Network latency or page load times
- **Solution**: Increase timeout in `PFFScraperConfig.REQUEST_TIMEOUT`
- **Alternative**: Use cached data with subsequent runs

### Issue: Cache not working
- **Cause**: Cache disabled or directory permissions
- **Solution**: Run `--no-cache` to disable caching for debugging
- **Check**: Verify `data/cache/pff/` directory exists and is writable

### Issue: Browser won't start
- **Cause**: Chromium not installed
- **Solution**: Run `poetry install` to ensure Playwright dependencies
- **Alternative**: Install Chromium: `playwright install chromium`

## Expected Results

### Typical Output (3 pages, with cache)
- **Page 1**: 25 prospects found, 12-20 valid
- **Page 2**: Similar count (cached if run twice)
- **Page 3**: Similar count
- **Total**: 50-100 prospects across pages
- **Validation Rate**: 85-95% valid

### Cache Behavior
```
First run:  Scrapes from live site → Caches results
Second run: Uses cache → 100% cache hit (0 API calls)
```

## Performance Metrics

| Operation | Time | Notes |
|-----------|------|-------|
| Single Page Scrape | 5-10s | Browser startup + page load + parse |
| Cache Load | <1s | Instant retrieval from disk |
| Multi-Page (3 pages) | 20-30s | Includes 2+ second rate limiting delays |
| Data Validation | <1s | Quick pass/fail checks |

## Integration with Pipeline

This test script is part of the data pipeline testing framework:
- Used for US-040 (PFF scraper implementation)
- Validates data before pipeline execution
- Supports ongoing scraper maintenance

Run as part of CI/CD or pre-pipeline checks:
```bash
poetry run python test_pff_scraper.py --pages 3 && echo "✓ Ready for pipeline"
```

## Related Files

- [data_pipeline/scrapers/pff_scraper.py](data_pipeline/scrapers/pff_scraper.py) - Main scraper implementation
- [tests/unit/test_pff_scraper.py](tests/unit/test_pff_scraper.py) - Unit tests
- [test_pff_scraper.py](test_pff_scraper.py) - This test script
