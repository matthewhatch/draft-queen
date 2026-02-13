"""Injury update tracking and change detection."""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class InjuryUpdate:
    """Represents an injury change or new injury."""

    prospect_id: int
    prospect_name: str
    change_type: str  # "new", "updated", "resolved", "worsened", "improved"
    injury_type: str
    previous_severity: Optional[int]
    new_severity: int
    timestamp: datetime
    details: Dict[str, Any]


class InjuryUpdateTracker:
    """Tracks injury changes across updates."""

    @staticmethod
    def detect_new_injuries(
        current_injuries: List[Dict], previous_injuries: List[Dict]
    ) -> List[InjuryUpdate]:
        """
        Detect newly reported injuries.

        Args:
            current_injuries: Current injury list with prospect_id
            previous_injuries: Previous injury list

        Returns:
            List of new injury updates
        """
        new_injuries = []
        previous_prospect_ids = {
            inj.get("prospect_id") for inj in previous_injuries
        }

        for injury in current_injuries:
            prospect_id = injury.get("prospect_id")
            if prospect_id and prospect_id not in previous_prospect_ids:
                update = InjuryUpdate(
                    prospect_id=prospect_id,
                    prospect_name=injury.get("prospect_name", "Unknown"),
                    change_type="new",
                    injury_type=injury.get("injury_type", "Unknown"),
                    previous_severity=None,
                    new_severity=injury.get("severity_score", 0),
                    timestamp=datetime.now(),
                    details={
                        "severity_label": injury.get("severity_label"),
                        "expected_return": injury.get("expected_return_date"),
                        "position": injury.get("position"),
                        "team": injury.get("team"),
                    },
                )
                new_injuries.append(update)
                logger.info(
                    f"Detected new injury: {injury.get('prospect_name')} - "
                    f"{injury.get('injury_type')} ({injury.get('severity_label')})"
                )

        return new_injuries

    @staticmethod
    def detect_resolved_injuries(
        current_injuries: List[Dict], previous_injuries: List[Dict]
    ) -> List[InjuryUpdate]:
        """
        Detect resolved (no longer listed) injuries.

        Args:
            current_injuries: Current injury list
            previous_injuries: Previous injury list

        Returns:
            List of resolved injury updates
        """
        resolved = []
        current_prospect_ids = {inj.get("prospect_id") for inj in current_injuries}

        for injury in previous_injuries:
            prospect_id = injury.get("prospect_id")
            if prospect_id and prospect_id not in current_prospect_ids:
                update = InjuryUpdate(
                    prospect_id=prospect_id,
                    prospect_name=injury.get("prospect_name", "Unknown"),
                    change_type="resolved",
                    injury_type=injury.get("injury_type", "Unknown"),
                    previous_severity=injury.get("severity_score", 0),
                    new_severity=0,
                    timestamp=datetime.now(),
                    details={"resolved_from": injury.get("severity_label")},
                )
                resolved.append(update)
                logger.info(
                    f"Detected resolved injury: {injury.get('prospect_name')} - "
                    f"{injury.get('injury_type')}"
                )

        return resolved

    @staticmethod
    def detect_severity_changes(
        current_injuries: List[Dict], previous_injuries: List[Dict]
    ) -> List[InjuryUpdate]:
        """
        Detect changes in injury severity.

        Args:
            current_injuries: Current injury list
            previous_injuries: Previous injury list

        Returns:
            List of severity change updates
        """
        changes = []

        # Create lookup for previous injuries
        prev_lookup = {}
        for inj in previous_injuries:
            prospect_id = inj.get("prospect_id")
            if prospect_id:
                key = (prospect_id, inj.get("injury_type"))
                prev_lookup[key] = inj

        # Check for changes
        for injury in current_injuries:
            prospect_id = injury.get("prospect_id")
            injury_type = injury.get("injury_type")

            if prospect_id:
                key = (prospect_id, injury_type)
                prev_injury = prev_lookup.get(key)

                if prev_injury:
                    prev_severity = prev_injury.get("severity_score", 0)
                    new_severity = injury.get("severity_score", 0)

                    if prev_severity != new_severity:
                        if new_severity > prev_severity:
                            change_type = "worsened"
                        else:
                            change_type = "improved"

                        update = InjuryUpdate(
                            prospect_id=prospect_id,
                            prospect_name=injury.get("prospect_name", "Unknown"),
                            change_type=change_type,
                            injury_type=injury_type,
                            previous_severity=prev_severity,
                            new_severity=new_severity,
                            timestamp=datetime.now(),
                            details={
                                "previous_status": prev_injury.get("severity_label"),
                                "new_status": injury.get("severity_label"),
                                "expected_return": injury.get("expected_return_date"),
                            },
                        )
                        changes.append(update)
                        logger.info(
                            f"Detected severity change: {injury.get('prospect_name')} - "
                            f"{injury_type}: {prev_injury.get('severity_label')} → "
                            f"{injury.get('severity_label')}"
                        )

        return changes

    @staticmethod
    def classify_critical_updates(
        updates: List[InjuryUpdate], severity_threshold: int = 2
    ) -> Tuple[List[InjuryUpdate], List[InjuryUpdate]]:
        """
        Classify updates as critical or normal.

        Args:
            updates: List of injury updates
            severity_threshold: Minimum severity for critical

        Returns:
            Tuple of (critical_updates, normal_updates)
        """
        critical = []
        normal = []

        for update in updates:
            # New major injuries or worsening
            if (
                update.change_type in ["new", "worsened"]
                and update.new_severity >= severity_threshold
            ):
                critical.append(update)
            else:
                normal.append(update)

        logger.info(
            f"Classified updates: {len(critical)} critical, {len(normal)} normal"
        )

        return critical, normal

    @staticmethod
    def get_update_summary(updates: List[InjuryUpdate]) -> Dict[str, int]:
        """
        Get summary of update types.

        Args:
            updates: List of updates

        Returns:
            Dictionary with counts by change type
        """
        summary = {
            "new": 0,
            "updated": 0,
            "resolved": 0,
            "worsened": 0,
            "improved": 0,
            "total": len(updates),
        }

        for update in updates:
            change_type = update.change_type
            if change_type in summary:
                summary[change_type] += 1

        return summary

    @staticmethod
    def generate_alert_message(
        critical_updates: List[InjuryUpdate],
    ) -> Optional[str]:
        """
        Generate alert message for critical injuries.

        Args:
            critical_updates: List of critical updates

        Returns:
            Alert message or None if no critical updates
        """
        if not critical_updates:
            return None

        new_injuries = [u for u in critical_updates if u.change_type == "new"]
        worsened = [u for u in critical_updates if u.change_type == "worsened"]

        message_parts = ["🚨 CRITICAL INJURY UPDATES 🚨\n"]

        if new_injuries:
            message_parts.append(f"\n🔴 NEW MAJOR INJURIES ({len(new_injuries)}):")
            for update in new_injuries:
                message_parts.append(
                    f"  • {update.prospect_name} ({update.details.get('position')}) - "
                    f"{update.injury_type} ({update.details.get('severity_label')})"
                )

        if worsened:
            message_parts.append(f"\n⚠️  WORSENING INJURIES ({len(worsened)}):")
            for update in worsened:
                message_parts.append(
                    f"  • {update.prospect_name} - "
                    f"{update.injury_type}: {update.details.get('previous_status')} → "
                    f"{update.details.get('new_status')}"
                )

        message_parts.append(f"\nUpdate Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")

        return "\n".join(message_parts)
