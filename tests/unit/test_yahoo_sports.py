"""Unit tests for Yahoo Sports scraper and data pipeline components."""

import pytest
import logging
from pathlib import Path
from bs4 import BeautifulSoup
from unittest.mock import Mock, patch, MagicMock
from data_pipeline.sources.yahoo_sports_scraper import (
    YahooSportsConnector,
    MockYahooSportsConnector,
)
from data_pipeline.validators.prospect_matcher import ProspectMatcher, MatchResult
from data_pipeline.validators.stat_validator import ProspectStatValidator, ValidationError

logger = logging.getLogger(__name__)

# Fixtures directory
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestYahooSportsConnectorBasic:
    """Tests for basic Yahoo Sports connector functionality."""

    def test_connector_initialization(self):
        """Test connector initializes with proper session."""
        connector = YahooSportsConnector()
        assert connector.session is not None
        assert connector.cached_prospects == {}
        assert connector.last_request_time == 0
        connector.close()

    def test_session_headers_set(self):
        """Test session has proper headers."""
        connector = YahooSportsConnector()
        headers = connector.session.headers
        assert "User-Agent" in headers
        assert "Mozilla" in headers["User-Agent"]
        connector.close()

    def test_rate_limit_delay(self):
        """Test rate limiting is enforced."""
        connector = YahooSportsConnector()
        connector.last_request_time = 0

        # Should not raise error
        connector._apply_rate_limit()
        # Rate limit delay should be applied
        assert connector.last_request_time > 0
        connector.close()

    def test_normalize_name(self):
        """Test name normalization."""
        assert ProspectMatcher._normalize_name("John Smith") == "john smith"
        assert ProspectMatcher._normalize_name("John Smith Jr.") == "john smith"
        assert ProspectMatcher._normalize_name("John Smith Sr.") == "john smith"
        assert ProspectMatcher._normalize_name("  John   Smith  ") == "john smith"

    def test_parse_integer(self):
        """Test integer parsing from strings."""
        connector = YahooSportsConnector()
        assert connector._parse_int("100") == 100
        assert connector._parse_int("1,234") == 1234
        assert connector._parse_int("invalid") is None
        assert connector._parse_int("") is None
        connector.close()

    def test_parse_float(self):
        """Test float parsing from strings."""
        connector = YahooSportsConnector()
        assert connector._parse_float("8.2") == 8.2
        assert connector._parse_float("10.5") == 10.5
        assert connector._parse_float("invalid") is None
        connector.close()


class TestYahooSportsHTMLParsing:
    """Tests for HTML parsing with fixtures."""

    def test_parse_qb_stats(self):
        """Test parsing QB stats from fixture."""
        with open(FIXTURES_DIR / "yahoo_sports_qb_fixture.html", "r") as f:
            html = f.read()

        connector = YahooSportsConnector()
        stats = connector._parse_player_stats(html)

        assert stats["name"] == "Jalen Hurts"
        assert stats["position"] == "QB"
        assert stats["college"] == "Oklahoma"
        assert len(stats["college_stats_by_year"]) == 2
        assert stats["production_metrics"]["total_receptions"] == 2
        assert stats["production_metrics"]["total_rushes"] == 95
        assert stats["performance_ranking"] == 8.2
        connector.close()

    def test_parse_wr_stats(self):
        """Test parsing WR stats from fixture."""
        with open(FIXTURES_DIR / "yahoo_sports_wr_fixture.html", "r") as f:
            html = f.read()

        connector = YahooSportsConnector()
        stats = connector._parse_player_stats(html)

        assert stats["name"] == "Ja'Marr Chase"
        assert stats["position"] == "WR"
        assert stats["college"] == "LSU"
        assert stats["production_metrics"]["total_receptions"] == 187
        assert stats["production_metrics"]["total_rushes"] == 13
        connector.close()

    def test_parse_incomplete_stats(self):
        """Test parsing incomplete/malformed HTML."""
        with open(FIXTURES_DIR / "yahoo_sports_incomplete_fixture.html", "r") as f:
            html = f.read()

        connector = YahooSportsConnector()
        stats = connector._parse_player_stats(html)

        # Should still have name but missing fields
        assert stats["name"] == "Incomplete Player"
        assert stats.get("position") is None
        assert stats.get("college") is None
        connector.close()


