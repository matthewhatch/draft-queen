"""Unit tests for PFF Grade Loader.

Tests fuzzy matching, grade normalization, database insertion,
and audit trail recording.
"""

import pytest
from unittest.mock import MagicMock, patch, ANY
from datetime import datetime, timezone
import uuid

from data_pipeline.loaders.pff_grade_loader import (
    PFFGradeLoader,
    MATCH_THRESHOLD_LOW,
    MATCH_THRESHOLD_HIGH,
)
from data_pipeline.validators.pff_validator import normalize_pff_grade


class TestPFFGradeLoader:
    """Test suite for PFFGradeLoader class."""

    def setup_method(self):
        """Setup before each test."""
        self.session = MagicMock()
        self.loader = PFFGradeLoader(self.session)

    def _make_pff_prospect(
        self,
        name="Travis Hunter",
        position="CB",
        school="Colorado",
        grade="96.2",
        class_year="Jr.",
        height="6' 1\"",
        weight="185",
        scraped_at="2026-02-12T00:00:00",
    ):
        """Helper to create PFF prospect dict."""
        return {
            "name": name,
            "position": position,
            "school": school,
            "grade": grade,
            "class": class_year,
            "height": height,
            "weight": weight,
            "scraped_at": scraped_at,
        }

    def _make_db_prospect(
        self,
        id=None,
        name="Travis Hunter",
        position="DB",
        college="Colorado",
    ):
        """Helper to create mock DB Prospect."""
        if id is None:
            id = uuid.uuid4()
        p = MagicMock()
        p.id = id
        p.name = name
        p.position = position
        p.college = college
        return p

    # ========== Test 1: Exact Match ==========
    def test_exact_match_name_position_college(self):
        """Test exact name + position + college match."""
        pff_data = self._make_pff_prospect()
        db_prospect = self._make_db_prospect()

        prospect_index = [
            {
                "id": db_prospect.id,
                "name": "travis hunter",
                "position": "DB",
                "college": "colorado",
                "obj": db_prospect,
            }
        ]

        match = self.loader._fuzzy_match(pff_data, prospect_index)

        # Verify exact match
        assert match is not None
        assert match[1] >= MATCH_THRESHOLD_HIGH  # Should be very high confidence

    # ========== Test 2: Fuzzy Name Match ==========
    def test_fuzzy_match_name_variation(self):
        """Test fuzzy match for name variation with matching position/school."""
        # Use matching position and school to isolate name fuzzing
        # NOTE: "DT" is a real PFF position that maps to "DL" in DB
        pff_data = self._make_pff_prospect(
            name="J. Carter",
            position="DT",  # Real PFF position (maps to DB "DL")
            school="Georgia",
        )
        db_prospect = self._make_db_prospect(
            name="Jalen Carter",
            position="DL",
            college="Georgia",
        )

        prospect_index = [
            {
                "id": db_prospect.id,
                "name": "jalen carter",
                "position": "DL",
                "college": "georgia",
                "obj": db_prospect,
            }
        ]

        match = self.loader._fuzzy_match(pff_data, prospect_index)
        # Should match with position and school helping
        assert match is not None
        assert match[1] >= MATCH_THRESHOLD_LOW

    # ========== Test 3: No Match (Unknown Prospect) ==========
    def test_no_match_unknown_prospect(self):
        """Test unmatched prospect (unknown to DB)."""
        pff_data = self._make_pff_prospect(
            name="Unknown Player",
            school="Unknown College",
        )
        prospect_index = [
            self._make_db_prospect(name="Travis Hunter", college="Colorado"),
            self._make_db_prospect(name="Saquon Barkley", college="Penn State"),
        ]
        
        # Convert to index format
        index_list = [
            {
                "id": p.id,
                "name": p.name.lower(),
                "position": p.position,
                "college": p.college.lower(),
                "obj": p,
            }
            for p in prospect_index
        ]

        match = self.loader._fuzzy_match(pff_data, index_list)
        assert match is None

    # ========== Test 4: Upsert - Update Existing Grade ==========
    def test_upsert_update_existing_grade(self):
        """Test updating an existing PFF grade for a prospect."""
        pff_data = self._make_pff_prospect(grade="95.0")
        db_prospect = self._make_db_prospect()

        existing_grade = MagicMock()
        existing_grade.id = 1
        existing_grade.grade_overall = 90.0

        # Mock query returns the existing grade
        self.session.query.return_value.filter_by.return_value.first.return_value = (
            existing_grade
        )

        prospect_index = [
            {
                "id": db_prospect.id,
                "name": "travis hunter",
                "position": "DB",
                "college": "colorado",
                "obj": db_prospect,
            }
        ]

        self.loader._process_one(pff_data, prospect_index)

        # Verify update, not insert
        assert self.loader.stats["updated"] == 1
        assert self.loader.stats["inserted"] == 0
        # Verify grade was updated
        assert existing_grade.grade_overall == 95.0

    # ========== Test 5: Position Mapping ==========
    def test_position_mapping_lt_to_ol(self):
        """Test PFF position mapping (LT -> OL for DB match)."""
        # PFF uses granular position 'LT', DB uses 'OL'
        pff_data = self._make_pff_prospect(position="LT")
        db_prospect = self._make_db_prospect(position="OL")

        prospect_index = [
            {
                "id": db_prospect.id,
                "name": "travis hunter",
                "position": "OL",
                "college": "colorado",
                "obj": db_prospect,
            }
        ]

        match = self.loader._fuzzy_match(pff_data, prospect_index)
        # Should match because position maps correctly
        assert match is not None

    # ========== Test 6: Grade Normalization ==========
    def test_grade_normalization(self):
        """Test PFF grade 0-100 -> 5.0-10.0 normalization."""
        test_cases = [
            (0, 5.0),    # Min
            (50, 7.5),   # Mid
            (100, 10.0), # Max
            (91.6, 9.6), # Example
        ]

        for pff_grade, expected in test_cases:
            normalized = normalize_pff_grade(pff_grade)
            assert normalized == expected, f"Grade {pff_grade} should map to {expected}, got {normalized}"

    # ========== Test 7: School -> College Field Mapping ==========
    def test_school_to_college_field_mapping(self):
        """Test PFF 'school' field maps to DB 'college' field."""
        pff_data = self._make_pff_prospect(school="Colorado")
        db_prospect = self._make_db_prospect(college="Colorado")

        prospect_index = [
            {
                "id": db_prospect.id,
                "name": "travis hunter",
                "position": "DB",
                "college": "colorado",  # DB field is 'college'
                "obj": db_prospect,
            }
        ]

        match = self.loader._fuzzy_match(pff_data, prospect_index)
        assert match is not None

    # ========== Test 8: Batch Load Stats ==========
    def test_batch_load_stats(self):
        """Test statistics are correctly tallied."""
        prospects = [
            self._make_pff_prospect(name="Prospect A"),
            self._make_pff_prospect(name="Prospect B", school="Unknown School"),
        ]

        # Mock DB query
        db_prospect_a = self._make_db_prospect(name="Prospect A")
        self.session.query.return_value.all.return_value = [db_prospect_a]
        self.session.query.return_value.filter_by.return_value.first.return_value = None

        stats = self.loader.load(prospects)

        assert stats["total"] == 2
        assert stats["matched"] >= 0
        assert stats["unmatched"] >= 0
        # matched + unmatched should equal total
        assert stats["matched"] + stats["unmatched"] == stats["total"]

    # ========== Test 9: Audit Trail Recording ==========
    def test_audit_trail_written(self):
        """Test DataLoadAudit record is written."""
        prospects = [self._make_pff_prospect()]

        # Mock DB query
        self.session.query.return_value.all.return_value = []
        
        self.loader.load(prospects)

        # Verify audit was added
        self.session.add.assert_called()
        self.session.commit.assert_called()

    # ========== Test 10: Duplicate Handling ==========
    def test_duplicate_pff_entries_same_prospect(self):
        """Test handling of duplicate PFF entries for same prospect."""
        # Same prospect appears twice
        prospects = [
            self._make_pff_prospect(name="Travis Hunter", grade="95.0"),
            self._make_pff_prospect(name="Travis Hunter", grade="96.0"),
        ]

        db_prospect = self._make_db_prospect(name="Travis Hunter")
        self.session.query.return_value.all.return_value = [db_prospect]

        # First call returns None (insert), second returns the inserted record (update)
        existing_grade = MagicMock()
        self.session.query.return_value.filter_by.return_value.first.side_effect = [
            None,  # First prospect - no existing grade
            existing_grade,  # Second prospect - found existing
        ]

        self.loader.load(prospects)

        # Should have 1 inserted, 1 updated
        assert self.loader.stats["inserted"] + self.loader.stats["updated"] == 2

    # ========== Test 11: Transaction Rollback on Error ==========
    def test_transaction_rollback_on_error(self):
        """Test transaction rolls back on critical error."""
        prospects = [self._make_pff_prospect()]

        # Mock commit to fail
        self.session.commit.side_effect = Exception("DB Error")
        self.session.query.return_value.all.return_value = []

        stats = self.loader.load(prospects)

        # Verify rollback was called
        self.session.rollback.assert_called()
        # Error count should be incremented
        assert stats["errors"] > 0


