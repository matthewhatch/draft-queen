"""
PFF Data Validation Framework

Validates prospect data from PFF.com including:
- Grade validation (0-100 scale)
- Position code validation
- Required field checks
- Data type and format validation
"""

import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class GradeValidator:
    """Validates prospect grades"""

    MIN_GRADE = 0.0
    MAX_GRADE = 100.0

    @staticmethod
    def validate_grade(grade: Optional[str]) -> Tuple[bool, Optional[str]]:
        """
        Validate prospect grade value
        
        Args:
            grade: Grade value (string representation of 0-100)
            
        Returns:
            (is_valid, error_message)
        """
        if grade is None or grade == "":
            return True, None  # Missing grades acceptable

        try:
            grade_val = float(grade)

            if grade_val < GradeValidator.MIN_GRADE:
                return False, f"Grade below minimum ({grade_val} < {GradeValidator.MIN_GRADE})"

            if grade_val > GradeValidator.MAX_GRADE:
                return False, f"Grade above maximum ({grade_val} > {GradeValidator.MAX_GRADE})"

            return True, None

        except (ValueError, TypeError) as e:
            return False, f"Invalid grade format: {grade} ({e})"

    @staticmethod
    def normalize_grade(grade: Optional[str]) -> Optional[float]:
        """
        Normalize grade to float value
        
        Args:
            grade: Grade value
            
        Returns:
            Float grade value or None if invalid/missing
        """
        if not grade:
            return None

        is_valid, _ = GradeValidator.validate_grade(grade)
        if not is_valid:
            return None

        try:
            return float(grade)
        except (ValueError, TypeError):
            return None


class PositionValidator:
    """Validates prospect position codes"""

    VALID_POSITIONS = {
        # Offense
        "QB", "RB", "FB", "WR", "TE",
        # Offensive Line
        "LT", "LG", "C", "RG", "RT", "OT", "OL",
        # Defense
        "DT", "DE", "EDGE", "LB", "CB", "S", "SS", "FS", "DB",
        # Special Teams
        "K", "P", "LS",
    }

    @staticmethod
    def validate_position(position: Optional[str]) -> Tuple[bool, Optional[str]]:
        """
        Validate prospect position code
        
        Args:
            position: Position code (e.g., 'CB', 'EDGE')
            
        Returns:
            (is_valid, error_message)
        """
        if position is None or position == "":
            return True, None  # Missing positions acceptable

        pos_upper = position.upper().strip()

        if pos_upper not in PositionValidator.VALID_POSITIONS:
            return False, f"Invalid position code: {position}"

        return True, None

    @staticmethod
    def normalize_position(position: Optional[str]) -> Optional[str]:
        """
        Normalize position to standard code
        
        Args:
            position: Position value
            
        Returns:
            Normalized position code or None if invalid
        """
        if not position:
            return None

        is_valid, _ = PositionValidator.validate_position(position)
        if not is_valid:
            return None

        return position.upper().strip()


class SchoolValidator:
    """Validates prospect school names"""

    @staticmethod
    def validate_school(school: Optional[str]) -> Tuple[bool, Optional[str]]:
        """
        Validate prospect school name
        
        Args:
            school: School name
            
        Returns:
            (is_valid, error_message)
        """
        if school is None or school == "":
            return True, None  # Missing school acceptable

        # School name should be at least 2 characters
        if len(school.strip()) < 2:
            return False, f"School name too short: {school}"

        return True, None

    @staticmethod
    def normalize_school(school: Optional[str]) -> Optional[str]:
        """
        Normalize school name
        
        Args:
            school: School name
            
        Returns:
            Normalized school name or None if invalid
        """
        if not school:
            return None

        is_valid, _ = SchoolValidator.validate_school(school)
        if not is_valid:
            return None

        return school.strip()