class TestDataValidation:
    """Tests for stat validation."""

    def test_validate_stat_within_range(self):
        """Test stat validation for values within range."""
        is_valid, error = ProspectStatValidator.validate_stat("receptions", 85)
        assert is_valid is True
        assert error is None

    def test_validate_stat_exceeds_max(self):
        """Test validation for value exceeding maximum."""
        is_valid, error = ProspectStatValidator.validate_stat("receptions", 250)
        assert is_valid is False
        assert error is not None
        assert "exceeds maximum" in error.message

    def test_validate_stat_below_min(self):
        """Test validation for value below minimum."""
        is_valid, error = ProspectStatValidator.validate_stat("receptions", -1)
        assert is_valid is False
        assert error is not None
        assert "below minimum" in error.message

    def test_validate_qb_prospect(self):
        """Test validation for QB prospect."""
        prospect = {
            "name": "Test QB",
            "position": "QB",
            "college": "Ohio State",
            "college_stats_by_year": [
                {"year": "2024", "receptions": 0, "rushes": 45, "pass_attempts": 425}
            ],
            "production_metrics": {
                "total_receptions": 0,
                "total_rushes": 95,
                "total_pass_attempts": 948,
            },
        }

        is_valid, errors = ProspectStatValidator.validate_prospect(prospect)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_invalid_position(self):
        """Test validation catches invalid position."""
        prospect = {
            "name": "Test Player",
            "position": "INVALID_POS",
        }

        is_valid, errors = ProspectStatValidator.validate_prospect(prospect)
        assert is_valid is False
        assert any("Invalid position" in e.message for e in errors)

    def test_validate_missing_name(self):
        """Test validation requires name."""
        prospect = {"position": "QB"}

        is_valid, errors = ProspectStatValidator.validate_prospect(prospect)
        assert is_valid is False
        assert any("required" in e.message for e in errors)

    def test_validation_summary(self):
        """Test validation summary generation."""
        prospects = [
            {
                "name": "Valid QB",
                "position": "QB",
                "college": "Ohio State",
                "college_stats_by_year": [
                    {
                        "year": "2024",
                        "receptions": 0,
                        "rushes": 45,
                        "pass_attempts": 425,
                    }
                ],
                "production_metrics": {
                    "total_receptions": 0,
                    "total_rushes": 95,
                    "total_pass_attempts": 948,
                },
            },
            {"name": "Invalid Player", "position": "INVALID"},
        ]

        valid_count, total_count, error_count, details = (
            ProspectStatValidator.get_validation_summary(prospects)
        )
        assert total_count == 2
        assert valid_count == 1
        assert error_count == 1


class TestProspectMatching:
    """Tests for prospect fuzzy matching."""

    def test_exact_name_match(self):
        """Test exact name matching."""
        score = ProspectMatcher.calculate_name_similarity("John Smith", "John Smith")
        assert score == 100

    def test_partial_name_match(self):
        """Test partial name matching."""
        score = ProspectMatcher.calculate_name_similarity("John Smith", "J. Smith")
        assert score > 80

    def test_name_with_suffix(self):
        """Test name matching with suffix."""
        score = ProspectMatcher.calculate_name_similarity("John Smith", "John Smith Jr.")
        assert score > 90

    def test_case_insensitive_match(self):
        """Test case-insensitive matching."""
        score = ProspectMatcher.calculate_name_similarity("JOHN SMITH", "john smith")
        assert score == 100

    def test_whitespace_handling(self):
        """Test whitespace handling in names."""
        score = ProspectMatcher.calculate_name_similarity("John  Smith", "John Smith")
        assert score == 100

    def test_find_best_match(self):
        """Test finding best match in prospect list."""
        existing = [
            {"id": 1, "name": "John Smith"},
            {"id": 2, "name": "Jane Doe"},
            {"id": 3, "name": "John Smythe"},
        ]

        result = ProspectMatcher.find_best_match(
            "John Smith", existing, threshold=80
        )
        assert result is not None
        assert result.prospect_id == 1
        assert result.is_match is True

    def test_find_all_matches(self):
        """Test finding all potential matches."""
        existing = [
            {"id": 1, "name": "John Smith"},
            {"id": 2, "name": "John Smythe"},
            {"id": 3, "name": "Jon Smith"},
        ]

        results = ProspectMatcher.find_all_matches(
            "John Smith", existing, threshold=75
        )
        assert len(results) >= 2
        # Best match should be first
        assert results[0].prospect_id == 1

    def test_deduplicate_prospects(self):
        """Test deduplication logic."""
        prospects = [
            {"id": 1, "name": "John Smith"},
            {"id": 2, "name": "John Smith"},  # Duplicate
            {"id": 3, "name": "Jane Doe"},
        ]

        unique, duplicates = ProspectMatcher.deduplicate_prospects(prospects)
        assert len(unique) == 2
        assert len(duplicates) > 0

    def test_match_across_sources(self):
        """Test cross-source matching with context."""
        new_prospect = {
            "name": "John Smith",
            "position": "QB",
            "college": "Ohio State",
        }
        existing = [
            {"id": 1, "name": "John Smith", "position": "QB", "college": "Ohio State"}
        ]

        result = ProspectMatcher.match_across_sources(
            new_prospect, existing, position_weight=0.3, college_weight=0.1
        )
        assert result is not None
        assert result.confidence == "high"

    def test_match_confidence_levels(self):
        """Test match confidence classifications."""
        # High confidence
        result = ProspectMatcher.find_best_match(
            "John Smith", [{"id": 1, "name": "John Smith"}], threshold=90
        )
        assert result.confidence == "high"

        # Medium confidence
        result = ProspectMatcher.find_best_match(
            "John Smith",
            [{"id": 1, "name": "Jon Smith"}],
            threshold=75,
        )
        assert result.confidence in ["medium", "low"]


