"""Quality rules configuration and execution engine.

Manages configurable quality validation rules persisted in database,
including rule definition, position-specific thresholds, and rule execution.

US-044: Enhanced Data Quality for Multi-Source Grades
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy import select, and_
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class RuleType(Enum):
    """Type of quality rule."""
    OUTLIER_DETECTION = "outlier_detection"      # Z-score based
    GRADE_RANGE = "grade_range"                  # Min/max bounds
    GRADE_CHANGE = "grade_change"                # Day-over-day change
    COMPLETENESS = "completeness"                # Required sources
    BUSINESS_LOGIC = "business_logic"            # Custom logic


class ThresholdType(Enum):
    """How threshold values are interpreted."""
    STD_DEV = "std_dev"                  # Number of standard deviations
    PERCENTAGE = "percentage"            # Percentage (0-100)
    ABSOLUTE = "absolute"               # Absolute value
    RANGE = "range"                     # Min-max range


class RuleSeverity(Enum):
    """Alert severity when rule violated."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class QualityRuleConfig:
    """Configuration for a quality rule."""
    rule_id: str
    rule_name: str
    rule_type: RuleType
    grade_source: str                  # "pff", "espn", "nfl", "yahoo"
    position: Optional[str]            # NULL = all positions
    threshold_type: ThresholdType
    threshold_value: float
    severity: RuleSeverity
    enabled: bool
    description: str
    created_at: datetime
    updated_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "rule_type": self.rule_type.value,
            "grade_source": self.grade_source,
            "position": self.position,
            "threshold_type": self.threshold_type.value,
            "threshold_value": self.threshold_value,
            "severity": self.severity.value,
            "enabled": self.enabled,
            "description": self.description,
        }


