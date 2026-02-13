"""Data validation framework for the pipeline."""

from typing import Tuple, List, Dict, Any
from pydantic import ValidationError
from data_pipeline.models import ProspectDataSchema
import logging

logger = logging.getLogger(__name__)


class ValidationResult:
    """Result of a validation operation."""

    def __init__(self, is_valid: bool, errors: List[str] = None, warnings: List[str] = None):
        """Initialize validation result."""
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []

    @property
    def has_issues(self) -> bool:
        """Check if there are any issues (errors or warnings)."""
        return len(self.errors) > 0 or len(self.warnings) > 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
        }


class SchemaValidator:
    """Validates data against Pydantic schemas."""

    @staticmethod
    def validate_prospect(data: Dict[str, Any]) -> ValidationResult:
        """
        Validate prospect data against schema.

        Args:
            data: Raw prospect data dictionary

        Returns:
            ValidationResult with any errors
        """
        errors = []

        try:
            # Validate against Pydantic schema
            prospect = ProspectDataSchema(**data)
            logger.debug(f"Prospect validation passed: {prospect.name}")
            return ValidationResult(is_valid=True)

        except ValidationError as e:
            # Extract Pydantic validation errors
            for error in e.errors():
                field = ".".join(str(x) for x in error["loc"])
                msg = error["msg"]
                errors.append(f"{field}: {msg}")

            logger.warning(f"Prospect validation failed: {errors}")
            return ValidationResult(is_valid=False, errors=errors)

        except Exception as e:
            error_msg = f"Unexpected validation error: {str(e)}"
            logger.error(error_msg)
            return ValidationResult(is_valid=False, errors=[error_msg])

    @staticmethod
    def validate_batch(data_list: List[Dict[str, Any]]) -> Tuple[int, int, int, List[Dict]]:
        """
        Validate a batch of prospect records.

        Args:
            data_list: List of raw prospect data dictionaries

        Returns:
            Tuple of (total, valid, invalid, errors)
        """
        total = len(data_list)
        valid = 0
        invalid = 0
        errors = []

        for idx, data in enumerate(data_list):
            result = SchemaValidator.validate_prospect(data)

            if result.is_valid:
                valid += 1
            else:
                invalid += 1
                errors.append(
                    {
                        "row": idx,
                        "data": data,
                        "errors": result.errors,
                    }
                )

        logger.info(f"Batch validation: {valid}/{total} valid, {invalid} invalid")

        return total, valid, invalid, errors


class BusinessRuleValidator:
    """Validates business rules for data."""

    @staticmethod
    def check_height_range(height: float) -> Tuple[bool, str]:
        """Check if height is within reasonable range."""
        if height < 5.5 or height > 7.0:
            return False, f"Height {height} is outside realistic range (5.5-7.0 feet)"
        return True, ""

    @staticmethod
    def check_weight_range(weight: int) -> Tuple[bool, str]:
        """Check if weight is within reasonable range."""
        if weight < 150 or weight > 350:
            return False, f"Weight {weight} is outside realistic range (150-350 lbs)"
        return True, ""

    @staticmethod
    def check_forty_time_range(forty_time: float) -> Tuple[bool, str]:
        """Check if 40-time is within reasonable range."""
        if forty_time < 4.3 or forty_time > 5.5:
            return False, f"40-time {forty_time} is outside realistic range (4.3-5.5 sec)"
        return True, ""

    @staticmethod
    def check_measurable_consistency(
        height: float = None, weight: int = None, forty_time: float = None
    ) -> List[str]:
        """
        Check consistency between related measurables.

        For example: faster 40-times typically correlate with lower weight
        """
        warnings = []

        if height and weight and weight > 0:
            # BMI calculation (rough check for outliers)
            bmi = (weight * 703) / (height * 12) ** 2
            if bmi > 35:
                warnings.append(f"High BMI ({bmi:.1f}) - may indicate data quality issue")
            if bmi < 15:
                warnings.append(f"Low BMI ({bmi:.1f}) - may indicate data quality issue")

        return warnings

    @staticmethod
    def validate_prospect_completeness(prospect: Dict[str, Any]) -> ValidationResult:
        """
        Validate that prospect has required fields.

        Required: name, position, college
        """
        errors = []
        warnings = []

        # Check required fields
        required_fields = ["name", "position", "college"]
        for field in required_fields:
            if field not in prospect or not prospect[field]:
                errors.append(f"Required field '{field}' is missing or empty")

        # Check for measurables (warning if missing)
        measurable_fields = ["height", "weight"]
        missing_measurables = [f for f in measurable_fields if not prospect.get(f)]
        if missing_measurables:
            warnings.append(f"Missing measurables: {', '.join(missing_measurables)}")

        is_valid = len(errors) == 0
        return ValidationResult(is_valid=is_valid, errors=errors, warnings=warnings)


class DuplicateDetector:
    """Detects duplicate prospects."""

    @staticmethod
    def get_duplicate_key(prospect: Dict[str, Any]) -> Tuple:
        """
        Generate a unique key for duplicate detection.

        Key components: name, position, college (case-insensitive)
        """
        name = prospect.get("name", "").lower().strip()
        position = prospect.get("position", "").lower().strip()
        college = prospect.get("college", "").lower().strip()

        return (name, position, college)

    @staticmethod
    def detect_duplicates_in_batch(data_list: List[Dict[str, Any]]) -> Dict[str, List[int]]:
        """
        Detect duplicate records within a batch.

        Returns:
            Dictionary mapping duplicate key to list of row indices
        """
        seen = {}
        duplicates = {}

        for idx, data in enumerate(data_list):
            key = DuplicateDetector.get_duplicate_key(data)

            if key in seen:
                # Found a duplicate
                if key not in duplicates:
                    duplicates[key] = [seen[key]]
                duplicates[key].append(idx)
            else:
                seen[key] = idx

        if duplicates:
            logger.warning(f"Found {len(duplicates)} duplicate groups in batch")

        return duplicates


class OutlierDetector:
    """Detects outlier values in data."""

    @staticmethod
    def detect_height_outliers(heights: List[float]) -> List[float]:
        """Detect outlier heights using Z-score."""
        import statistics

        if len(heights) < 3:
            return []

        mean = statistics.mean(heights)
        stdev = statistics.stdev(heights)

        outliers = []
        for h in heights:
            z_score = abs((h - mean) / stdev) if stdev > 0 else 0
            if z_score > 3.0:  # 3 standard deviations
                outliers.append(h)

        return outliers

    @staticmethod
    def detect_weight_outliers(weights: List[int]) -> List[int]:
        """Detect outlier weights using Z-score."""
        import statistics

        if len(weights) < 3:
            return []

        mean = statistics.mean(weights)
        stdev = statistics.stdev(weights)

        outliers = []
        for w in weights:
            z_score = abs((w - mean) / stdev) if stdev > 0 else 0
            if z_score > 3.0:
                outliers.append(w)

        return outliers
