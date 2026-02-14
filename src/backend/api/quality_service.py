"""Quality and alert API service."""

import logging
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy.orm import Session

from data_pipeline.quality.alert_manager import AlertManager
from data_pipeline.quality.alert_generator import AlertGenerator, AlertThreshold
from data_pipeline.quality.email_service import EmailNotificationService, EmailConfig
from data_pipeline.quality.alert_repository import AlertRepository
from backend.api.quality_schemas import (
    AlertResponse, AlertListResponse, AlertSummaryResponse, 
    QualityMetricsResponse, AlertDigestResponse, BulkAcknowledgeResponse
)

logger = logging.getLogger(__name__)


class QualityAPIService:
    """Service for quality and alert API operations."""
    
    def __init__(self, session: Session):
        """Initialize service with database session."""
        self.session = session
        
        # Initialize quality system components
        self.alert_generator = AlertGenerator()
        self.email_service = EmailNotificationService()
        self.alert_repository = AlertRepository(session)
        self.alert_manager = AlertManager(
            session=session,
            generator=self.alert_generator,
            email_service=self.email_service,
            repository=self.alert_repository
        )
    
    def get_recent_alerts(
        self,
        days: int = 1,
        severity: Optional[str] = None,
        acknowledged: Optional[bool] = None,
        position: Optional[str] = None,
        source: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> AlertListResponse:
        """
        Retrieve recent alerts with filtering.
        
        Args:
            days: Number of days to look back
            severity: Filter by severity (info, warning, critical)
            acknowledged: Filter by acknowledgment status
            position: Filter by position
            source: Filter by grade source
            skip: Number of records to skip
            limit: Maximum records to return
            
        Returns:
            AlertListResponse with alerts and metadata
        """
        try:
            # Get alerts from repository
            alerts = self.alert_repository.get_recent_alerts(
                days=days,
                severity=severity,
                acknowledged=acknowledged
            )
            
            # Filter by position if provided
            if position:
                alerts = [a for a in alerts if a.get('position') == position]
            
            # Filter by source if provided
            if source:
                alerts = [a for a in alerts if a.get('grade_source') == source]
            
            # Calculate counts before pagination
            total_count = len(alerts)
            unacknowledged = sum(1 for a in alerts if not a.get('acknowledged'))
            critical = sum(1 for a in alerts if a.get('severity') == 'critical')
            warning = sum(1 for a in alerts if a.get('severity') == 'warning')
            info = sum(1 for a in alerts if a.get('severity') == 'info')
            
            # Apply pagination
            paginated_alerts = alerts[skip:skip + limit]
            
            # Convert to response objects
            alert_responses = [AlertResponse(**alert) for alert in paginated_alerts]
            
            return AlertListResponse(
                total_count=total_count,
                returned_count=len(alert_responses),
                alerts=alert_responses,
                unacknowledged_count=unacknowledged,
                critical_count=critical,
                warning_count=warning,
                info_count=info
            )
        
        except Exception as e:
            logger.error(f"Error retrieving alerts: {e}", exc_info=True)
            raise
    
    def get_alerts_by_position(
        self,
        position: str,
        days: int = 7,
        severity: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> AlertListResponse:
        """
        Retrieve alerts for specific position.
        
        Args:
            position: Position code
            days: Number of days to look back
            severity: Filter by severity
            skip: Number of records to skip
            limit: Maximum records to return
            
        Returns:
            AlertListResponse for position
        """
        try:
            alerts = self.alert_repository.get_alerts_by_position(
                position=position,
                days=days,
                severity=severity
            )
            
            total_count = len(alerts)
            critical = sum(1 for a in alerts if a.get('severity') == 'critical')
            warning = sum(1 for a in alerts if a.get('severity') == 'warning')
            info = sum(1 for a in alerts if a.get('severity') == 'info')
            
            paginated_alerts = alerts[skip:skip + limit]
            alert_responses = [AlertResponse(**alert) for alert in paginated_alerts]
            
            return AlertListResponse(
                total_count=total_count,
                returned_count=len(alert_responses),
                alerts=alert_responses,
                unacknowledged_count=sum(1 for a in alerts if not a.get('acknowledged')),
                critical_count=critical,
                warning_count=warning,
                info_count=info
            )
        
        except Exception as e:
            logger.error(f"Error retrieving alerts for position {position}: {e}", exc_info=True)
            raise
    
    def get_alerts_by_source(
        self,
        source: str,
        days: int = 7,
        severity: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> AlertListResponse:
        """
        Retrieve alerts for specific grade source.
        
        Args:
            source: Grade source (e.g., 'pff', 'espn')
            days: Number of days to look back
            severity: Filter by severity
            skip: Number of records to skip
            limit: Maximum records to return
            
        Returns:
            AlertListResponse for source
        """
        try:
            alerts = self.alert_repository.get_alerts_by_source(
                source=source,
                days=days,
                severity=severity
            )
            
            total_count = len(alerts)
            critical = sum(1 for a in alerts if a.get('severity') == 'critical')
            warning = sum(1 for a in alerts if a.get('severity') == 'warning')
            info = sum(1 for a in alerts if a.get('severity') == 'info')
            
            paginated_alerts = alerts[skip:skip + limit]
            alert_responses = [AlertResponse(**alert) for alert in paginated_alerts]
            
            return AlertListResponse(
                total_count=total_count,
                returned_count=len(alert_responses),
                alerts=alert_responses,
                unacknowledged_count=sum(1 for a in alerts if not a.get('acknowledged')),
                critical_count=critical,
                warning_count=warning,
                info_count=info
            )
        
        except Exception as e:
            logger.error(f"Error retrieving alerts for source {source}: {e}", exc_info=True)
            raise
    
    def get_alert_summary(self, days: int = 7, severity: Optional[str] = None) -> AlertSummaryResponse:
        """
        Get alert summary statistics.
        
        Args:
            days: Number of days to look back
            severity: Filter by severity
            
        Returns:
            AlertSummaryResponse with aggregated statistics
        """
        try:
            summary = self.alert_manager.get_alert_summary(days=days, severity=severity)
            
            # Calculate oldest unacknowledged alert age
            unack_alerts = self.alert_repository.get_recent_alerts(
                days=days,
                acknowledged=False
            )
            
            oldest_age_hours = None
            if unack_alerts:
                oldest_alert = min(unack_alerts, key=lambda a: a.get('generated_at', datetime.utcnow()))
                age = datetime.utcnow() - oldest_alert.get('generated_at', datetime.utcnow())
                oldest_age_hours = age.total_seconds() / 3600
            
            return AlertSummaryResponse(
                total_alerts=summary.get('total_alerts', 0),
                unacknowledged_critical=summary.get('by_severity', {}).get('critical', 0),
                unacknowledged_warning=summary.get('by_severity', {}).get('warning', 0),
                unacknowledged_info=summary.get('by_severity', {}).get('info', 0),
                by_position=summary.get('by_position', {}),
                by_source=summary.get('by_source', {}),
                by_type=summary.get('by_type', {}),
                critical_positions=list({a.get('position') for a in unack_alerts 
                                       if a.get('severity') == 'critical' and a.get('position')}),
                critical_sources=list({a.get('grade_source') for a in unack_alerts 
                                      if a.get('severity') == 'critical' and a.get('grade_source')}),
                oldest_unacknowledged_alert_age_hours=oldest_age_hours
            )
        
        except Exception as e:
            logger.error(f"Error getting alert summary: {e}", exc_info=True)
            raise
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> AlertResponse:
        """
        Acknowledge a single alert.
        
        Args:
            alert_id: Alert ID (UUID)
            acknowledged_by: User or system acknowledging
            
        Returns:
            Updated AlertResponse
        """
        try:
            self.alert_repository.acknowledge_alert(alert_id, acknowledged_by)
            
            # Retrieve updated alert
            alerts = self.alert_repository.get_recent_alerts(days=90)
            alert = next((a for a in alerts if str(a.get('id')) == str(alert_id)), None)
            
            if not alert:
                raise ValueError(f"Alert {alert_id} not found after acknowledgment")
            
            return AlertResponse(**alert)
        
        except Exception as e:
            logger.error(f"Error acknowledging alert {alert_id}: {e}", exc_info=True)
            raise
    
    def acknowledge_multiple_alerts(
        self,
        alert_ids: List[str],
        acknowledged_by: str
    ) -> BulkAcknowledgeResponse:
        """
        Acknowledge multiple alerts.
        
        Args:
            alert_ids: List of alert IDs
            acknowledged_by: User or system acknowledging
            
        Returns:
            BulkAcknowledgeResponse with results
        """
        try:
            acknowledged = 0
            failed = 0
            failed_ids = []
            
            for alert_id in alert_ids:
                try:
                    self.alert_repository.acknowledge_alert(alert_id, acknowledged_by)
                    acknowledged += 1
                except Exception as e:
                    logger.warning(f"Failed to acknowledge alert {alert_id}: {e}")
                    failed += 1
                    failed_ids.append(alert_id)
            
            return BulkAcknowledgeResponse(
                acknowledged=acknowledged,
                failed=failed,
                alert_ids=alert_ids,
                failed_ids=failed_ids
            )
        
        except Exception as e:
            logger.error(f"Error acknowledging multiple alerts: {e}", exc_info=True)
            raise
    
    def get_alert_digest(self, days_back: int = 1) -> AlertDigestResponse:
        """
        Generate alert digest for email preview.
        
        Args:
            days_back: Number of days to include in digest
            
        Returns:
            AlertDigestResponse with digest content
        """
        try:
            digest = self.alert_manager.generate_daily_digest(days_back=days_back)
            
            return AlertDigestResponse(
                subject=digest.get('subject', 'Draft Queen Quality Alerts'),
                body=digest.get('body', ''),
                alert_count=digest.get('alert_count', 0),
                critical_count=digest.get('critical_count', 0),
                warning_count=digest.get('warning_count', 0),
                info_count=digest.get('info_count', 0),
                digest_date=datetime.utcnow()
            )
        
        except Exception as e:
            logger.error(f"Error generating alert digest: {e}", exc_info=True)
            raise
    
    def cleanup_old_alerts(self, days_to_keep: int = 90) -> int:
        """
        Delete alerts older than retention period.
        
        Args:
            days_to_keep: Number of days to retain
            
        Returns:
            Count of deleted alerts
        """
        try:
            deleted_count = self.alert_repository.cleanup_old_alerts(days_to_keep)
            logger.info(f"Cleaned up {deleted_count} old alerts (kept {days_to_keep} days)")
            return deleted_count
        
        except Exception as e:
            logger.error(f"Error cleaning up alerts: {e}", exc_info=True)
            raise
