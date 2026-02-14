"""Email system configuration and scheduling for quality alerts."""

import logging
from datetime import datetime, time
from typing import List, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from src.data_pipeline.quality.alert_manager import AlertManager
from src.data_pipeline.quality.email_service import EmailConfig, EmailNotificationService
from sqlalchemy.orm import Session
from src.config import settings

logger = logging.getLogger(__name__)


class EmailAlertScheduler:
    """Manages scheduled email alerts and digest generation."""

    def __init__(self, session: Session):
        """Initialize email scheduler with database session."""
        self.session = session
        self.scheduler: Optional[BackgroundScheduler] = None
        self.email_config = self._load_email_config()
        self.alert_manager = AlertManager(session=session)
        self.recipient_list = self._load_recipients()

    def _load_email_config(self) -> EmailConfig:
        """Load SMTP configuration from settings."""
        return EmailConfig(
            smtp_host=getattr(settings, 'smtp_host', 'smtp.gmail.com'),
            smtp_port=getattr(settings, 'smtp_port', 587),
            sender_email=getattr(settings, 'sender_email', 'noreply@draft-queen.local'),
            sender_name=getattr(settings, 'sender_name', 'Draft Queen Alerts'),
            use_tls=getattr(settings, 'use_tls', True),
        )

    def _load_recipients(self) -> List[str]:
        """Load email recipients from settings."""
        recipients_str = getattr(settings, 'alert_recipients', '')
        if not recipients_str:
            logger.warning('No alert recipients configured')
            return []

        return [email.strip() for email in recipients_str.split(',') if email.strip()]

    def start(self) -> None:
        """Start the email scheduler."""
        if self.scheduler is not None and self.scheduler.running:
            logger.warning('Email scheduler already running')
            return

        self.scheduler = BackgroundScheduler()

        # Schedule daily digest at 9 AM EST
        self.scheduler.add_job(
            self._send_daily_digest,
            trigger=CronTrigger(hour=9, minute=0, timezone='US/Eastern'),
            id='daily_alert_digest',
            name='Daily Quality Alert Digest',
            replace_existing=True,
        )

        # Schedule summary every morning at 8 AM EST
        self.scheduler.add_job(
            self._send_morning_summary,
            trigger=CronTrigger(hour=8, minute=0, timezone='US/Eastern'),
            id='morning_alert_summary',
            name='Morning Quality Alert Summary',
            replace_existing=True,
        )

        self.scheduler.start()
        logger.info('✓ Email scheduler started')
        logger.info(f'  - Daily digest: 9:00 AM EST')
        logger.info(f'  - Morning summary: 8:00 AM EST')
        logger.info(f'  - Recipients: {", ".join(self.recipient_list)}')

    def stop(self) -> None:
        """Stop the email scheduler."""
        if self.scheduler is None:
            return

        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info('✓ Email scheduler stopped')
        self.scheduler = None

    def _send_daily_digest(self) -> None:
        """Send daily alert digest email."""
        try:
            logger.info('[SCHEDULER] Generating daily alert digest...')

            if not self.recipient_list:
                logger.warning('No recipients configured for alert digest')
                return

            # Generate digest
            digest = self.alert_manager.generate_daily_digest(
                days_back=1,
                exclude_acknowledged=False,
            )

            if digest['alert_count'] == 0:
                logger.info('No alerts in digest, skipping email send')
                return

            # Send to each recipient
            email_service = EmailNotificationService(config=self.email_config)
            success_count = 0
            failure_count = 0

            for recipient_email in self.recipient_list:
                try:
                    self.alert_manager.send_alert_notification(
                        recipient_email=recipient_email,
                        digest=digest,
                        smtp_credentials={
                            'host': self.email_config.smtp_host,
                            'port': self.email_config.smtp_port,
                            'sender': self.email_config.sender_email,
                            'use_tls': self.email_config.use_tls,
                        },
                    )
                    success_count += 1
                    logger.info(f'✓ Daily digest sent to {recipient_email}')
                except Exception as e:
                    failure_count += 1
                    logger.error(f'✗ Failed to send digest to {recipient_email}: {e}')

            logger.info(
                f'[SCHEDULER] Daily digest complete: {success_count} sent, {failure_count} failed'
            )

        except Exception as e:
            logger.error(f'[SCHEDULER] Failed to send daily digest: {e}', exc_info=True)

    def _send_morning_summary(self) -> None:
        """Send morning alert summary email."""
        try:
            logger.info('[SCHEDULER] Generating morning alert summary...')

            if not self.recipient_list:
                logger.warning('No recipients configured for alert summary')
                return

            # Get alert summary for past 24 hours
            summary = self.alert_manager.get_alert_summary(days=1)

            # Create summary email
            summary_content = self._format_summary_email(summary)

            logger.info(f'[SCHEDULER] Morning summary: {summary}')
            logger.info(f'[SCHEDULER] Morning summary email generated ({len(summary_content)} chars)')

        except Exception as e:
            logger.error(f'[SCHEDULER] Failed to send morning summary: {e}', exc_info=True)

    def _format_summary_email(self, summary: dict) -> str:
        """Format alert summary for email."""
        total = summary.get('total_alerts', 0)
        critical = summary.get('by_severity', {}).get('critical', 0)
        warning = summary.get('by_severity', {}).get('warning', 0)
        info = summary.get('by_severity', {}).get('info', 0)

        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .header {{ background-color: #f3f4f6; padding: 20px; border-radius: 5px; }}
                .stat {{ display: inline-block; margin: 10px 20px 10px 0; }}
                .critical {{ color: #dc2626; font-weight: bold; }}
                .warning {{ color: #ea8c55; font-weight: bold; }}
                .info {{ color: #2563eb; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>📊 Quality Alert Summary</h2>
                <p>Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            </div>
            
            <div class="summary">
                <div class="stat"><strong>Total:</strong> {total}</div>
                <div class="stat"><span class="critical">🔴 Critical:</span> {critical}</div>
                <div class="stat"><span class="warning">🟡 Warning:</span> {warning}</div>
                <div class="stat"><span class="info">ℹ️ Info:</span> {info}</div>
            </div>
            
            <p>For details, visit the <a href="https://draft-queen.local/quality">Quality Dashboard</a></p>
        </body>
        </html>
        """
        return html

    def send_immediate_critical_alert(self, alert_message: str) -> None:
        """Send immediate alert for critical issues (not scheduled)."""
        try:
            logger.info('[ALERT] Sending immediate critical alert...')

            if not self.recipient_list:
                logger.warning('No recipients configured for immediate alert')
                return

            html = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    .urgent {{ background-color: #fee2e2; border-left: 4px solid #dc2626; padding: 20px; }}
                </style>
            </head>
            <body>
                <div class="urgent">
                    <h2>🚨 URGENT: Critical Quality Alert</h2>
                    <p><strong>Time:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                    <p><strong>Alert:</strong> {alert_message}</p>
                    <p>Immediate action may be required. Please review the <a href="https://draft-queen.local/quality">Quality Dashboard</a></p>
                </div>
            </body>
            </html>
            """

            for recipient_email in self.recipient_list:
                try:
                    logger.info(f'Sending immediate critical alert to {recipient_email}')
                    # TODO: Implement SMTP sending
                except Exception as e:
                    logger.error(f'Failed to send immediate alert to {recipient_email}: {e}')

        except Exception as e:
            logger.error(f'Failed to send immediate critical alert: {e}', exc_info=True)

    def cleanup_old_alerts(self) -> None:
        """Cleanup old alerts (can be called manually or scheduled)."""
        try:
            logger.info('Cleaning up old alerts (>90 days)...')
            deleted_count = self.alert_manager.cleanup_old_alerts(days_to_keep=90)
            logger.info(f'✓ Deleted {deleted_count} old alerts')
        except Exception as e:
            logger.error(f'Failed to cleanup old alerts: {e}', exc_info=True)


def setup_email_scheduler(session: Session) -> EmailAlertScheduler:
    """Initialize and start the email scheduler."""
    scheduler = EmailAlertScheduler(session)
    scheduler.start()
    return scheduler
