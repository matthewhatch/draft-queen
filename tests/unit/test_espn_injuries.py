"""Unit tests for ESPN injury scraper and tracking components."""

import pytest
import logging
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from data_pipeline.sources.espn_injury_scraper import (
    ESPNInjuryConnector,
    MockESPNInjuryConnector,
)
from data_pipeline.validators.injury_tracker import (
    InjuryUpdateTracker,
    InjuryUpdate,
)

logger = logging.getLogger(__name__)

# Fixtures directory
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestESPNConnectorBasic:
    """Tests for basic ESPN connector functionality."""

    def test_connector_initialization(self):
        """Test connector initializes properly."""
        connector = ESPNInjuryConnector()
        assert connector.session is not None
        assert connector.cached_injuries == {}
        assert connector.last_update is None
        connector.close()

    def test_session_headers(self):
        """Test session has proper headers."""
        connector = ESPNInjuryConnector()
        headers = connector.session.headers
        assert "User-Agent" in headers
        assert "Mozilla" in headers["User-Agent"]
        connector.close()

    def test_injury_type_normalization(self):
        """Test injury type normalization."""
        connector = ESPNInjuryConnector()
        
        assert connector._normalize_injury_type("knee") == "Knee"
        assert connector._normalize_injury_type("Knee Injury") == "Knee"
        assert connector._normalize_injury_type("torn acl") == "Torn Acl"
        assert connector._normalize_injury_type("hamstring strain") == "Hamstring"
        
        connector.close()

    def test_severity_extraction(self):
        """Test severity extraction from status strings."""
        connector = ESPNInjuryConnector()
        
        label, score = connector._extract_severity("Out")
        assert label == "Out"
        assert score == 3
        
        label, score = connector._extract_severity("Day-to-Day")
        assert label == "Day-to-Day"
        assert score == 2
        
        label, score = connector._extract_severity("Questionable")
        assert label == "Questionable"
        assert score == 1
        
        connector.close()

    def test_return_date_parsing(self):
        """Test parsing expected return dates."""
        connector = ESPNInjuryConnector()
        
        # Should parse various formats
        date1 = connector._parse_return_date("February 14, 2026")
        assert date1 is not None
        assert date1.month == 2
        assert date1.day == 14
        
        date2 = connector._parse_return_date("02/14/2026")
        assert date2 is not None
        
        # Should handle None gracefully
        assert connector._parse_return_date(None) is None
        assert connector._parse_return_date("invalid") is None
        
        connector.close()

    def test_rate_limit_enforcement(self):
        """Test rate limiting is applied."""
        connector = ESPNInjuryConnector()
        connector.last_request_time = 0
        
        connector._apply_rate_limit()
        # Should have set last_request_time
        assert connector.last_request_time > 0
        
        connector.close()


class TestESPNHTMLParsing:
    """Tests for ESPN HTML parsing."""

    def test_parse_complete_injury_list(self):
        """Test parsing complete injury list from fixture."""
        with open(FIXTURES_DIR / "espn_injuries_fixture.html", "r") as f:
            html = f.read()

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        rows = soup.find_all("tr", class_="injury-row")

        assert len(rows) == 4
        
        connector = ESPNInjuryConnector()
        
        # Parse first row (Mahomes)
        injury = connector._parse_injury_row(str(rows[0]))
        assert injury is not None
        assert injury["player_name"] == "Patrick Mahomes"
        assert injury["position"] == "QB"
        assert injury["team"] == "KC"
        assert injury["injury_type"] == "Ankle"  # Normalized to primary injury
        assert injury["severity_label"] == "Day-to-Day"
        assert injury["severity_score"] == 2
        
        connector.close()

    def test_parse_incomplete_injury_data(self):
        """Test parsing incomplete injury data."""
        with open(FIXTURES_DIR / "espn_injuries_incomplete_fixture.html", "r") as f:
            html = f.read()

        connector = ESPNInjuryConnector()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        row = soup.find("tr", class_="injury-row")
        
        injury = connector._parse_injury_row(str(row))
        
        # Should parse available data gracefully
        assert injury is not None
        assert injury["player_name"] == "Test Player"
        assert injury.get("position") is None
        
        connector.close()


