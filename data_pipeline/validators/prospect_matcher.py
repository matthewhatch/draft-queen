"""Fuzzy matching utilities for prospect deduplication across data sources."""

import logging
from typing import List, Dict, Tuple, Optional
from rapidfuzz import fuzz
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    """Result of a fuzzy match operation."""

    prospect_id: int
    prospect_name: str
    match_score: float  # 0-100
    is_match: bool  # True if above threshold
    confidence: str  # "high", "medium", "low"


class ProspectMatcher:
    """Fuzzy matching for prospect deduplication and linking."""

    # Thresholds for different match confidence levels
    HIGH_CONFIDENCE_THRESHOLD = 95
    MEDIUM_CONFIDENCE_THRESHOLD = 85
    LOW_CONFIDENCE_THRESHOLD = 75

    @staticmethod
    def calculate_name_similarity(name1: str, name2: str) -> float:
        """
        Calculate similarity score between two names (0-100).

        Uses token_set_ratio which handles partial matches and word order differences.

        Args:
            name1: First name
            name2: Second name

        Returns:
            Similarity score (0-100)
        """
        # Normalize names
        n1 = ProspectMatcher._normalize_name(name1)
        n2 = ProspectMatcher._normalize_name(name2)

        # Use token_set_ratio for flexible matching
        score = fuzz.token_set_ratio(n1, n2)
        logger.debug(f"Name similarity '{name1}' vs '{name2}': {score}")

        return score

    @staticmethod
    def _normalize_name(name: str) -> str:
        """
        Normalize name for comparison.

        Handles:
        - Case differences
        - Whitespace
        - Common suffixes (Jr., Sr., II, III, etc.)
        - Initials

        Args:
            name: Name to normalize

        Returns:
            Normalized name
        """
        # Convert to lowercase
        name = name.lower().strip()

        # Remove common suffixes
        suffixes = [" jr.", " sr.", " i.", " ii.", " iii.", " iv.", " v."]
        for suffix in suffixes:
            if name.endswith(suffix):
                name = name[: -len(suffix)].strip()

        # Remove extra whitespace
        name = " ".join(name.split())

        return name

    @staticmethod
    def find_best_match(
        prospect_name: str,
        existing_prospects: List[Dict],
        threshold: int = MEDIUM_CONFIDENCE_THRESHOLD,
    ) -> Optional[MatchResult]:
        """
        Find best matching existing prospect for a new prospect.

        Args:
            prospect_name: Name of prospect to match
            existing_prospects: List of existing prospects with 'id' and 'name'
            threshold: Minimum match score to consider a match

        Returns:
            MatchResult with best match or None if no good match found
        """
        if not existing_prospects:
            return None

        best_score = 0
        best_prospect = None

        for prospect in existing_prospects:
            score = ProspectMatcher.calculate_name_similarity(
                prospect_name, prospect.get("name", "")
            )

            if score > best_score:
                best_score = score
                best_prospect = prospect

        if best_score < threshold:
            logger.debug(
                f"No match found for '{prospect_name}' (best score: {best_score})"
            )
            return None

        # Determine confidence level
        if best_score >= ProspectMatcher.HIGH_CONFIDENCE_THRESHOLD:
            confidence = "high"
        elif best_score >= ProspectMatcher.MEDIUM_CONFIDENCE_THRESHOLD:
            confidence = "medium"
        else:
            confidence = "low"

        result = MatchResult(
            prospect_id=best_prospect.get("id"),
            prospect_name=best_prospect.get("name", ""),
            match_score=best_score,
            is_match=True,
            confidence=confidence,
        )

        logger.info(
            f"Found {confidence} confidence match for '{prospect_name}': "
            f"{result.prospect_name} (score: {best_score})"
        )

        return result

    @staticmethod
    def find_all_matches(
        prospect_name: str,
        existing_prospects: List[Dict],
        threshold: int = LOW_CONFIDENCE_THRESHOLD,
    ) -> List[MatchResult]:
        """
        Find all potential matches for a prospect (ranked by score).

        Args:
            prospect_name: Name of prospect to match
            existing_prospects: List of existing prospects
            threshold: Minimum match score to include

        Returns:
            List of MatchResult objects sorted by score (descending)
        """
        results = []

        for prospect in existing_prospects:
            score = ProspectMatcher.calculate_name_similarity(
                prospect_name, prospect.get("name", "")
            )

            if score >= threshold:
                # Determine confidence
                if score >= ProspectMatcher.HIGH_CONFIDENCE_THRESHOLD:
                    confidence = "high"
                elif score >= ProspectMatcher.MEDIUM_CONFIDENCE_THRESHOLD:
                    confidence = "medium"
                else:
                    confidence = "low"

                result = MatchResult(
                    prospect_id=prospect.get("id"),
                    prospect_name=prospect.get("name", ""),
                    match_score=score,
                    is_match=True,
                    confidence=confidence,
                )
                results.append(result)

        # Sort by score descending
        results.sort(key=lambda r: r.match_score, reverse=True)

        logger.info(
            f"Found {len(results)} potential matches for '{prospect_name}' above threshold {threshold}"
        )

        return results

    @staticmethod
    def deduplicate_prospects(prospects: List[Dict]) -> Tuple[List[Dict], Dict]:
        """
        Remove duplicate prospects from list using fuzzy matching.

        Args:
            prospects: List of prospects (with 'name' and optional 'id' fields)

        Returns:
            Tuple of (unique_prospects, duplicates_found)
            duplicates_found maps prospect index to matched prospect index
        """
        unique = []
        duplicates = {}

        for idx, prospect in enumerate(prospects):
            # Check if this prospect matches any already-unique prospects
            match = ProspectMatcher.find_best_match(
                prospect.get("name", ""),
                unique,
                threshold=ProspectMatcher.HIGH_CONFIDENCE_THRESHOLD,
            )

            if match:
                # This is a duplicate - record the mapping
                duplicates[idx] = match.prospect_id
                logger.debug(
                    f"Prospect '{prospect.get('name')}' is duplicate of "
                    f"'{match.prospect_name}' (score: {match.match_score})"
                )
            else:
                # This is unique
                unique.append(prospect)

        logger.info(
            f"Deduplication complete: {len(unique)} unique from {len(prospects)} total "
            f"({len(duplicates)} duplicates removed)"
        )

        return unique, duplicates

    @staticmethod
    def match_across_sources(
        new_prospect: Dict,
        existing_prospects: List[Dict],
        position_weight: float = 0.3,
        college_weight: float = 0.1,
    ) -> Optional[MatchResult]:
        """
        Match prospect across sources using name + contextual information.

        Args:
            new_prospect: New prospect from one source (name, position, college)
            existing_prospects: List of existing prospects
            position_weight: Weight for position match (0-1)
            college_weight: Weight for college match (0-1)

        Returns:
            MatchResult with best match or None
        """
        if not existing_prospects:
            return None

        best_score = 0
        best_prospect = None

        for prospect in existing_prospects:
            # Name similarity (base score)
            name_score = ProspectMatcher.calculate_name_similarity(
                new_prospect.get("name", ""), prospect.get("name", "")
            )

            # Position bonus
            position_bonus = 0
            if (
                new_prospect.get("position") == prospect.get("position")
                and new_prospect.get("position")
            ):
                position_bonus = 10 * position_weight

            # College bonus
            college_bonus = 0
            if (
                new_prospect.get("college", "").lower()
                == prospect.get("college", "").lower()
                and new_prospect.get("college")
            ):
                college_bonus = 5 * college_weight

            # Combined score (cap at 100)
            combined_score = min(100, name_score + position_bonus + college_bonus)

            if combined_score > best_score:
                best_score = combined_score
                best_prospect = prospect

        if best_score < ProspectMatcher.MEDIUM_CONFIDENCE_THRESHOLD:
            return None

        # Determine confidence
        if best_score >= ProspectMatcher.HIGH_CONFIDENCE_THRESHOLD:
            confidence = "high"
        elif best_score >= ProspectMatcher.MEDIUM_CONFIDENCE_THRESHOLD:
            confidence = "medium"
        else:
            confidence = "low"

        result = MatchResult(
            prospect_id=best_prospect.get("id"),
            prospect_name=best_prospect.get("name", ""),
            match_score=best_score,
            is_match=True,
            confidence=confidence,
        )

        logger.info(
            f"Cross-source match: '{new_prospect.get('name')}' ({new_prospect.get('position')}, "
            f"{new_prospect.get('college')}) → '{result.prospect_name}' (score: {best_score})"
        )

        return result
