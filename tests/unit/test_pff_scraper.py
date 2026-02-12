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
        """Load page 1 fixture with correct PFF DOM structure"""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "pff" / "page_1_correct_structure.html"
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
        """Test parsing valid prospect with correct PFF DOM structure"""
        html = """
        <div class="g-card g-card--border-gray">
            <div class="m-ranking-header">
                <div class="m-ranking-header__main-details">
                    <h3 class="m-ranking-header__title">
                        <a href="#">Fernando Mendoza</a>
                    </h3>
                </div>
                <div class="m-ranking-header__details">
                    <div class="m-stat">
                        <div class="g-label">Position</div>
                        <div class="g-data">QB</div>
                    </div>
                    <div class="m-stat">
                        <div class="g-label">Class</div>
                        <div class="g-data">RS Jr.</div>
                    </div>
                </div>
            </div>
            <div class="g-card__content">
                <div class="m-stat-cluster">
                    <div>
                        <div class="g-label">School</div>
                        <div class="g-data"><span>Indiana</span></div>
                    </div>
                    <div>
                        <div class="g-label">Height</div>
                        <div class="g-data">6' 5"</div>
                    </div>
                </div>
                <table class="g-table">
                    <tbody>
                        <tr>
                            <td data-cell-label="Season Grade">
                                <div class="kyber-grade-badge__info-text">91.6</div>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        div = soup.find("div", class_="g-card")

        prospect = scraper.parse_prospect(div)

        assert prospect is not None
        assert prospect["name"] == "Fernando Mendoza"
        assert prospect["position"] == "QB"
        assert prospect["school"] == "Indiana"
        assert prospect["class"] == "RS Jr."
        assert prospect["grade"] == "91.6"

    def test_parse_prospect_missing_name(self, scraper):
        """Test parsing prospect without name"""
        html = """
        <div class="g-card g-card--border-gray">
            <div class="m-ranking-header">
                <!-- No title/name element -->
                <div class="m-ranking-header__details">
                    <div class="m-stat">
                        <div class="g-label">Position</div>
                        <div class="g-data">CB</div>
                    </div>
                </div>
            </div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        div = soup.find("div", class_="g-card")

        prospect = scraper.parse_prospect(div)

        assert prospect is None

    def test_parse_prospect_with_missing_fields(self, scraper):
        """Test parsing prospect with missing optional fields"""
        html = """
        <div class="g-card g-card--border-gray">
            <div class="m-ranking-header">
                <div class="m-ranking-header__main-details">
                    <h3 class="m-ranking-header__title">
                        <a href="#">Test Prospect</a>
                    </h3>
                </div>
                <div class="m-ranking-header__details">
                    <div class="m-stat">
                        <div class="g-label">Position</div>
                        <div class="g-data">CB</div>
                    </div>
                </div>
            </div>
            <div class="g-card__content">
                <div class="m-stat-cluster">
                    <!-- No school, height, weight -->
                </div>
                <table class="g-table"><tbody><tr></tr></tbody></table>
            </div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        div = soup.find("div", class_="g-card")

        prospect = scraper.parse_prospect(div)

        assert prospect is not None
        assert prospect["name"] == "Test Prospect"
        assert prospect["position"] == "CB"
        assert prospect["school"] is None

    def test_parse_fixture_page1(self, scraper, fixture_html_page1):
        """Test parsing fixture page 1 with real prospect data"""
        if not fixture_html_page1:
            pytest.skip("Fixture file not found")

        soup = BeautifulSoup(fixture_html_page1, "html.parser")
        prospects = []

        prospect_divs = soup.find_all("div", class_="g-card")
        for div in prospect_divs:
            prospect = scraper.parse_prospect(div)
            if prospect:
                prospects.append(prospect)

        # Should find 3 prospects from fixture
        assert len(prospects) == 3
        # Check first prospect
        assert prospects[0]["name"] == "Fernando Mendoza"
        assert prospects[0]["position"] == "QB"
        assert prospects[0]["school"] == "Indiana"
        assert prospects[0]["grade"] == "91.6"
        # Check second prospect (partial data)
        assert prospects[1]["name"] == "Rueben Bain Jr"
        assert prospects[1]["position"] == "EDGE"
        # Check third prospect
        assert prospects[2]["name"] == "Arvell Reese"
        assert prospects[2]["position"] == "LB"

        # All 3 prospects from fixture have been tested above

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

        # Create fixture-like HTML with correct structure
        html = """
        <div class="g-card g-card--border-gray">
            <div class="m-ranking-header">
                <div class="m-ranking-header__main-details">
                    <h3 class="m-ranking-header__title"><a>Test 1</a></h3>
                </div>
                <div class="m-ranking-header__details">
                    <div class="m-stat">
                        <div class="g-label">Position</div>
                        <div class="g-data">CB</div>
                    </div>
                </div>
            </div>
            <div class="g-card__content">
                <div class="m-stat-cluster"></div>
                <table class="g-table"><tbody><tr></tr></tbody></table>
            </div>
        </div>
        <div class="g-card g-card--border-gray">
            <div class="m-ranking-header">
                <div class="m-ranking-header__main-details">
                    <h3 class="m-ranking-header__title"><a>Test 2</a></h3>
                </div>
                <div class="m-ranking-header__details">
                    <div class="m-stat">
                        <div class="g-label">Position</div>
                        <div class="g-data">INVALID</div>
                    </div>
                </div>
            </div>
            <div class="g-card__content">
                <div class="m-stat-cluster"></div>
                <table class="g-table"><tbody><tr></tr></tbody></table>
            </div>
        </div>
        """

        soup = BeautifulSoup(html, "html.parser")
        prospects = []

        for div in soup.find_all("div", class_="g-card"):
            prospect = scraper.parse_prospect(div)
            if prospect:
                prospects.append(prospect)

        assert len(prospects) == 1  # Only valid prospect
        assert prospects[0]["name"] == "Test 1"

        scraper.prospects = prospects
        summary = scraper.get_summary()

        assert summary["total_prospects"] == 1
        assert summary["by_position"]["CB"] == 1
