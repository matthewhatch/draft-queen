"""CFR (College Football Reference) Transformer

Transforms CFR staging data to prospect_college_stats canonical table.

Position-specific stat normalization:
- QB: passing, rushing, interceptions
- RB: rushing, receiving, kick return
- WR: receiving, rushing
- TE: receiving
- OL: games_started
- DL: tackles, sacks, TFL, forced fumbles
- EDGE: sacks, tackles, TFL
- LB: tackles, sacks, passes defended, interceptions
- DB: interceptions, passes defended, tackles
"""

from typing import Optional, Dict, Any, List
from uuid import UUID
from decimal import Decimal
import logging

from .base_transformer import BaseTransformer, TransformationResult, FieldChange
from .lineage_recorder import LineageRecorder

logger = logging.getLogger(__name__)


class CFRTransformer(BaseTransformer):
    """Transform CFR college football stats to prospect_college_stats table."""

    SOURCE_NAME = "cfr"
    STAGING_TABLE_NAME = "cfr_staging"

    # Position-specific stat groups for validation
    POSITION_STAT_GROUPS = {
        "QB": [
            "passing_attempts",
            "passing_completions",
            "passing_yards",
            "passing_touchdowns",
            "interceptions_thrown",
            "rushing_attempts",
            "rushing_yards",
        ],
        "RB": [
            "rushing_attempts",
            "rushing_yards",
            "rushing_touchdowns",
            "receiving_targets",
            "receiving_receptions",
            "receiving_yards",
            "receiving_touchdowns",
            "kick_return_attempts",
            "kick_return_yards",
        ],
        "WR": [
            "receiving_targets",
            "receiving_receptions",
            "receiving_yards",
            "receiving_touchdowns",
            "rushing_attempts",
            "rushing_yards",
        ],
        "TE": [
            "receiving_targets",
            "receiving_receptions",
            "receiving_yards",
            "receiving_touchdowns",
        ],
        "OL": ["games_started"],
        "DL": [
            "tackles",
            "tackles_for_loss",
            "sacks",
            "forced_fumbles",
            "passes_defended",
        ],
        "EDGE": [
            "tackles",
            "tackles_for_loss",
            "sacks",
            "forced_fumbles",
            "passes_defended",
        ],
        "LB": [
            "tackles",
            "tackles_for_loss",
            "sacks",
            "passes_defended",
            "interceptions_defensive",
            "forced_fumbles",
        ],
        "DB": [
            "tackles",
            "interceptions_defensive",
            "passes_defended",
            "forced_fumbles",
        ],
    }

    # Expected stat value ranges per position
    STAT_RANGES = {
        "passing_attempts": (0, 600),
        "passing_completions": (0, 400),
        "passing_yards": (0, 5000),
        "passing_touchdowns": (0, 60),
        "interceptions_thrown": (0, 30),
        "rushing_attempts": (0, 400),
        "rushing_yards": (0, 2500),
        "rushing_touchdowns": (0, 30),
        "receiving_targets": (0, 200),
        "receiving_receptions": (0, 150),
        "receiving_yards": (0, 2000),
        "receiving_touchdowns": (0, 30),
        "kick_return_attempts": (0, 100),
        "kick_return_yards": (0, 3000),
        "tackles": (0, 200),
        "tackles_for_loss": (0, 50),
        "sacks": (0, 30),
        "passes_defended": (0, 50),
        "interceptions_defensive": (0, 15),
        "forced_fumbles": (0, 10),
        "games_started": (0, 20),
    }

    async def validate_staging_data(self, row: Dict) -> bool:
        """Validate CFR staging row.

        Args:
            row: CFR staging data row

        Returns:
            True if valid, False otherwise
        """
        # Required fields
        if not row.get("cfr_player_id"):
            self.logger.warning(f"CFR staging row {row.get('id')}: missing cfr_player_id")
            return False

        if not row.get("season"):
            self.logger.warning(f"CFR staging row {row.get('id')}: missing season")
            return False

        if not row.get("position"):
            self.logger.warning(f"CFR staging row {row.get('id')}: missing position")
            return False

        # Validate season range
        try:
            season = int(row["season"])
            if not (2010 <= season <= 2025):
                self.logger.warning(
                    f"CFR staging row {row.get('id')}: season {season} out of range"
                )
                return False
        except (ValueError, TypeError):
            self.logger.warning(
                f"CFR staging row {row.get('id')}: season not an integer"
            )
            return False

        # Validate position
        position = row.get("position", "").upper()
        if position not in self.POSITION_STAT_GROUPS:
            self.logger.warning(
                f"CFR staging row {row.get('id')}: unknown position {position}"
            )
            return False

        # Validate stat ranges for expected stats
        for stat_name, (min_val, max_val) in self.STAT_RANGES.items():
            if stat_name in row and row[stat_name] is not None:
                try:
                    stat_value = float(row[stat_name])
                    if not (min_val <= stat_value <= max_val):
                        self.logger.warning(
                            f"CFR staging row {row.get('id')}: {stat_name}={stat_value} out of range [{min_val}, {max_val}]"
                        )
                        return False
                except (ValueError, TypeError):
                    self.logger.warning(
                        f"CFR staging row {row.get('id')}: {stat_name} not numeric: {row[stat_name]}"
                    )
                    return False

        return True

    async def get_prospect_identity(self, row: Dict) -> Optional[Dict]:
        """Extract prospect identity from CFR data.

        Args:
            row: CFR staging data

        Returns:
            Dict with name, position, college, cfr_player_id or None
        """
        if not row.get("cfr_player_id"):
            return None

        # Parse name (may be "Last, First" format)
        full_name = row.get("name_full", "").strip()
        if not full_name:
            return None

        # Parse name components
        if "," in full_name:
            parts = full_name.split(",", 1)
            name_last = parts[0].strip()
            name_first = parts[1].strip() if len(parts) > 1 else ""
        else:
            # Assume "First Last" format
            parts = full_name.rsplit(" ", 1)
            name_first = parts[0] if len(parts) > 0 else ""
            name_last = parts[1] if len(parts) > 1 else ""

        return {
            "name_first": name_first,
            "name_last": name_last,
            "position": row.get("position", "").upper(),
            "college": row.get("college", ""),
            "cfr_player_id": str(row["cfr_player_id"]),
        }

    async def match_prospect(
        self, identity: Dict, entity_id: Optional[UUID] = None
    ) -> Optional[UUID]:
        """Match CFR prospect to existing prospect_core record.

        Strategy:
        1. Match by cfr_player_id in prospect_core.cfr_player_id
        2. Fuzzy name match (if no cfr_id match)
        3. Create new prospect if no match

        Args:
            identity: Prospect identity dict
            entity_id: Optional existing prospect to update

        Returns:
            UUID of matched/created prospect or None on error
        """
        from difflib import SequenceMatcher
        from sqlalchemy import text

        cfr_id = identity.get("cfr_player_id")
        if not cfr_id:
            return None

        # 1. Try exact match by cfr_player_id
        result = await self.db.execute(
            text(
                "SELECT id FROM prospect_core WHERE cfr_player_id = :cfr_id LIMIT 1"
            ),
            {"cfr_id": cfr_id},
        )
        prospect_id = result.scalar()
        if prospect_id:
            return UUID(prospect_id) if isinstance(prospect_id, str) else prospect_id

        # 2. Try fuzzy name match
        name_first = identity.get("name_first", "").lower()
        name_last = identity.get("name_last", "").lower()
        position = identity.get("position", "").upper()

        result = await self.db.execute(
            text(
                "SELECT id, name_first, name_last FROM prospect_core WHERE position = :position AND status = 'active' ORDER BY updated_at DESC LIMIT 50"
            ),
            {"position": position},
        )
        prospects = result.fetchall()

        best_match = None
        best_score = 0.0

        for prospect in prospects:
            prospect_first = (
                prospect[1].lower() if prospect[1] else ""
            )  # name_first
            prospect_last = prospect[2].lower() if prospect[2] else ""  # name_last

            # Calculate similarity
            first_similarity = SequenceMatcher(
                None, name_first, prospect_first
            ).ratio()
            last_similarity = SequenceMatcher(None, name_last, prospect_last).ratio()

            # Weight: last name more important (0.6) than first (0.4)
            combined_score = (last_similarity * 0.6) + (first_similarity * 0.4)

            if combined_score > best_score:
                best_score = combined_score
                best_match = prospect

        # Accept if > 80% match
        if best_match and best_score > 0.80:
            prospect_id = best_match[0]
            # Update cfr_player_id for future matches
            await self.db.execute(
                text(
                    "UPDATE prospect_core SET cfr_player_id = :cfr_id WHERE id = :id"
                ),
                {"cfr_id": cfr_id, "id": str(prospect_id)},
            )
            return UUID(prospect_id) if isinstance(prospect_id, str) else prospect_id

        # 3. Create new prospect
        new_prospect_id = UUID(
            str(
                (
                    await self.db.execute(
                        text(
                            """
                        INSERT INTO prospect_core 
                        (name_first, name_last, position, college, cfr_player_id, 
                         created_from_source, status)
                        VALUES (:name_first, :name_last, :position, :college, :cfr_id,
                                'cfr', 'active')
                        RETURNING id
                        """
                        ),
                        {
                            "name_first": name_first,
                            "name_last": name_last,
                            "position": position,
                            "college": identity.get("college", ""),
                            "cfr_id": cfr_id,
                        },
                    )
                ).scalar()
            )
        )

        return new_prospect_id

    async def transform_staging_to_canonical(
        self, staging_row: Dict, prospect_id: UUID
    ) -> TransformationResult:
        """Transform single CFR staging row to canonical fields.

        Wrapper for transform_row to match abstract method signature.

        Args:
            staging_row: Row from cfr_staging table
            prospect_id: UUID of matched/created prospect_core

        Returns:
            TransformationResult with field changes
        """
        return await self.transform_row(staging_row, prospect_id)

    async def transform_row(self, row: Dict, prospect_id: UUID) -> TransformationResult:
        """Transform CFR row to prospect_college_stats record.

        Args:
            row: CFR staging data
            prospect_id: Prospect ID

        Returns:
            TransformationResult with field changes
        """
        # Extract stats
        season = int(row.get("season", 0))
        position = row.get("position", "").upper()

        # Build field changes for all provided stats
        field_changes = []

        # Add season
        field_changes.append(
            FieldChange(
                field_name="season",
                value_current=season,
                value_previous=None,
                transformation_rule_id="extract_season",
                transformation_logic="Extract from CFR staging",
            )
        )

        # Add college
        college = row.get("college", "")
        if college:
            field_changes.append(
                FieldChange(
                    field_name="college",
                    value_current=college,
                    value_previous=None,
                    transformation_rule_id="extract_college",
                    transformation_logic="Extract from CFR staging",
                )
            )

        # Add position-specific stats
        expected_stats = self.POSITION_STAT_GROUPS.get(position, [])
        for stat_name in expected_stats:
            if stat_name in row and row[stat_name] is not None:
                # Normalize to Decimal for consistency
                try:
                    value = Decimal(str(row[stat_name]))
                except (ValueError, TypeError):
                    continue

                field_changes.append(
                    FieldChange(
                        field_name=stat_name,
                        value_current=value,
                        value_previous=None,
                        transformation_rule_id=f"cfr_{stat_name}",
                        transformation_logic=f"CFR {stat_name} from college season {season}",
                    )
                )

        # Add draft year if provided
        draft_year = row.get("draft_year")
        if draft_year:
            field_changes.append(
                FieldChange(
                    field_name="draft_year",
                    value_current=int(draft_year),
                    value_previous=None,
                    transformation_rule_id="extract_draft_year",
                    transformation_logic="Extract projected draft year from CFR",
                )
            )

        return TransformationResult(
            entity_type="prospect_college_stats",
            entity_id=prospect_id,
            field_changes=field_changes,
            extraction_id=None,
            source_system=self.SOURCE_NAME,
            source_row_id=row.get("id"),
            staged_from_table=self.STAGING_TABLE_NAME,
        )
