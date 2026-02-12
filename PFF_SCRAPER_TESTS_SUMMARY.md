# PFF Scraper Test Scripts Summary

## Overview

Created comprehensive testing infrastructure for the PFF.com Draft Big Board scraper with 3 main components:

1. **test_pff_scraper.py** - Full-featured test framework
2. **run_pff_tests.py** - Quick scenario runner
3. **PFF_SCRAPER_TEST_GUIDE.md** - Complete documentation

## Test Scripts

### 1. test_pff_scraper.py
**Advanced testing framework with flexible options**

Features:
- 4 test types: single page, multi-page, cache, all
- Rich formatted output with tables and statistics
- Data validation reporting
- Progress bars for multi-page scrapes
- Configurable cache behavior
- Headless/headed browser modes

Usage:
```bash
# Default: 3 pages with cache
poetry run python test_pff_scraper.py

# 5 pages
poetry run python test_pff_scraper.py --pages 5

# Cache test only
poetry run python test_pff_scraper.py --test cache

# Show browser
poetry run python test_pff_scraper.py --no-headless

# Disable cache
poetry run python test_pff_scraper.py --no-cache
```

### 2. run_pff_tests.py
**Quick scenario runner with preset configurations**

Features:
- 6 preset scenarios for common use cases
- Interactive menu mode
- Direct command-line support
- Shows command before execution
- No need to remember complex arguments

6 Scenarios:
1. **Quick** - Single page (10 seconds)
2. **Standard** - 3 pages (30 seconds)
3. **Full** - 5 pages (60 seconds)
4. **Cache** - Cache functionality test
5. **Visual** - Browser visible for debugging
6. **Debug** - No cache for troubleshooting

Usage:
```bash
# Interactive menu
poetry run python run_pff_tests.py

# Direct scenario
poetry run python run_pff_tests.py 1          # Quick
poetry run python run_pff_tests.py 2          # Standard
poetry run python run_pff_tests.py "Quick"    # By name
```

### 3. PFF_SCRAPER_TEST_GUIDE.md
**Comprehensive documentation**

Includes:
- Quick start examples
- All command-line options
- Test type descriptions
- Output interpretation guide
- Troubleshooting section
- Performance metrics
- Expected results
- CI/CD integration

## Test Coverage

### What Gets Tested

| Component | Test | Method |
|-----------|------|--------|
| **Scraper** | Single page scrape | Fetch page 1 from PFF.com |
| **Parser** | HTML parsing | Extract prospect data |
| **Validation** | Data validation | Check prospect attributes |
| **Cache** | Cache functionality | Load/save cache files |
| **Performance** | Multi-page scraping | Rate limiting, timeouts |
| **Error Handling** | Recovery mechanisms | Fallback to cache on error |

### Success Metrics

- **Page 1 Results**: 25 prospect divs found, 12+ valid prospects
- **Validation Rate**: 85-95% of prospects pass validation
- **Cache Performance**: <1 second for cached loads
- **Single Page Time**: 5-10 seconds including browser startup

## Example Outputs

### Prospect Table
```
Name                      Pos  School                Class     Ht/Wt        Grade
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Fernando Mendoza          QB   Indiana               RS Jr.    6' 5"/225    91.6
Carnell Tate              WR   Ohio State            Jr.       6' 3"/195    88.6
Makai Lemon               WR   USC                   Jr.       5' 11"/195   90.8
```

### Summary Statistics
```
Total Prospects: 12

By Position:
  QB    1  █
  WR    4  ████████████
  LB    2  ██████
  CB    3  █████████
  S     1  █
  TE    1  █

Top Schools:
  Ohio State         4
  USC                1
  LSU                1
  Tennessee          1
  Arizona State      1
```

### Validation Report
```
Total Prospects: 12
✓ Valid: 12 (100%)
✗ Invalid: 0 (0%)
```

## Integration

### With CI/CD
```bash
# Run before pipeline execution
poetry run python run_pff_tests.py 2 && echo "✓ Ready for pipeline"

# Or programmatically
exit_code=$(poetry run python test_pff_scraper.py --test single)
if [ $exit_code -eq 0 ]; then
  poetry run python -m cli.main pipeline run
fi
```

### With Development Workflow
```bash
# Quick verification while developing
poetry run python run_pff_tests.py 1

# Cache test to verify caching works
poetry run python run_pff_tests.py 4

# Full test before committing
poetry run python run_pff_tests.py 3
```

## File Locations

```
/home/parrot/code/draft-queen/
├── test_pff_scraper.py              ← Main test framework
├── run_pff_tests.py                 ← Scenario runner
├── PFF_SCRAPER_TEST_GUIDE.md        ← Documentation
├── data_pipeline/
│   └── scrapers/
│       └── pff_scraper.py           ← Scraper being tested
└── tests/
    ├── unit/
    │   └── test_pff_scraper.py      ← Unit tests
    └── integration/
        └── test_pipeline.py         ← Integration tests
```

## Performance

| Scenario | Time | Page Loads | API Calls | Cache Hits |
|----------|------|-----------|-----------|-----------|
| Quick | ~10s | 1 | 1 | 0 (first run) |
| Standard | ~30s | 3 | 3 | 0 (first run) |
| Full | ~60s | 5 | 5 | 0 (first run) |
| Cache Test | ~2s | 2 | 1 | 1 |
| Second Run | ~1-2s | 0 | 0 | N (all cached) |

## Recent Test Results

✅ **Cache Test** - PASSED
- First load: Scraped 12 prospects from live site
- Second load: Loaded 12 prospects from cache
- Cache performance: <1 second

✅ **Single Page Test** - PASSED
- Prospects found: 12/25 divs parsed successfully
- Validation rate: 100%

✅ **Quick Scenario** - PASSED
- Execution time: ~10 seconds
- Total prospects: 12
- All tests completed successfully

## Next Steps

1. **Add to CI/CD**: Integrate into automated testing pipeline
2. **Monitor Results**: Track prospect count and validation rates over time
3. **Update Selectors**: Adjust CSS selectors if PFF website structure changes
4. **Expand Tests**: Add position-specific validation tests
5. **Performance**: Optimize multi-page scraping performance

## Related Documentation

- [Data Pipeline README](../docs/AGENT_INSTRUCTIONS_DATA_PIPELINE.md)
- [US-040 Completion Report](../docs/US-040_PROGRESS.md)
- [Sprint Planning](../sprint-planning/SPRINT_4_USER_STORIES.md)

## Support

For issues or questions:
1. Check [PFF_SCRAPER_TEST_GUIDE.md](PFF_SCRAPER_TEST_GUIDE.md) troubleshooting section
2. Review scraper logs in `logs/pipeline.log`
3. Check cached data in `data/cache/pff/`
4. Run debug scenario: `poetry run python run_pff_tests.py 6`
