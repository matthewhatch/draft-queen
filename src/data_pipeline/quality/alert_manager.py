"""Alert management and orchestration service.

Coordinates alert generation, persistence, and notification delivery.

US-044: Enhanced Data Quality for Multi-Source Grades - Phase 4
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class AlertManager:
    """Orchestrate alert generation, persistence, and notifications.
    
    Main service for managing the complete alert workflow from metrics
    to notifications.
    """
    
    def __init__(self,
                 session: Session,
                 generator=None,
                 email_service=None,
                 repository=None):
        """Initialize alert manager.
        
        Args:
            session: SQLAlchemy Session for database operations
            generator: AlertGenerator instance (creates default if None)
            email_service: EmailNotificationService instance (creates default if None)
            repository: AlertRepository instance (creates default if None)
        """
        self.session = session
        
        # Initialize components with defaults if not provided
        if generator is None:
            from src.data_pipeline.quality.alert_generator import AlertGenerator
            generator = AlertGenerator()
        self.generator = generator
        
        if email_service is None:
            from src.data_pipeline.quality.email_service import EmailNotificationService
            email_service = EmailNotificationService()
        self.email_service = email_service
        
        if repository is None:
            from src.data_pipeline.quality.alert_repository import AlertRepository
            repository = AlertRepository(session)
        self.repository = repository
    
    def process_metrics_and_generate_alerts(self,
                                           metrics: List[Dict],
                                           dry_run: bool = False) -> Dict:
        """Process metrics and generate alerts.
        
        Args:
            metrics: List of quality metric dictionaries
            dry_run: If True, generate alerts but don't persist
        
        Returns:
            Dictionary with:
            - 'alerts_generated': count
            - 'alerts_critical': count
            - 'alerts_warning': count
            - 'alerts_saved': count (if not dry_run)
            - 'alert_ids': list of saved alert IDs
        """
        try:
            all_alerts = []
            
            # Generate alerts from metrics
            for metric in metrics:
                metric_alerts = self.generator.generate_alerts(metric)
                all_alerts.extend(metric_alerts)
            
            logger.info(f"Generated {len(all_alerts)} alerts from {len(metrics)} metrics")
            
            # Count by severity
            critical_count = len([a for a in all_alerts if a.get('severity') == 'critical'])
            warning_count = len([a for a in all_alerts if a.get('severity') == 'warning'])
            
            # Save alerts if not dry-run
            alert_ids = []
            if not dry_run and all_alerts:
                alert_ids = self.repository.save_alerts_batch(all_alerts)
            
            return {
                'alerts_generated': len(all_alerts),
                'alerts_critical': critical_count,
                'alerts_warning': warning_count,
                'alerts_info': len(all_alerts) - critical_count - warning_count,
                'alerts_saved': len(alert_ids) if not dry_run else 0,
                'alert_ids': alert_ids,
                'dry_run': dry_run,
            }
        
        except Exception as e:
            logger.error(f"Failed to process metrics: {str(e)}")
            raise
    
    def generate_daily_digest(self,
                             days_back: int = 1,
                             exclude_acknowledged: bool = True) -> Optional[Dict]:
        """Generate daily alert digest for email notification.
        
        Args:
            days_back: Number of days to include in digest
            exclude_acknowledged: If True, exclude acknowledged alerts
        
        Returns:
            Email digest dictionary with 'subject' and 'body', or None if no alerts
        """
        try:
            # Get alerts from repository
            if exclude_acknowledged:
                alerts = self.repository.get_recent_alerts(
                    days=days_back,
                    acknowledged=False
                )
            else:
                alerts = self.repository.get_recent_alerts(days=days_back)
            
            if not alerts:
                logger.info("No alerts to include in digest")
                return None
            
            # Sort by severity (critical first)
            severity_order = {'critical': 0, 'warning': 1, 'info': 2}
            alerts = sorted(
                alerts,
                key=lambda a: (severity_order.get(a.get('severity', 'info'), 99),
                              a.get('generated_at', datetime.utcnow()))
            )
            
            # Generate digest
            digest = self.email_service.generate_alert_digest(alerts)
            
            logger.info(f"Generated digest with {len(alerts)} alerts")
            return digest
        
        except Exception as e:
            logger.error(f"Failed to generate digest: {str(e)}")
            return None
    
    def send_alert_notification(self,
                               recipient_email: str,
                               digest: Dict,
                               smtp_credentials: Optional[Dict] = None) -> bool:
        """Send alert digest via email.
        
        Args:
            recipient_email: Email address to send to
            digest: Email digest dictionary
            smtp_credentials: Optional SMTP credentials dict with:
                - 'username': str
                - 'password': str
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Prepare message
            message = self.email_service.prepare_email_message(digest, recipient_email)
            
            # In production, would use SMTP here
            # For now, just log the message
            logger.info(
                f"Alert digest prepared for {recipient_email}\n"
                f"Subject: {message['subject']}\n"
                f"Alerts: {digest.get('alert_count', 0)}"
            )
            
            # In a real implementation, this would send via SMTP:
            # self._send_via_smtp(message, smtp_credentials)
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to send notification: {str(e)}")
            return False
    
    def get_alert_summary(self,
                         days: int = 7,
                         severity: Optional[str] = None) -> Dict:
        """Get summary of recent alerts.
        
        Args:
            days: Number of days to include
            severity: Optional severity filter
        
        Returns:
            Dictionary with alert statistics
        """
        try:
            alerts = self.repository.get_recent_alerts(days=days, severity=severity)
            
            # Group by position
            by_position = {}
            for alert in alerts:
                pos = alert.get('position', 'unknown')
                by_position[pos] = by_position.get(pos, 0) + 1
            
            # Group by source
            by_source = {}
            for alert in alerts:
                src = alert.get('grade_source', 'unknown')
                by_source[src] = by_source.get(src, 0) + 1
            
            # Group by type
            by_type = {}
            for alert in alerts:
                atype = alert.get('alert_type', 'unknown')
                by_type[atype] = by_type.get(atype, 0) + 1
            
            # Unacknowledged count
            unack_critical = self.repository.get_unacknowledged_count(severity='critical')
            unack_warning = self.repository.get_unacknowledged_count(severity='warning')
            
            return {
                'total_alerts': len(alerts),
                'unacknowledged_critical': unack_critical,
                'unacknowledged_warning': unack_warning,
                'by_position': by_position,
                'by_source': by_source,
                'by_type': by_type,
                'days_included': days,
                'generated_at': datetime.utcnow(),
            }
        
        except Exception as e:
            logger.error(f"Failed to get alert summary: {str(e)}")
            return {}
    
    def acknowledge_alerts(self,
                          alert_ids: List[str],
                          acknowledged_by: str) -> Dict:
        """Acknowledge multiple alerts.
        
        Args:
            alert_ids: List of alert IDs to acknowledge
            acknowledged_by: User/system acknowledging the alerts
        
        Returns:
            Dictionary with:
            - 'acknowledged': count successful
            - 'failed': count failed
            - 'alert_ids': list of acknowledged IDs
        """
        acknowledged = []
        failed = []
        
        for alert_id in alert_ids:
            success = self.repository.acknowledge_alert(alert_id, acknowledged_by)
            if success:
                acknowledged.append(alert_id)
            else:
                failed.append(alert_id)
        
        logger.info(f"Acknowledged {len(acknowledged)} alerts")
        
        return {
            'acknowledged': len(acknowledged),
            'failed': len(failed),
            'alert_ids': acknowledged,
        }
    
    def cleanup_old_alerts(self, days_to_keep: int = 90) -> int:
        """Delete old alerts outside retention window.
        
        Args:
            days_to_keep: Number of days to retain
        
        Returns:
            Count of deleted alerts
        """
        count = self.repository.cleanup_old_alerts(days_to_keep)
        return count
    
    def run_daily_workflow(self,
                          metrics: List[Dict],
                          recipient_emails: List[str],
                          dry_run: bool = False,
                          smtp_credentials: Optional[Dict] = None) -> Dict:
        """Execute complete daily alert workflow.
        
        Args:
            metrics: List of quality metrics to process
            recipient_emails: List of email addresses for digest
            dry_run: If True, don't persist alerts or send emails
            smtp_credentials: Optional SMTP credentials
        
        Returns:
            Dictionary with workflow execution results
        """
        try:
            logger.info("Starting daily alert workflow")
            
            # Step 1: Generate and persist alerts
            metric_result = self.process_metrics_and_generate_alerts(
                metrics,
                dry_run=dry_run
            )
            
            # Step 2: Generate digest
            digest = self.generate_daily_digest()
            
            # Step 3: Send notifications
            notification_result = {
                'sent': 0,
                'failed': 0,
                'recipients': [],
            }
            
            if digest and not dry_run:
                for email in recipient_emails:
                    success = self.send_alert_notification(
                        email,
                        digest,
                        smtp_credentials
                    )
                    if success:
                        notification_result['sent'] += 1
                        notification_result['recipients'].append(email)
                    else:
                        notification_result['failed'] += 1
            
            # Step 4: Cleanup old alerts
            cleanup_count = 0 if dry_run else self.cleanup_old_alerts()
            
            # Compile results
            return {
                'status': 'success',
                'metrics_processed': len(metrics),
                'alerts_generated': metric_result.get('alerts_generated', 0),
                'alerts_critical': metric_result.get('alerts_critical', 0),
                'alerts_warning': metric_result.get('alerts_warning', 0),
                'alerts_saved': metric_result.get('alerts_saved', 0),
                'digest_generated': digest is not None,
                'notifications_sent': notification_result.get('sent', 0),
                'notifications_failed': notification_result.get('failed', 0),
                'old_alerts_cleaned': cleanup_count,
                'dry_run': dry_run,
                'executed_at': datetime.utcnow(),
            }
        
        except Exception as e:
            logger.error(f"Daily workflow failed: {str(e)}")
            raise
