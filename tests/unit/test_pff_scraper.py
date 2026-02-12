"""
Comprehensive unit tests for PFF scraper and validators

Test coverage:
- HTML parsing (with fixtures)
- Prospect extraction
- Data validation
- Error handling
- Cache operations
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from bs4 import BeautifulSoup

from data_pipeline.scrapers.pff_scraper import PFFScraper, PFFProspectValidator
from data_pipeline.validators.pff_validator import (
    GradeValidator,
    PositionValidator,
    ProspectValidator,
    ProspectBatchValidator,
)


class TestGradeValidator:
    """Tests for grade validation"""

    def test_valid_grades(self):
        """Test valid grade values"""
        valid_grades = ["0", "50", "100", "9.8", "0.1"]
        for grade in valid_grades:
            is_valid, error = GradeValidator.validate_grade(grade)
            assert is_valid, f"Grade {grade} should be valid: {error}"

    def test_invalid_grades(self):
        """Test invalid grade values"""
        invalid_grades = ["105", "-1", "abc", "150.5"]
        for grade in invalid_grades:
            is_valid, error = GradeValidator.validate_grade(grade)
            assert not is_valid, f"Grade {grade} should be invalid"

    def test_empty_grades(self):
        """Test empty/missing grades are acceptable"""
        for grade in [None, ""]:
            is_valid, error = GradeValidator.validate_grade(grade)
            assert is_valid, f"Empty grade {grade!r} should be acceptable"

    def test_normalize_grade(self):
        """Test grade normalization"""
        assert GradeValidator.normalize_grade("9.8") == 9.8
        assert GradeValidator.normalize_grade("100") == 100.0
        assert GradeValidator.normalize_grade(None) is None
        assert GradeValidator.normalize_grade("invalid") is None


class TestPositionValidator:
    """Tests for position validation"""

    def test_valid_positions(self):
        """Test valid position codes"""
        valid_positions = ["CB", "QB", "EDGE", "LB", "WR", "RB", "DT"]
        for pos in valid_positions:
            is_valid, error = PositionValidator.validate_position(pos)
            assert is_valid, f"Position {pos} should be valid: {error}"

    def test_invalid_positions(self):
        """Test invalid position codes"""
        invalid_positions = ["XYZ", "INVALID", "FOO", "123"]
        for pos in invalid_positions:
            is_valid, error = PositionValidator.validate_position(pos)
            assert not is_valid, f"Position {pos} should be invalid"

    def test_case_insensitive(self):
        """Test position validation is case-insensitive"""
        is_valid, _ = PositionValidator.validate_position("cb")
        assert is_valid

    def test_normalize_position(self):
        """Test position normalization"""
        assert PositionValidator.normalize_position("cb") == "CB"
        assert PositionValidator.normalize_position("EDGE") == "EDGE"
        assert PositionValidator.normalize_position("invalid") is None


class TestProspectValidator:
    """Tests for complete prospect validation"""

    def test_valid_prospect(self):
        """Test valid prospect record"""
        prospect = {
            "name": "Patrick Surtain III",
            "position": "CB",
            "grade": "9.8",
            "school": "Miami (FL)",
        }
        is_valid, errors = ProspectValidator.validate_prospect(prospect)
        assert is_valid, f"Valid prospect failed: {errors}"

    def test_missing_name(self):
        """Test prospect without name"""
        prospect = {"position": "CB", "grade": "9.8"}
        is_valid, errors = ProspectValidator.validate_prospect(prospect)
        assert not is_valid
        assert any("name" in e for e in errors)

    def test_invalid_grade_in_prospect(self):
        """Test prospect with invalid grade"""
        prospect = {
            "name": "Test",
            "position": "CB",
            "grade": "105",
        }
        is_valid, errors = ProspectValidator.validate_prospect(prospect)
        assert not is_valid
        assert any("grade" in e for e in errors)

    def test_invalid_position_in_prospect(self):
        """Test prospect with invalid position"""
        prospect = {
            "name": "Test",
            "position": "INVALID",
            "grade": "9.8",
        }
        is_valid, errors = ProspectValidator.validate_prospect(prospect)
        assert not is_valid
        assert any("position" in e for e in errors)

    def test_normalize_prospect(self):
        """Test prospect normalization"""
        raw = {
            "name": "  Test  ",
            "position": "cb",
            "grade": "9.8",
            "school": "  Miami (FL)  ",
            "class": "Junior",
        }
        normalized = ProspectValidator.normalize_prospect(raw)

        assert normalized["name"] == "Test"
        assert normalized["position"] == "CB"
        assert normalized["grade"] == 9.8
        assert normalized["school"] == "Miami (FL)"


class TestProspectBatchValidator:
    """Tests for batch validation"""

    def test_batch_validation(self):
        """Test batch validation"""
        prospects = [
            {"name": "Test 1", "position": "CB", "grade": "9.8"},
            {"name": "Test 2", "position": "INVALID", "grade": "9.5"},
            {"name": "", "position": "WR", "grade": "8.9"},
            {"name": "Test 4", "position": "EDGE", "grade": "9.1"},
        ]

        valid, invalid = ProspectBatchValidator.filter_and_normalize(prospects)

        assert len(valid) == 2
        assert len(invalid) == 2
        assert all("name" in p for p in valid)


class TestPFFScraper:
    """Tests for PFF scraper with fixtures"""

    @pytest.fixture
    def scraper(self):
        """Create scraper instance"""
        return PFFScraper(season=2026, cache_enabled=False)

    @pytest.fixture
    def fixture_html_page1(self):
        """Load page 1 fixture"""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "pff" / "page_1.html"
        if fixture_path.exists():
            with open(fixture_path, "r") as f:
                return f.read()
        return None

    @pytest.fixture
    def fixture_html_page2(self):
        """Load page 2 fixture"""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "pff" / "page_2.html"
        if fixture_path.exists():
            with open(fixture_path, "r") as f:
                return f.read()
        return None

    def test_scraper_initialization(self, scraper):
        """Test scraper initialization"""
        assert scraper.season == 2026
        assert scraper.headless is True
        assert scraper.prospects == []

    def test_parse_prospect_valid(self, scraper):
        """Test parsing valid prospect"""
        html = """
        <div class="card-prospects-box">
            <h3>Patrick Surtain III</h3>
            <span class="position">CB</span>
            <span class="school">Miami (FL)</span>
            <span class="grade">9.8</span>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        div = soup.find("div", class_="card-prospects-box")

        prospect = scraper.parse_prospect(div)

        assert prospect is not None
        assert prospect["name"] == "Patrick Surtain III"
        assert prospect["position"] == "CB"
        assert prospect["grade"] == "9.8"

    def test_parse_prospect_missing_name(self, scraper):
        """Test parsing prospect without name"""
        html = """
        <div class="card-prospects-box">
            <span class="position">CB</span>
            <span class="grade">9.8</span>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        div = soup.find("div", class_="card-prospects-box")

        prospect = scraper.parse_prospect(div)

        assert prospect is None

    def test_parse_prospect_with_missing_fields(self, scraper):
        """Test parsing prospect with missing optional fields"""
        html = """
        <div class="card-prospects-box">
            <h3>Test Prospect</h3>
            <span class="position">CB</span>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        div = soup.find("div", class_="card-prospects-box")

        prospect = scraper.parse_prospect(div)

        assert prospect is not None
        assert prospect["name"] == "Test Prospect"
        assert prospect["position"] == "CB"
        assert prospect["school"] is None

    def test_parse_fixture_page1(self, scraper, fixture_html_page1):
        """Test parsing fixture page 1"""
        if not fixture_html_page1:
            pytest.skip("Fixture file not found")

        soup = BeautifulSoup(fixture_html_page1, "html.parser")
        prospects = []

        for div in soup.find_all("div", class_="card-prospects-box"):
            prospect = scraper.parse_prospect(div)
            if prospect:
                prospects.append(prospect)

        assert len(prospects) >= 5
        assert any(p["name"] == "Patrick Surtain III" for p in prospects)

    def test_cache_operations(self):
        """Test cache save/load"""
        with tempfile.TemporaryDirectory() as tmpdir:
            scraper = PFFScraper(season=2026, cache_enabled=True)
            scraper.cache_dir = Path(tmpdir)

            # Save to cache
            test_prospects = [
                {"name": "Test 1", "position": "CB", "grade": "9.8"},
                {"name": "Test 2", "position": "WR", "grade": "9.1"},
            ]
            scraper._save_cache(1, test_prospects)

            # Verify cache file exists
            cache_file = Path(tmpdir) / "season_2026_page_1.json"
            assert cache_file.exists()

            # Load from cache
            loaded = scraper._load_cache(1)
            assert loaded == test_prospects

    def test_get_summary(self, scraper):
        """Test scraper summary"""
        scraper.prospects = [
            {"name": "Test 1", "position": "CB", "school": "Miami"},
            {"name": "Test 2", "position": "QB", "school": "Alabama"},
            {"name": "Test 3", "position": "CB", "school": "Miami"},
        ]

        summary = scraper.get_summary()

        assert summary["total_prospects"] == 3
        assert summary["by_position"]["CB"] == 2
        assert summary["by_position"]["QB"] == 1
        assert summary["by_school"]["Miami"] == 2
        assert summary["by_school"]["Alabama"] == 1