class QualityRulesEngine:
    """Executes configurable quality rules from database."""
    
    # Pre-defined rule templates
    DEFAULT_RULES = [
        {
            "rule_name": "pff_grade_outlier_qb",
            "rule_type": RuleType.OUTLIER_DETECTION,
            "grade_source": "pff",
            "position": "QB",
            "threshold_type": ThresholdType.STD_DEV,
            "threshold_value": 2.0,  # 2 std devs
            "severity": RuleSeverity.WARNING,
            "description": "QB PFF grades > 2σ from position mean",
        },
        {
            "rule_name": "pff_grade_outlier_edge",
            "rule_type": RuleType.OUTLIER_DETECTION,
            "grade_source": "pff",
            "position": "EDGE",
            "threshold_type": ThresholdType.STD_DEV,
            "threshold_value": 2.0,
            "severity": RuleSeverity.WARNING,
            "description": "EDGE PFF grades > 2σ from position mean",
        },
        {
            "rule_name": "grade_range_pff",
            "rule_type": RuleType.GRADE_RANGE,
            "grade_source": "pff",
            "position": None,  # All positions
            "threshold_type": ThresholdType.RANGE,
            "threshold_value": 0.0,  # Special: stored as "0-100" in description
            "severity": RuleSeverity.CRITICAL,
            "description": "PFF grades must be 0-100",
        },
        {
            "rule_name": "suspicious_grade_change",
            "rule_type": RuleType.GRADE_CHANGE,
            "grade_source": None,  # All sources
            "position": None,  # All positions
            "threshold_type": ThresholdType.PERCENTAGE,
            "threshold_value": 20.0,  # 20% change
            "severity": RuleSeverity.WARNING,
            "description": "Grade change > 20% day-over-day",
        },
        {
            "rule_name": "pff_grade_required",
            "rule_type": RuleType.COMPLETENESS,
            "grade_source": "pff",
            "position": None,  # All positions
            "threshold_type": ThresholdType.ABSOLUTE,
            "threshold_value": 1.0,  # At least 1 source
            "severity": RuleSeverity.CRITICAL,
            "description": "Every prospect must have PFF grade",
        },
    ]
    
    def __init__(self, session: Session):
        """Initialize rules engine.
        
        Args:
            session: SQLAlchemy Session for database queries
        """
        self.session = session
        self._rules_cache: Optional[List[QualityRuleConfig]] = None
        self._cache_timestamp: Optional[datetime] = None
        
    def load_active_rules(
        self, 
        refresh: bool = False,
        position_filter: Optional[str] = None
    ) -> List[QualityRuleConfig]:
        """Load active rules from database with caching.
        
        Args:
            refresh: Force reload from database
            position_filter: Load rules for specific position
            
        Returns:
            List of active QualityRuleConfig objects
        """
        from src.data_pipeline.models.quality import QualityRule
        
        # Return cached if fresh
        if not refresh and self._rules_cache is not None:
            rules = self._rules_cache
        else:
            # Load from database
            stmt = select(QualityRule).where(QualityRule.enabled == True)
            db_rules = self.session.execute(stmt).scalars().all()
            
            rules = []
            for db_rule in db_rules:
                config = QualityRuleConfig(
                    rule_id=str(db_rule.rule_id),
                    rule_name=db_rule.rule_name,
                    rule_type=RuleType(db_rule.rule_type),
                    grade_source=db_rule.grade_source,
                    position=db_rule.position,
                    threshold_type=ThresholdType(db_rule.threshold_type),
                    threshold_value=db_rule.threshold_value,
                    severity=RuleSeverity(db_rule.severity),
                    enabled=db_rule.enabled,
                    description=db_rule.description,
                    created_at=db_rule.created_at,
                    updated_at=db_rule.updated_at,
                )
                rules.append(config)
            
            self._rules_cache = rules
            self._cache_timestamp = datetime.now()
        
        # Filter by position if specified
        if position_filter:
            return [
                r for r in rules
                if r.position is None or r.position == position_filter
            ]
        
        return rules
    
    def get_rule_for_prospect(
        self,
        position: str,
        grade_source: str,
        rule_type: RuleType,
    ) -> Optional[QualityRuleConfig]:
        """Get the most specific rule for a prospect.
        
        Priority: position-specific > position-agnostic
        
        Args:
            position: Player position (e.g., "QB", "EDGE")
            grade_source: Grade source ("pff", "espn", etc.)
            rule_type: Type of rule
            
        Returns:
            Most specific matching rule or None
        """
        rules = self.load_active_rules()
        
        # Filter by rule type and source
        matching = [
            r for r in rules
            if r.rule_type == rule_type and (
                r.grade_source == grade_source or r.grade_source is None
            )
        ]
        
        # Prefer position-specific
        position_specific = [r for r in matching if r.position == position]
        if position_specific:
            return position_specific[0]
        
        # Fall back to position-agnostic
        agnostic = [r for r in matching if r.position is None]
        if agnostic:
            return agnostic[0]
        
        return None
    
    def get_outlier_threshold(
        self,
        position: str,
        grade_source: str = "pff",
    ) -> Tuple[Optional[float], RuleSeverity]:
        """Get outlier detection threshold for position/source.
        
        Args:
            position: Player position
            grade_source: Grade source
            
        Returns:
            Tuple of (threshold_value, severity) or (None, INFO) if no rule
        """
        rule = self.get_rule_for_prospect(
            position, grade_source, RuleType.OUTLIER_DETECTION
        )
        
        if rule:
            return rule.threshold_value, rule.severity
        
        # Default: 2 std devs, warning severity
        return 2.0, RuleSeverity.WARNING
    
    def get_position_groups(self) -> List[str]:
        """Get all unique positions with rules defined.
        
        Returns:
            List of position codes (e.g., ["QB", "EDGE", "CB"])
        """
        rules = self.load_active_rules()
        positions = set()
        for rule in rules:
            if rule.position:
                positions.add(rule.position)
        return sorted(list(positions))
    
    def initialize_default_rules(self) -> int:
        """Create default rules if they don't exist.
        
        Returns:
            Number of rules created
        """
        from src.data_pipeline.models.quality import QualityRule
        from uuid import uuid4
        
        created_count = 0
        
        for rule_def in self.DEFAULT_RULES:
            # Check if rule exists
            stmt = select(QualityRule).where(
                QualityRule.rule_name == rule_def["rule_name"]
            )
            existing = self.session.execute(stmt).scalars().first()
            
            if existing:
                logger.info(f"Rule already exists: {rule_def['rule_name']}")
                continue
            
            # Create new rule
            try:
                new_rule = QualityRule(
                    rule_id=uuid4(),
                    rule_name=rule_def["rule_name"],
                    rule_type=rule_def["rule_type"].value,
                    grade_source=rule_def["grade_source"],
                    position=rule_def.get("position"),
                    threshold_type=rule_def["threshold_type"].value,
                    threshold_value=rule_def["threshold_value"],
                    severity=rule_def["severity"].value,
                    enabled=True,
                    description=rule_def["description"],
                )
                self.session.add(new_rule)
                created_count += 1
                logger.info(f"Created rule: {rule_def['rule_name']}")
            except Exception as e:
                logger.error(f"Failed to create rule {rule_def['rule_name']}: {e}")
                continue
        
        if created_count > 0:
            self.session.commit()
            self._rules_cache = None  # Invalidate cache
        
        return created_count
    
    def update_rule_threshold(
        self,
        rule_name: str,
        new_threshold: float,
        severity: Optional[RuleSeverity] = None,
    ) -> bool:
        """Update a rule's threshold value.
        
        Args:
            rule_name: Name of rule to update
            new_threshold: New threshold value
            severity: New severity level (optional)
            
        Returns:
            True if updated, False if rule not found
        """
        from src.data_pipeline.models.quality import QualityRule
        
        stmt = select(QualityRule).where(QualityRule.rule_name == rule_name)
        rule = self.session.execute(stmt).scalars().first()
        
        if not rule:
            logger.warning(f"Rule not found: {rule_name}")
            return False
        
        rule.threshold_value = new_threshold
        if severity:
            rule.severity = severity.value
        rule.updated_at = datetime.now()
        
        self.session.commit()
        self._rules_cache = None  # Invalidate cache
        
        logger.info(f"Updated rule {rule_name}: threshold={new_threshold}")
        return True
    
    def list_rules_by_position(self, position: str) -> List[QualityRuleConfig]:
        """List all rules applicable to a position.
        
        Args:
            position: Player position
            
        Returns:
            List of applicable rules
        """
        rules = self.load_active_rules()
        return [
            r for r in rules
            if r.position is None or r.position == position
        ]
    
    def get_rules_summary(self) -> Dict[str, Any]:
        """Get summary of all active rules.
        
        Returns:
            Dictionary with rule statistics
        """
        rules = self.load_active_rules()
        
        by_type = {}
        for rule in rules:
            rule_type = rule.rule_type.value
            by_type[rule_type] = by_type.get(rule_type, 0) + 1
        
        by_severity = {}
        for rule in rules:
            severity = rule.severity.value
            by_severity[severity] = by_severity.get(severity, 0) + 1
        
        positions = self.get_position_groups()
        
        return {
            "total_rules": len(rules),
            "active_rules": len([r for r in rules if r.enabled]),
            "by_type": by_type,
            "by_severity": by_severity,
            "positions_with_rules": positions,
            "last_cache_refresh": self._cache_timestamp.isoformat() if self._cache_timestamp else None,
        }