class TestMockESPNConnector:
    """Tests for mock ESPN connector."""

    def test_mock_initialization(self):
        """Test mock connector initializes."""
        connector = MockESPNInjuryConnector()
        assert connector is not None

    def test_mock_fetch_injuries(self):
        """Test mock returns injury data."""
        connector = MockESPNInjuryConnector()
        injuries = connector.fetch_injuries()

        assert len(injuries) == 3
        assert injuries[0]["player_name"] == "Test QB"
        assert injuries[1]["injury_type"] == "Hamstring"
        assert injuries[2]["severity_score"] == 1

    def test_mock_data_structure(self):
        """Test mock data has correct structure."""
        connector = MockESPNInjuryConnector()
        injuries = connector.fetch_injuries()

        for injury in injuries:
            assert "player_name" in injury
            assert "position" in injury
            assert "team" in injury
            assert "injury_type" in injury
            assert "severity_label" in injury
            assert "severity_score" in injury
            assert "expected_return_date" in injury
            assert "reported_date" in injury

    def test_mock_health_check(self):
        """Test mock health check."""
        connector = MockESPNInjuryConnector()
        assert connector.health_check() is True


class TestInjuryTracking:
    """Tests for injury update tracking."""

    def test_detect_new_injuries(self):
        """Test detecting newly reported injuries."""
        current = [
            {
                "prospect_id": 1,
                "prospect_name": "Player A",
                "injury_type": "Knee",
                "severity_score": 3,
            },
            {
                "prospect_id": 2,
                "prospect_name": "Player B",
                "injury_type": "Ankle",
                "severity_score": 2,
            },
        ]
        
        previous = [
            {
                "prospect_id": 1,
                "prospect_name": "Player A",
                "injury_type": "Shoulder",
                "severity_score": 1,
            }
        ]

        new_injuries = InjuryUpdateTracker.detect_new_injuries(current, previous)
        
        assert len(new_injuries) == 1
        assert new_injuries[0].prospect_id == 2
        assert new_injuries[0].change_type == "new"
        assert new_injuries[0].injury_type == "Ankle"

    def test_detect_resolved_injuries(self):
        """Test detecting resolved injuries."""
        current = [
            {
                "prospect_id": 1,
                "prospect_name": "Player A",
                "injury_type": "Knee",
                "severity_score": 3,
            }
        ]
        
        previous = [
            {
                "prospect_id": 1,
                "prospect_name": "Player A",
                "injury_type": "Knee",
                "severity_score": 3,
            },
            {
                "prospect_id": 2,
                "prospect_name": "Player B",
                "injury_type": "Ankle",
                "severity_score": 2,
            },
        ]

        resolved = InjuryUpdateTracker.detect_resolved_injuries(current, previous)
        
        assert len(resolved) == 1
        assert resolved[0].prospect_id == 2
        assert resolved[0].change_type == "resolved"

    def test_detect_severity_changes(self):
        """Test detecting severity changes."""
        current = [
            {
                "prospect_id": 1,
                "prospect_name": "Player A",
                "injury_type": "Knee",
                "severity_label": "Out",
                "severity_score": 3,
            }
        ]
        
        previous = [
            {
                "prospect_id": 1,
                "prospect_name": "Player A",
                "injury_type": "Knee",
                "severity_label": "Day-to-Day",
                "severity_score": 2,
            }
        ]

        changes = InjuryUpdateTracker.detect_severity_changes(current, previous)
        
        assert len(changes) == 1
        assert changes[0].change_type == "worsened"
        assert changes[0].previous_severity == 2
        assert changes[0].new_severity == 3

    def test_classify_critical_updates(self):
        """Test classifying critical vs normal updates."""
        updates = [
            InjuryUpdate(
                prospect_id=1,
                prospect_name="Player A",
                change_type="new",
                injury_type="Knee",
                previous_severity=None,
                new_severity=3,
                timestamp=datetime.now(),
                details={"severity_label": "Out"},
            ),
            InjuryUpdate(
                prospect_id=2,
                prospect_name="Player B",
                change_type="improved",
                injury_type="Ankle",
                previous_severity=2,
                new_severity=1,
                timestamp=datetime.now(),
                details={"severity_label": "Questionable"},
            ),
        ]

        critical, normal = InjuryUpdateTracker.classify_critical_updates(
            updates, severity_threshold=2
        )

        assert len(critical) == 1
        assert len(normal) == 1
        assert critical[0].prospect_id == 1

    def test_get_update_summary(self):
        """Test generating update summary."""
        updates = [
            InjuryUpdate(
                prospect_id=1,
                prospect_name="Player A",
                change_type="new",
                injury_type="Knee",
                previous_severity=None,
                new_severity=3,
                timestamp=datetime.now(),
                details={},
            ),
            InjuryUpdate(
                prospect_id=2,
                prospect_name="Player B",
                change_type="resolved",
                injury_type="Ankle",
                previous_severity=2,
                new_severity=0,
                timestamp=datetime.now(),
                details={},
            ),
        ]

        summary = InjuryUpdateTracker.get_update_summary(updates)

        assert summary["total"] == 2
        assert summary["new"] == 1
        assert summary["resolved"] == 1

    def test_generate_alert_message(self):
        """Test generating alert message."""
        critical_updates = [
            InjuryUpdate(
                prospect_id=1,
                prospect_name="Patrick Mahomes",
                change_type="new",
                injury_type="Knee",
                previous_severity=None,
                new_severity=3,
                timestamp=datetime.now(),
                details={
                    "severity_label": "Out",
                    "position": "QB",
                },
            ),
        ]

        message = InjuryUpdateTracker.generate_alert_message(critical_updates)

        assert message is not None
        assert "CRITICAL INJURY" in message
        assert "Patrick Mahomes" in message
        assert "Knee" in message
        assert "QB" in message