class TestPFFProspectValidator:
    """Tests for embedded PFF prospect validator"""

    def test_validate_grade(self):
        """Test grade validation"""
        assert PFFProspectValidator.validate_grade("9.8") is True
        assert PFFProspectValidator.validate_grade("105") is False
        assert PFFProspectValidator.validate_grade(None) is True

    def test_validate_position(self):
        """Test position validation"""
        assert PFFProspectValidator.validate_position("CB") is True
        assert PFFProspectValidator.validate_position("INVALID") is False
        assert PFFProspectValidator.validate_position(None) is True

    def test_validate_prospect(self):
        """Test prospect validation"""
        valid_prospect = {
            "name": "Test",
            "position": "CB",
            "grade": "9.8",
        }
        assert PFFProspectValidator.validate_prospect(valid_prospect) is True

        invalid_prospect = {
            "name": "Test",
            "position": "INVALID",
        }
        assert PFFProspectValidator.validate_prospect(invalid_prospect) is False


# Integration tests
class TestPFFScraperIntegration:
    """Integration tests for scraper"""

    def test_scraper_workflow(self):
        """Test complete scraper workflow"""
        scraper = PFFScraper(season=2026, cache_enabled=False)

        # Create fixture-like HTML
        html = """
        <div class="card-prospects-box">
            <h3>Test 1</h3>
            <span class="position">CB</span>
            <span class="grade">9.5</span>
        </div>
        <div class="card-prospects-box">
            <h3>Test 2</h3>
            <span class="position">INVALID</span>
            <span class="grade">9.3</span>
        </div>
        """

        soup = BeautifulSoup(html, "html.parser")
        prospects = []

        for div in soup.find_all("div", class_="card-prospects-box"):
            prospect = scraper.parse_prospect(div)
            if prospect:
                prospects.append(prospect)

        assert len(prospects) == 1  # Only valid prospect
        assert prospects[0]["name"] == "Test 1"

        scraper.prospects = prospects
        summary = scraper.get_summary()

        assert summary["total_prospects"] == 1
        assert summary["by_position"]["CB"] == 1