class ProspectValidator:
    """Validates complete prospect records"""

    REQUIRED_FIELDS = {"name"}  # Only name is required

    @staticmethod
    def validate_prospect(prospect: Dict) -> Tuple[bool, Optional[List[str]]]:
        """
        Validate complete prospect record
        
        Args:
            prospect: Prospect dictionary
            
        Returns:
            (is_valid, list_of_error_messages)
        """
        errors = []

        # Check required fields
        for field in ProspectValidator.REQUIRED_FIELDS:
            if not prospect.get(field):
                errors.append(f"Missing required field: {field}")

        # Validate name (if present)
        if prospect.get("name"):
            name = prospect["name"].strip()
            if len(name) < 2:
                errors.append(f"Prospect name too short: {name}")

        # Validate grade
        if prospect.get("grade"):
            is_valid, error = GradeValidator.validate_grade(prospect["grade"])
            if not is_valid:
                errors.append(f"Invalid grade: {error}")

        # Validate position
        if prospect.get("position"):
            is_valid, error = PositionValidator.validate_position(prospect["position"])
            if not is_valid:
                errors.append(f"Invalid position: {error}")

        # Validate school
        if prospect.get("school"):
            is_valid, error = SchoolValidator.validate_school(prospect["school"])
            if not is_valid:
                errors.append(f"Invalid school: {error}")

        return len(errors) == 0, errors if errors else None

    @staticmethod
    def normalize_prospect(prospect: Dict) -> Dict:
        """
        Normalize prospect data to standard format
        
        Args:
            prospect: Raw prospect dictionary
            
        Returns:
            Normalized prospect dictionary
        """
        normalized = {
            "name": prospect.get("name", "").strip() if prospect.get("name") else None,
            "position": PositionValidator.normalize_position(prospect.get("position")),
            "school": SchoolValidator.normalize_school(prospect.get("school")),
            "class": prospect.get("class", "").strip() if prospect.get("class") else None,
            "grade": GradeValidator.normalize_grade(prospect.get("grade")),
        }

        # Add optional fields
        for key in ["rank", "scraped_at"]:
            if key in prospect:
                normalized[key] = prospect[key]

        return normalized

    @staticmethod
    def validate_and_normalize(prospect: Dict) -> Tuple[bool, Optional[Dict]]:
        """
        Validate and normalize prospect in one operation
        
        Args:
            prospect: Raw prospect dictionary
            
        Returns:
            (is_valid, normalized_prospect or error_list)
        """
        is_valid, errors = ProspectValidator.validate_prospect(prospect)

        if not is_valid:
            return False, errors

        try:
            normalized = ProspectValidator.normalize_prospect(prospect)
            return True, normalized
        except Exception as e:
            return False, [f"Normalization error: {e}"]


class ProspectBatchValidator:
    """Validates batches of prospects"""

    @staticmethod
    def validate_batch(prospects: List[Dict]) -> Dict:
        """
        Validate batch of prospects
        
        Args:
            prospects: List of prospect dictionaries
            
        Returns:
            Validation report with statistics
        """
        report = {
            "total": len(prospects),
            "valid": 0,
            "invalid": 0,
            "errors": [],
        }

        for i, prospect in enumerate(prospects):
            is_valid, errors = ProspectValidator.validate_prospect(prospect)

            if is_valid:
                report["valid"] += 1
            else:
                report["invalid"] += 1
                report["errors"].append({
                    "prospect": prospect.get("name", f"Row {i}"),
                    "errors": errors,
                })

        return report

    @staticmethod
    def filter_and_normalize(prospects: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Filter valid prospects and normalize them
        
        Args:
            prospects: List of raw prospect dictionaries
            
        Returns:
            (valid_normalized_prospects, invalid_prospects)
        """
        valid = []
        invalid = []

        for prospect in prospects:
            is_valid, result = ProspectValidator.validate_and_normalize(prospect)

            if is_valid:
                valid.append(result)
            else:
                invalid.append({
                    "original": prospect,
                    "errors": result,
                })

        return valid, invalid


# ============================================================================
# PFF-specific validators for grade integration (US-041)
# ============================================================================

PFF_TO_DB_POSITION_MAP = {
    "LT": "OL", "LG": "OL", "C": "OL", "RG": "OL", "RT": "OL", "OT": "OL",
    "DT": "DL", "DE": "DL",
    "SS": "DB", "FS": "DB", "CB": "DB",
    "EDGE": "EDGE", "LB": "LB",
    "QB": "QB", "RB": "RB", "FB": "FB", "WR": "WR", "TE": "TE",
    "K": "K", "P": "P", "LS": "OL",
}


def map_pff_position_to_db(pff_position: str) -> Optional[str]:
    """Map a PFF-native position to a DB-compatible position code.
    
    Args:
        pff_position: PFF position (e.g., 'LT', 'CB', 'EDGE')
        
    Returns:
        DB-compatible position or None if unmappable
    """
    if not pff_position:
        return None
    return PFF_TO_DB_POSITION_MAP.get(pff_position.upper().strip())


def normalize_pff_grade(pff_grade: float) -> float:
    """Convert PFF 0–100 grade to 5.0–10.0 scale.
    
    Formula: normalized = 5.0 + (pff_grade / 100.0) * 5.0
    - PFF 0 → 5.0
    - PFF 50 → 7.5
    - PFF 100 → 10.0
    
    Args:
        pff_grade: Raw PFF grade (0-100)
        
    Returns:
        Normalized grade (5.0-10.0)
    """
    clamped = max(0.0, min(100.0, float(pff_grade)))
    return round(5.0 + (clamped / 100.0) * 5.0, 1)


class PFFDataValidator:
    """Validators for PFF prospect data (grade integration)."""
    
    @staticmethod
    def validate_batch(prospects: List[Dict]) -> List[Dict]:
        """Validate and filter PFF prospects for grade loading.
        
        Args:
            prospects: List of raw PFF prospect dicts
            
        Returns:
            List of validated prospects (filtered for required fields)
        """
        validated = []
        for prospect in prospects:
            # Check required fields for grade integration
            if not prospect.get("name") or not prospect.get("grade"):
                logger.debug(f"Skipping prospect missing name or grade: {prospect.get('name', 'UNKNOWN')}")
                continue
            validated.append(prospect)
        return validated
