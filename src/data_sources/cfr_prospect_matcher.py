"""CFR-to-Prospect Matching Algorithm (CFR-002)

Three-tier matching strategy for linking College Football Reference scraped players
to existing prospect records with 95%+ accuracy:

1. EXACT MATCH: name + college + position (exact string match)
2. FUZZY MATCH: name similarity > 85% + college + position (handles variations)
3. MANUAL REVIEW: Flags unmatched prospects for manual review

Quality Targets:
- Exact matches: 85%+
- Fuzzy matches: 10%+
- Manual review queue: <5%
- False positives: 0%
"""

import logging
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple, Set
from uuid import UUID

logger = logging.getLogger(__name__)


@dataclass
class CFRMatchResult:
    """Result of a CFR-to-prospect matching operation."""

    cfr_player_id: str
    cfr_player_name: str
    prospect_id: Optional[UUID]
    prospect_name: Optional[str]
    match_type: str  # "exact", "fuzzy", "new", "unmatched"
    match_score: float  # 0-100 for fuzzy matches
    confidence: str  # "high", "medium", "low", "pending"
    reason: str  # Description of why this result
    manually_reviewed: bool = False
    reviewed_by: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "cfr_player_id": self.cfr_player_id,
            "cfr_player_name": self.cfr_player_name,
            "prospect_id": str(self.prospect_id) if self.prospect_id else None,
            "prospect_name": self.prospect_name,
            "match_type": self.match_type,
            "match_score": self.match_score,
            "confidence": self.confidence,
            "reason": self.reason,
            "manually_reviewed": self.manually_reviewed,
            "reviewed_by": self.reviewed_by,
            "notes": self.notes,
        }