class TestMockConnector:
    """Tests for mock connector."""

    def test_mock_connector_initialization(self):
        """Test mock connector initializes."""
        connector = MockYahooSportsConnector()
        assert connector is not None

    def test_mock_connector_fetch_prospects(self):
        """Test mock connector returns test data."""
        connector = MockYahooSportsConnector()
        prospects = connector.fetch_prospects()

        assert len(prospects) == 2
        assert prospects[0]["name"] == "Test QB"
        assert prospects[1]["name"] == "Test WR"

    def test_mock_connector_health_check(self):
        """Test mock health check always passes."""
        connector = MockYahooSportsConnector()
        assert connector.health_check() is True

    def test_mock_data_format(self):
        """Test mock data has proper format."""
        connector = MockYahooSportsConnector()
        prospects = connector.fetch_prospects()

        for prospect in prospects:
            assert "name" in prospect
            assert "position" in prospect
            assert "college" in prospect
            assert "college_stats_by_year" in prospect
            assert "production_metrics" in prospect


class TestYahooSportsIntegration:
    """Integration tests for Yahoo Sports scraper."""

    @patch("data_pipeline.sources.yahoo_sports_scraper.requests.Session.get")
    def test_fetch_prospects_with_mocked_http(self, mock_get):
        """Test fetching prospects with mocked HTTP."""
        # Read fixture
        with open(FIXTURES_DIR / "yahoo_sports_qb_fixture.html", "r") as f:
            fixture_content = f.read()

        # Mock response
        mock_response = MagicMock()
        mock_response.text = fixture_content
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        connector = YahooSportsConnector()
        prospects = connector.fetch_prospects()

        # Should have parsed the fixture
        assert len(prospects) > 0
        connector.close()

    def test_cache_fallback(self):
        """Test cache fallback when fetch fails."""
        connector = YahooSportsConnector()
        connector.cached_prospects["prospects"] = [
            {"name": "Cached Player", "position": "QB"}
        ]

        # This should use cache since URL is mocked to fail
        with patch.object(connector, "_fetch_url", return_value=None):
            prospects = connector.fetch_prospects()
            assert len(prospects) == 1
            assert prospects[0]["name"] == "Cached Player"

        connector.close()


class TestErrorHandling:
    """Tests for error handling."""

    def test_parse_stats_handles_missing_fields(self):
        """Test parsing gracefully handles missing fields."""
        html = """
        <div class="player-card">
            <h3 class="player-name">Test</h3>
        </div>
        """
        connector = YahooSportsConnector()
        stats = connector._parse_player_stats(html)

        assert stats["name"] == "Test"
        assert stats.get("position") is None
        connector.close()

    def test_validation_with_invalid_types(self):
        """Test validation handles invalid types."""
        prospect = {
            "name": "Test",
            "position": "QB",
            "college_stats_by_year": [
                {
                    "year": "2024",
                    "receptions": "not_a_number",
                    "rushes": 45,
                    "pass_attempts": 425,
                }
            ],
        }

        is_valid, errors = ProspectStatValidator.validate_prospect(prospect)
        # Should have errors for invalid type
        assert len(errors) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
