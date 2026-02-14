"""Alert persistence and retrieval service.

Manages storage and retrieval of quality alerts with filtering and acknowledgment.

US-044: Enhanced Data Quality for Multi-Source Grades - Phase 4
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import uuid4
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class AlertRepository:
    """Manage alert persistence and retrieval.
    
    Handles storing, retrieving, and managing quality alerts in the database.
    """
    
    def __init__(self, session: Session):
        """Initialize repository with database session.
        
        Args:
            session: SQLAlchemy Session for database operations
        """
        self.session = session
    
    def save_alert(self,
                  alert: Dict,
                  metric_id: Optional[str] = None) -> str:
        """Save alert to database.
        
        Args:
            alert: Alert dictionary with:
                - alert_type: str
                - severity: str
                - message: str
                - metric_value: float
                - threshold_value: float
                - position: Optional[str]
                - grade_source: Optional[str]
                - quality_score: float
                - generated_at: datetime
            metric_id: Optional reference to QualityMetric
        
        Returns:
            Alert ID (UUID)
        
        Raises:
            Exception: If database operation fails
        """
        try:
            from src.data_pipeline.models.quality import QualityAlert
            
            alert_id = str(uuid4())
            
            # Create alert record
            quality_alert = QualityAlert(
                alert_id=alert_id,
                metric_id=metric_id,
                alert_type=alert.get('alert_type'),
                severity=alert.get('severity'),
                message=alert.get('message'),
                metric_value=alert.get('metric_value'),
                threshold_value=alert.get('threshold_value'),
                position=alert.get('position'),
                grade_source=alert.get('grade_source'),
                quality_score=alert.get('quality_score'),
                generated_at=alert.get('generated_at', datetime.utcnow()),
                acknowledged=False,
                acknowledged_by=None,
                acknowledged_at=None,
                created_at=datetime.utcnow(),
            )
            
            self.session.add(quality_alert)
            self.session.commit()
            
            logger.info(f"Saved alert {alert_id} ({alert.get('alert_type')})")
            return alert_id
        
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to save alert: {str(e)}")
            raise
    
    def save_alerts_batch(self, alerts: List[Dict]) -> List[str]:
        """Save multiple alerts to database.
        
        Args:
            alerts: List of alert dictionaries
        
        Returns:
            List of alert IDs
        """
        alert_ids = []
        for alert in alerts:
            try:
                alert_id = self.save_alert(alert)
                alert_ids.append(alert_id)
            except Exception as e:
                logger.warning(f"Failed to save alert in batch: {str(e)}")
                continue
        
        logger.info(f"Saved {len(alert_ids)} of {len(alerts)} alerts")
        return alert_ids
    
    def get_recent_alerts(self,
                         days: int = 1,
                         severity: Optional[str] = None,
                         acknowledged: Optional[bool] = None) -> List[Dict]:
        """Get recent alerts with optional filtering.
        
        Args:
            days: Number of days to look back (default: 1)
            severity: Optional severity filter ('critical', 'warning', 'info')
            acknowledged: Optional filter for acknowledged status
        
        Returns:
            List of alert dictionaries
        """
        try:
            from src.data_pipeline.models.quality import QualityAlert
            
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Build query
            query = self.session.query(QualityAlert).filter(
                QualityAlert.generated_at >= cutoff_date
            ).order_by(QualityAlert.generated_at.desc())
            
            # Apply optional filters
            if severity:
                query = query.filter(QualityAlert.severity == severity)
            
            if acknowledged is not None:
                query = query.filter(QualityAlert.acknowledged == acknowledged)
            
            # Execute query
            alerts = query.all()
            
            # Convert to dictionaries
            return [self._alert_to_dict(alert) for alert in alerts]
        
        except Exception as e:
            logger.error(f"Failed to get recent alerts: {str(e)}")
            return []
    
    def get_alerts_by_position(self,
                              position: str,
                              days: int = 7,
                              severity: Optional[str] = None) -> List[Dict]:
        """Get alerts for specific position.
        
        Args:
            position: Position code (e.g., 'QB', 'WR')
            days: Number of days to look back
            severity: Optional severity filter
        
        Returns:
            List of alert dictionaries
        """
        try:
            from src.data_pipeline.models.quality import QualityAlert
            
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            query = self.session.query(QualityAlert).filter(
                QualityAlert.position == position,
                QualityAlert.generated_at >= cutoff_date
            ).order_by(QualityAlert.generated_at.desc())
            
            if severity:
                query = query.filter(QualityAlert.severity == severity)
            
            alerts = query.all()
            return [self._alert_to_dict(alert) for alert in alerts]
        
        except Exception as e:
            logger.error(f"Failed to get alerts for {position}: {str(e)}")
            return []
    
    def get_alerts_by_source(self,
                            source: str,
                            days: int = 7,
                            severity: Optional[str] = None) -> List[Dict]:
        """Get alerts for specific grade source.
        
        Args:
            source: Grade source code (e.g., 'pff', 'espn')
            days: Number of days to look back
            severity: Optional severity filter
        
        Returns:
            List of alert dictionaries
        """
        try:
            from src.data_pipeline.models.quality import QualityAlert
            
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            query = self.session.query(QualityAlert).filter(
                QualityAlert.grade_source == source,
                QualityAlert.generated_at >= cutoff_date
            ).order_by(QualityAlert.generated_at.desc())
            
            if severity:
                query = query.filter(QualityAlert.severity == severity)
            
            alerts = query.all()
            return [self._alert_to_dict(alert) for alert in alerts]
        
        except Exception as e:
            logger.error(f"Failed to get alerts for {source}: {str(e)}")
            return []
    
    def acknowledge_alert(self,
                         alert_id: str,
                         acknowledged_by: str) -> bool:
        """Mark alert as acknowledged.
        
        Args:
            alert_id: ID of alert to acknowledge
            acknowledged_by: User/system that acknowledged the alert
        
        Returns:
            True if successful, False otherwise
        """
        try:
            from src.data_pipeline.models.quality import QualityAlert
            
            alert = self.session.query(QualityAlert).filter(
                QualityAlert.alert_id == alert_id
            ).first()
            
            if not alert:
                logger.warning(f"Alert {alert_id} not found")
                return False
            
            alert.acknowledged = True
            alert.acknowledged_by = acknowledged_by
            alert.acknowledged_at = datetime.utcnow()
            
            self.session.commit()
            logger.info(f"Acknowledged alert {alert_id}")
            return True
        
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to acknowledge alert: {str(e)}")
            return False
    
    def get_unacknowledged_count(self,
                                severity: Optional[str] = None) -> int:
        """Get count of unacknowledged alerts.
        
        Args:
            severity: Optional severity filter
        
        Returns:
            Count of unacknowledged alerts
        """
        try:
            from src.data_pipeline.models.quality import QualityAlert
            
            query = self.session.query(QualityAlert).filter(
                QualityAlert.acknowledged == False
            )
            
            if severity:
                query = query.filter(QualityAlert.severity == severity)
            
            return query.count()
        
        except Exception as e:
            logger.error(f"Failed to get unacknowledged count: {str(e)}")
            return 0
    
    def cleanup_old_alerts(self, days_to_keep: int = 90) -> int:
        """Delete alerts older than retention period.
        
        Args:
            days_to_keep: Number of days to keep (older alerts deleted)
        
        Returns:
            Count of deleted alerts
        """
        try:
            from src.data_pipeline.models.quality import QualityAlert
            
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            # Get alerts to delete
            alerts_to_delete = self.session.query(QualityAlert).filter(
                QualityAlert.generated_at < cutoff_date
            ).all()
            
            count = len(alerts_to_delete)
            
            # Delete them
            for alert in alerts_to_delete:
                self.session.delete(alert)
            
            self.session.commit()
            logger.info(f"Deleted {count} old alerts")
            return count
        
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to cleanup old alerts: {str(e)}")
            return 0
    
    def _alert_to_dict(self, alert) -> Dict:
        """Convert alert ORM object to dictionary.
        
        Args:
            alert: QualityAlert ORM object
        
        Returns:
            Dictionary representation of alert
        """
        return {
            'alert_id': alert.alert_id,
            'metric_id': alert.metric_id,
            'alert_type': alert.alert_type,
            'severity': alert.severity,
            'message': alert.message,
            'metric_value': alert.metric_value,
            'threshold_value': alert.threshold_value,
            'position': alert.position,
            'grade_source': alert.grade_source,
            'quality_score': alert.quality_score,
            'generated_at': alert.generated_at,
            'acknowledged': alert.acknowledged,
            'acknowledged_by': alert.acknowledged_by,
            'acknowledged_at': alert.acknowledged_at,
            'created_at': alert.created_at,
        }