class TestInjuryFiltering:
    """Tests for injury filtering methods."""

    def test_fetch_injuries_by_position(self):
        """Test filtering injuries by position."""
        connector = MockESPNInjuryConnector()
        qb_injuries = connector.fetch_injuries_by_position("QB")

        assert len(qb_injuries) == 1
        assert qb_injuries[0]["position"] == "QB"

    def test_fetch_injuries_by_team(self):
        """Test filtering injuries by team."""
        connector = MockESPNInjuryConnector()
        kc_injuries = connector.fetch_injuries_by_team("KC")

        assert len(kc_injuries) == 1
        assert kc_injuries[0]["team"] == "KC"

    def test_fetch_critical_injuries(self):
        """Test filtering critical injuries."""
        connector = MockESPNInjuryConnector()
        critical = connector.fetch_critical_injuries(severity_threshold=2)

        assert len(critical) == 2  # Score 2 and 3
        assert all(i["severity_score"] >= 2 for i in critical)


class TestInjuryProspectLinking:
    """Tests for linking injuries to prospects."""

    def test_link_injury_to_prospect(self):
        """Test linking injury to prospect via fuzzy matching."""
        connector = MockESPNInjuryConnector()
        injury = {
            "player_name": "Test QB",
            "injury_type": "Knee",
        }
        
        prospects = [
            {"id": 1, "name": "Test QB"},
            {"id": 2, "name": "Another Player"},
        ]

        result = connector.link_to_prospect(injury, prospects)

        assert result is not None
        assert result["prospect_id"] == 1
        assert result["prospect_name"] == "Test QB"


class TestESPNHealth:
    """Tests for health checking."""

    def test_get_update_age(self):
        """Test getting update age."""
        connector = ESPNInjuryConnector()
        
        assert connector.get_update_age() is None
        
        connector.last_update = datetime.now() - timedelta(hours=1)
        age = connector.get_update_age()
        
        assert age is not None
        assert age.total_seconds() > 3600  # More than 1 hour
        
        connector.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
