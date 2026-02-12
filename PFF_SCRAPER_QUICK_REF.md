# PFF Scraper Test Quick Reference

## 🚀 Quick Start (30 seconds)

```bash
# Run quick test
poetry run python run_pff_tests.py 1

# Or run standard test
poetry run python test_pff_scraper.py
```

## 📋 Available Commands

| Command | Purpose | Time |
|---------|---------|------|
| `poetry run python run_pff_tests.py 1` | Quick single page | 10s |
| `poetry run python run_pff_tests.py 2` | Standard 3 pages | 30s |
| `poetry run python run_pff_tests.py 3` | Full 5 pages | 60s |
| `poetry run python run_pff_tests.py 4` | Test cache only | 2s |
| `poetry run python run_pff_tests.py 5` | Visual (see browser) | 10s |
| `poetry run python run_pff_tests.py 6` | Debug (no cache) | 10s |

## 🎯 Choose Your Script

### For Quick Testing
```bash
poetry run python run_pff_tests.py
# Interactive menu, choose scenario
```

### For Advanced Configuration
```bash
poetry run python test_pff_scraper.py --pages 5 --test multi
```

### For Integration
```bash
poetry run python test_pff_scraper.py --test cache
# Exit code 0 = success, cache working
```

## 📊 What Each Test Shows

| Metric | Scenario | Result |
|--------|----------|--------|
| **Prospects Found** | Any | Usually 12-25 per page |
| **Validation Rate** | Any | Typically 85-100% |
| **Cache Hit** | Cache test | Should be ~1 second |
| **Position Distribution** | Any | QB, WR, RB, etc. |
| **Top Schools** | Multi-page | Alabama, Ohio State, etc. |

## 🔍 Expected Output Sample

```
✓ Total Prospects: 12

📊 By Position:
  QB    1 █
  WR    4 ████████████
  CB    3 █████████
  LB    2 ██████

🏫 Top Schools:
  Ohio State         4
  USC                1

⭐ Grade Statistics:
  Average: 87.2
  Max: 91.6
  Min: 70.4
```

## ⚠️ Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| No prospects found | Run with `--no-headless` to see browser |
| Timeout | May take longer, wait 2-3 minutes |
| Cache errors | Try `--no-cache` option |
| Browser won't start | Run `playwright install chromium` |

## 📖 Full Documentation

- **Complete Guide**: [PFF_SCRAPER_TEST_GUIDE.md](PFF_SCRAPER_TEST_GUIDE.md)
- **Summary**: [PFF_SCRAPER_TESTS_SUMMARY.md](PFF_SCRAPER_TESTS_SUMMARY.md)
- **Code**: [test_pff_scraper.py](test_pff_scraper.py)
- **Runner**: [run_pff_tests.py](run_pff_tests.py)

## 🎓 Examples

### Verify Scraper is Working
```bash
poetry run python run_pff_tests.py 1
```

### Test with 10 Pages
```bash
poetry run python test_pff_scraper.py --pages 10
```

### Debug Cache Issues
```bash
poetry run python test_pff_scraper.py --test cache --no-cache
```

### Pre-Pipeline Check
```bash
poetry run python run_pff_tests.py 2 && echo "✓ Ready!"
```

## 💡 Pro Tips

1. **First run takes longer** - Browser startup + page load
2. **Subsequent runs are faster** - Uses cache automatically
3. **Watch the browser** - Use `--no-headless` to see what it's scraping
4. **Check validation** - Look for % valid in summary
5. **Grade filtering** - Check average grades are realistic (70-92 range)

## ✅ Success Checklist

- [ ] Prospects found: 10+ per page
- [ ] Validation rate: >80%
- [ ] Cache working: <1s second load
- [ ] Positions detected: QB, WR, RB, etc.
- [ ] Schools detected: Alabama, Ohio State, etc.

## 🔗 Related Commands

```bash
# Run data pipeline
poetry run python -m cli.main pipeline run

# View pipeline logs
poetry run python -m cli.main pipeline logs

# Check database
poetry run python -c "from backend.database import db; print(db.SessionLocal())"

# Run all unit tests
poetry run pytest tests/unit/test_pff_scraper.py
```

## 📞 Support

1. Check troubleshooting section in full guide
2. Enable debug logging: `--test single --no-cache`
3. Run visual test: `run_pff_tests.py 5`
4. Check logs: `logs/pipeline.log`