class TestPFFPositionMapping:
    """Test PFF position mapping functionality."""

    def test_all_pff_positions_mapped(self):
        """Test that all PFF positions can be mapped to DB positions."""
        from data_pipeline.validators.pff_validator import (
            PFF_TO_DB_POSITION_MAP,
            map_pff_position_to_db,
        )

        expected_mappings = {
            "LT": "OL",
            "LG": "OL",
            "C": "OL",
            "RG": "OL",
            "RT": "OL",
            "DT": "DL",
            "DE": "DL",
            "SS": "DB",
            "FS": "DB",
            "CB": "DB",
            "EDGE": "EDGE",
            "LB": "LB",
            "QB": "QB",
            "RB": "RB",
            "WR": "WR",
            "TE": "TE",
            "K": "K",
            "P": "P",
        }

        for pff_pos, expected_db_pos in expected_mappings.items():
            actual = map_pff_position_to_db(pff_pos)
            assert (
                actual == expected_db_pos
            ), f"Position {pff_pos} should map to {expected_db_pos}, got {actual}"

    def test_unmapped_position_returns_none(self):
        """Test that unmapped positions return None."""
        from data_pipeline.validators.pff_validator import map_pff_position_to_db

        assert map_pff_position_to_db("INVALID") is None
        assert map_pff_position_to_db("") is None
        assert map_pff_position_to_db(None) is None


class TestWeightedFuzzyMatching:
    """Test weighted fuzzy matching algorithm."""

    def test_match_weights_name_heavy_plus_college(self):
        """Test that name (60%) + college match can reach threshold.
        
        Note: Name alone maxes at 60% which is below 75% threshold.
        This test validates that position/college help reach threshold.
        """
        loader = PFFGradeLoader(MagicMock())

        pff_data = {
            "name": "Travis Hunter",
            "position": "CB",
            "school": "Colorado",
            "grade": "96.2",
        }

        prospect_index = [
            {
                "id": "id1",
                "name": "travis hunter",  # Exact match (100)
                "position": "DB",  # Perfect position map (100)
                "college": "colorado",  # Exact college (100)
                "obj": None,
            }
        ]

        match = loader._fuzzy_match(pff_data, prospect_index)
        # Should match: name 100% (60) + position 100% (25) + college 100% (15) = 100
        assert match is not None
        assert match[1] >= MATCH_THRESHOLD_HIGH