class CFRProspectMatcher:
    """Three-tier matching algorithm for CFR players to existing prospects."""

    # Confidence thresholds
    EXACT_MATCH_THRESHOLD = 100  # Must be perfect match
    HIGH_CONFIDENCE_THRESHOLD = 95  # 95%+ similarity
    MEDIUM_CONFIDENCE_THRESHOLD = 85  # 85%+ similarity
    LOW_CONFIDENCE_THRESHOLD = 75  # 75%+ similarity (for logging only)

    # Match score weights for fuzzy matching
    LAST_NAME_WEIGHT = 0.6
    FIRST_NAME_WEIGHT = 0.4
    POSITION_BONUS = 10.0  # Points added if position matches
    COLLEGE_BONUS = 5.0  # Points added if college matches exactly

    @staticmethod
    def normalize_name(name: str) -> str:
        """
        Normalize name for comparison.

        Handles:
        - Case differences
        - Whitespace
        - Common suffixes (Jr., Sr., II, III, etc.)
        - Leading/trailing spaces

        Args:
            name: Name to normalize (can be "Last, First" or "First Last")

        Returns:
            Normalized name in "First Last" format
        """
        if not name:
            return ""

        # Convert to lowercase
        name = name.lower().strip()

        # If format is "Last, First", convert to "First Last"
        if "," in name:
            parts = name.split(",", 1)
            last = parts[0].strip()
            first = parts[1].strip() if len(parts) > 1 else ""
            name = f"{first} {last}".strip()

        # Remove common suffixes (remove in multiple passes to handle multiple suffixes)
        suffixes = [" jr.", " sr.", " ii.", " iii.", " iv.", " v.", " jr", " sr", " ii", " iii", " iv", " v"]
        max_iterations = 5  # Prevent infinite loops
        for _ in range(max_iterations):
            found_suffix = False
            for suffix in suffixes:
                if name.endswith(suffix):
                    name = name[: -len(suffix)].strip()
                    found_suffix = True
                    break
            if not found_suffix:
                break  # No more suffixes found

        # Remove extra whitespace
        name = " ".join(name.split())

        return name

    @staticmethod
    def normalize_college(college: str) -> str:
        """
        Normalize college name for comparison.

        Handles:
        - Case differences
        - Common abbreviations (TX=Texas, A&M=Texas A&M, etc.)
        - Whitespace

        Args:
            college: College name to normalize

        Returns:
            Normalized college name
        """
        if not college:
            return ""

        college = college.lower().strip()

        # Common abbreviation replacements (only for exact word matches)
        replacements = {
            "tx": "texas",
            "a&m": "texas a&m",
            "ole miss": "mississippi",
            "u of florida": "florida",
            "fla": "florida",
            "fl": "florida",
            "penn st": "penn state",
            "penn st.": "penn state",
            "ok": "oklahoma",
            "okla": "oklahoma",
            "nc state": "north carolina state",
            "nc": "north carolina",
            "sc": "south carolina",
            "unc": "north carolina",
            "usc": "southern california",
            "so. cal": "southern california",
            "msu": "michigan state",
            "u of m": "michigan",
            "osu": "ohio state",
            "lsu": "louisiana state",
            "la": "louisiana",
            "umd": "maryland",
            "gtech": "georgia tech",
            "ga tech": "georgia tech",
            "va tech": "virginia tech",
            "vt": "virginia tech",
            "byu": "brigham young",
            "unlv": "nevada las vegas",
        }

        # Try exact match first
        if college in replacements:
            college = replacements[college]
        else:
            # Try substring replacement only if it's a complete word
            # Split by spaces and check each word/phrase
            for abbrev, full in replacements.items():
                # Only replace if abbrev appears as a separate token
                # to avoid "texas a&m" matching "a&m" key
                if college == abbrev or (
                    " " + abbrev in " " + college + " "
                    and abbrev not in ["a&m"]  # Exclude problematic abbreviations
                ):
                    college = college.replace(" " + abbrev, " " + full)
                    if college.startswith(abbrev + " "):
                        college = college.replace(abbrev + " ", full + " ")

        # Remove extra whitespace
        college = " ".join(college.split())

        return college


    @staticmethod
    def calculate_name_similarity(name1: str, name2: str) -> float:
        """
        Calculate similarity score between two names (0-100).

        Handles:
        - Full name comparison (matching whole names first)
        - Last name-only matching
        - First name-only matching
        - Takes the best of these approaches

        Args:
            name1: First name
            name2: Second name

        Returns:
            Similarity score (0-100)
        """
        n1 = CFRProspectMatcher.normalize_name(name1)
        n2 = CFRProspectMatcher.normalize_name(name2)

        if not n1 or not n2:
            return 0.0

        # Exact match
        if n1 == n2:
            return 100.0

        # Split into first and last names
        n1_parts = n1.split()
        n2_parts = n2.split()

        n1_first = n1_parts[0] if n1_parts else ""
        n1_last = n1_parts[-1] if len(n1_parts) > 1 else (n1_parts[0] if n1_parts else "")

        n2_first = n2_parts[0] if n2_parts else ""
        n2_last = n2_parts[-1] if len(n2_parts) > 1 else (n2_parts[0] if n2_parts else "")

        # Calculate similarity ratios
        full_similarity = SequenceMatcher(None, n1, n2).ratio() * 100

        # Last name is more important (60% weight)
        last_similarity = SequenceMatcher(None, n1_last, n2_last).ratio() * 100
        first_similarity = SequenceMatcher(None, n1_first, n2_first).ratio() * 100

        weighted_score = (last_similarity * CFRProspectMatcher.LAST_NAME_WEIGHT) + (
            first_similarity * CFRProspectMatcher.FIRST_NAME_WEIGHT
        )

        # Return the better of full match or weighted approach
        return max(full_similarity, weighted_score)

    @staticmethod
    def exact_match(
        cfr_name: str,
        cfr_college: str,
        cfr_position: str,
        existing_prospects: List[Dict],
    ) -> Optional[Dict]:
        """
        Tier 1: Exact matching on name + college + position.

        Args:
            cfr_name: CFR player name
            cfr_college: CFR player college
            cfr_position: CFR player position
            existing_prospects: List of existing prospect dicts with
                               id, name, college, position

        Returns:
            Matching prospect dict or None
        """
        norm_cfr_name = CFRProspectMatcher.normalize_name(cfr_name)
        norm_cfr_college = CFRProspectMatcher.normalize_college(cfr_college)
        norm_cfr_position = cfr_position.upper().strip()

        for prospect in existing_prospects:
            prospect_name = prospect.get("name", "")
            prospect_college = prospect.get("college", "")
            prospect_position = prospect.get("position", "").upper().strip()

            norm_prospect_name = CFRProspectMatcher.normalize_name(prospect_name)
            norm_prospect_college = CFRProspectMatcher.normalize_college(prospect_college)
            norm_prospect_position = prospect_position  # Position already normalized

            # Exact match on all three fields
            if (
                norm_cfr_name == norm_prospect_name
                and norm_cfr_college == norm_prospect_college
                and norm_cfr_position == norm_prospect_position
            ):
                logger.info(
                    f"EXACT MATCH: CFR '{cfr_name}' ({cfr_college}, {cfr_position}) "
                    f"→ Prospect '{prospect_name}' (ID: {prospect.get('id')})"
                )
                return prospect

        return None

    @staticmethod
    def fuzzy_match(
        cfr_name: str,
        cfr_college: str,
        cfr_position: str,
        existing_prospects: List[Dict],
        threshold: int = MEDIUM_CONFIDENCE_THRESHOLD,
    ) -> Optional[Tuple[Dict, float]]:
        """
        Tier 2: Fuzzy matching on name similarity with college + position constraints.

        Strategy:
        1. Filter prospects by college + position (if available)
        2. Calculate name similarity for filtered prospects
        3. Accept if similarity > threshold
        4. Return best match

        Args:
            cfr_name: CFR player name
            cfr_college: CFR player college
            cfr_position: CFR player position
            existing_prospects: List of existing prospect dicts
            threshold: Minimum name similarity score (0-100)

        Returns:
            Tuple of (matching prospect dict, match_score) or None
        """
        norm_cfr_college = CFRProspectMatcher.normalize_college(cfr_college)
        norm_cfr_position = cfr_position.upper().strip()

        best_prospect = None
        best_score = 0.0

        for prospect in existing_prospects:
            prospect_college = prospect.get("college", "")
            prospect_position = prospect.get("position", "").upper().strip()
            prospect_name = prospect.get("name", "")

            norm_prospect_college = CFRProspectMatcher.normalize_college(prospect_college)

            # Filter by position (must match exactly)
            if norm_cfr_position != prospect_position:
                continue

            # Filter by college (prefer exact match, but allow fuzzy if no exact)
            if norm_prospect_college != norm_cfr_college:
                # College mismatch - might still match if name is very high confidence
                # But require higher name similarity (90%+ instead of 85%+)
                if threshold <= CFRProspectMatcher.MEDIUM_CONFIDENCE_THRESHOLD:
                    threshold = CFRProspectMatcher.HIGH_CONFIDENCE_THRESHOLD

            # Calculate name similarity
            name_score = CFRProspectMatcher.calculate_name_similarity(
                cfr_name, prospect_name
            )

            # Track best match
            if name_score > best_score:
                best_score = name_score
                best_prospect = prospect

        # Accept if above threshold
        if best_prospect and best_score >= threshold:
            logger.info(
                f"FUZZY MATCH ({best_score:.1f}%): CFR '{cfr_name}' "
                f"({cfr_college}, {cfr_position}) → Prospect "
                f"'{best_prospect.get('name')}' (ID: {best_prospect.get('id')})"
            )
            return (best_prospect, best_score)

        if best_prospect and best_score >= CFRProspectMatcher.LOW_CONFIDENCE_THRESHOLD:
            logger.debug(
                f"PARTIAL MATCH ({best_score:.1f}%, below threshold {threshold}): "
                f"CFR '{cfr_name}' → Prospect '{best_prospect.get('name')}'"
            )

        return None

    @staticmethod
    def match(
        cfr_player: Dict,
        existing_prospects: List[Dict],
        allow_new_prospect: bool = False,
    ) -> CFRMatchResult:
        """
        Execute three-tier matching strategy.

        Tiers:
        1. Exact match (name + college + position)
        2. Fuzzy match (name similarity > 85% + college + position)
        3. Manual review flag (or create new prospect if allowed)

        Args:
            cfr_player: CFR player dict with cfr_player_id, name, college, position
            existing_prospects: List of existing prospects to match against
            allow_new_prospect: If True, create new prospect record instead of flagging

        Returns:
            CFRMatchResult with match details
        """
        cfr_id = cfr_player.get("cfr_player_id", "")
        cfr_name = cfr_player.get("name", "")
        cfr_college = cfr_player.get("college", "")
        cfr_position = cfr_player.get("position", "")

        if not cfr_id or not cfr_name or not cfr_college or not cfr_position:
            return CFRMatchResult(
                cfr_player_id=cfr_id,
                cfr_player_name=cfr_name,
                prospect_id=None,
                prospect_name=None,
                match_type="unmatched",
                match_score=0.0,
                confidence="pending",
                reason="Missing required CFR player fields (id, name, college, position)",
            )

        # Tier 1: Exact Match
        exact_match_prospect = CFRProspectMatcher.exact_match(
            cfr_name, cfr_college, cfr_position, existing_prospects
        )
        if exact_match_prospect:
            return CFRMatchResult(
                cfr_player_id=cfr_id,
                cfr_player_name=cfr_name,
                prospect_id=UUID(exact_match_prospect["id"])
                if isinstance(exact_match_prospect["id"], str)
                else exact_match_prospect["id"],
                prospect_name=exact_match_prospect.get("name"),
                match_type="exact",
                match_score=100.0,
                confidence="high",
                reason="Exact match on name + college + position",
            )

        # Tier 2: Fuzzy Match (85%+ similarity)
        fuzzy_result = CFRProspectMatcher.fuzzy_match(
            cfr_name,
            cfr_college,
            cfr_position,
            existing_prospects,
            threshold=CFRProspectMatcher.MEDIUM_CONFIDENCE_THRESHOLD,
        )
        if fuzzy_result:
            fuzzy_prospect, fuzzy_score = fuzzy_result
            confidence = "high" if fuzzy_score >= 95 else "medium"
            return CFRMatchResult(
                cfr_player_id=cfr_id,
                cfr_player_name=cfr_name,
                prospect_id=UUID(fuzzy_prospect["id"])
                if isinstance(fuzzy_prospect["id"], str)
                else fuzzy_prospect["id"],
                prospect_name=fuzzy_prospect.get("name"),
                match_type="fuzzy",
                match_score=fuzzy_score,
                confidence=confidence,
                reason=f"Fuzzy name match ({fuzzy_score:.1f}%) with college + position",
            )

        # Tier 3: Manual Review (or create new)
        if allow_new_prospect:
            return CFRMatchResult(
                cfr_player_id=cfr_id,
                cfr_player_name=cfr_name,
                prospect_id=None,  # Will be assigned on creation
                prospect_name=cfr_name,
                match_type="new",
                match_score=0.0,
                confidence="pending",
                reason="No match found - creating new prospect record",
            )

        return CFRMatchResult(
            cfr_player_id=cfr_id,
            cfr_player_name=cfr_name,
            prospect_id=None,
            prospect_name=None,
            match_type="unmatched",
            match_score=0.0,
            confidence="pending",
            reason="No match found - flagged for manual review",
        )

    @staticmethod
    def batch_match(
        cfr_players: List[Dict],
        existing_prospects: List[Dict],
        allow_new_prospects: bool = False,
    ) -> Dict:
        """
        Batch match multiple CFR players to prospects.

        Args:
            cfr_players: List of CFR player dicts
            existing_prospects: List of existing prospects
            allow_new_prospects: If True, create new prospects instead of flagging

        Returns:
            Dict with results and statistics
        """
        results = []
        stats = {
            "total": len(cfr_players),
            "exact_matches": 0,
            "fuzzy_matches": 0,
            "new_prospects": 0,
            "unmatched": 0,
        }

        for cfr_player in cfr_players:
            result = CFRProspectMatcher.match(
                cfr_player, existing_prospects, allow_new_prospects
            )
            results.append(result)

            # Update statistics
            if result.match_type == "exact":
                stats["exact_matches"] += 1
            elif result.match_type == "fuzzy":
                stats["fuzzy_matches"] += 1
            elif result.match_type == "new":
                stats["new_prospects"] += 1
            elif result.match_type == "unmatched":
                stats["unmatched"] += 1

        # Log summary
        exact_pct = (stats["exact_matches"] / stats["total"] * 100) if stats["total"] > 0 else 0
        fuzzy_pct = (stats["fuzzy_matches"] / stats["total"] * 100) if stats["total"] > 0 else 0
        unmatched_pct = (stats["unmatched"] / stats["total"] * 100) if stats["total"] > 0 else 0

        logger.info(
            f"Batch match complete: {stats['exact_matches']} exact ({exact_pct:.1f}%), "
            f"{stats['fuzzy_matches']} fuzzy ({fuzzy_pct:.1f}%), "
            f"{stats['unmatched']} unmatched ({unmatched_pct:.1f}%)"
        )

        return {
            "results": results,
            "stats": stats,
        }

    @staticmethod
    def get_unmatched_prospects(batch_result: Dict) -> List[Dict]:
        """
        Extract unmatched prospects from batch matching results.

        Useful for creating manual review queue.

        Args:
            batch_result: Result dict from batch_match()

        Returns:
            List of CFR players that need manual review
        """
        unmatched = []
        for result in batch_result["results"]:
            if result.match_type == "unmatched":
                unmatched.append(
                    {
                        "cfr_player_id": result.cfr_player_id,
                        "cfr_player_name": result.cfr_player_name,
                        "reason": result.reason,
                    }
                )
        return unmatched

    @staticmethod
    def generate_match_report(batch_result: Dict) -> str:
        """
        Generate human-readable matching report.

        Args:
            batch_result: Result dict from batch_match()

        Returns:
            Formatted report string
        """
        stats = batch_result["stats"]
        total = stats["total"]

        exact_pct = (stats["exact_matches"] / total * 100) if total > 0 else 0
        fuzzy_pct = (stats["fuzzy_matches"] / total * 100) if total > 0 else 0
        new_pct = (stats["new_prospects"] / total * 100) if total > 0 else 0
        unmatched_pct = (stats["unmatched"] / total * 100) if total > 0 else 0

        report = f"""
═══════════════════════════════════════════════════════════════
CFR PROSPECT MATCHING REPORT
═══════════════════════════════════════════════════════════════

Total Prospects Processed: {total}

MATCH RESULTS:
  • Exact Matches:        {stats['exact_matches']:4d} ({exact_pct:5.1f}%) ✓
  • Fuzzy Matches:        {stats['fuzzy_matches']:4d} ({fuzzy_pct:5.1f}%) ✓
  • New Prospects:        {stats['new_prospects']:4d} ({new_pct:5.1f}%)
  • Manual Review Queue:  {stats['unmatched']:4d} ({unmatched_pct:5.1f}%)

QUALITY METRICS:
  • Matched (Exact + Fuzzy): {stats['exact_matches'] + stats['fuzzy_matches']} ({(stats['exact_matches'] + stats['fuzzy_matches']) / total * 100 if total > 0 else 0:.1f}%)
  • Target: ≥ 95%
  • Status: {'✓ PASS' if ((stats['exact_matches'] + stats['fuzzy_matches']) / total * 100) >= 95 else '✗ BELOW TARGET'}

═══════════════════════════════════════════════════════════════
"""

        return report
