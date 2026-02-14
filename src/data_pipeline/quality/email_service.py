"""Email notification service for quality alerts.

Compiles daily alert digests and sends email notifications to stakeholders.

US-044: Enhanced Data Quality for Multi-Source Grades - Phase 4
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


class EmailConfig:
    """Email configuration for notifications."""
    
    def __init__(self,
                 smtp_host: str = "localhost",
                 smtp_port: int = 587,
                 sender_email: str = "alerts@draft-queen.local",
                 sender_name: str = "Draft Queen Alerts",
                 use_tls: bool = True):
        """Initialize email configuration.
        
        Args:
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port
            sender_email: Sender email address
            sender_name: Sender display name
            use_tls: Whether to use TLS encryption
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_name = sender_name
        self.use_tls = use_tls


class EmailNotificationService:
    """Send email notifications for quality alerts.
    
    Generates HTML email digests and sends to configured recipients.
    """
    
    def __init__(self, config: Optional[EmailConfig] = None):
        """Initialize email service.
        
        Args:
            config: Email configuration (uses defaults if None)
        """
        self.config = config or EmailConfig()
    
    def generate_alert_digest(self,
                             alerts: List[Dict],
                             digest_date: Optional[datetime] = None) -> Dict[str, str]:
        """Generate email digest from alerts.
        
        Args:
            alerts: List of alert dictionaries
            digest_date: Date for digest (uses today if None)
        
        Returns:
            Dictionary with 'subject' and 'body' (HTML)
        """
        if not digest_date:
            digest_date = datetime.utcnow()
        
        # Organize alerts by severity
        critical_alerts = [a for a in alerts if a.get('severity') == 'critical']
        warning_alerts = [a for a in alerts if a.get('severity') == 'warning']
        info_alerts = [a for a in alerts if a.get('severity') == 'info']
        
        # Generate subject
        subject = self._generate_subject(critical_alerts, warning_alerts, digest_date)
        
        # Generate HTML body
        body = self._generate_html_body(critical_alerts, warning_alerts, info_alerts, digest_date)
        
        return {
            'subject': subject,
            'body': body,
            'alert_count': len(alerts),
            'critical_count': len(critical_alerts),
            'warning_count': len(warning_alerts),
        }
    
    def _generate_subject(self,
                         critical_alerts: List[Dict],
                         warning_alerts: List[Dict],
                         digest_date: datetime) -> str:
        """Generate email subject line.
        
        Args:
            critical_alerts: Critical-severity alerts
            warning_alerts: Warning-severity alerts
            digest_date: Date of digest
        
        Returns:
            Subject line string
        """
        date_str = digest_date.strftime('%Y-%m-%d')
        
        if critical_alerts:
            count = len(critical_alerts)
            return f"⚠️ CRITICAL: {count} quality alert{'s' if count != 1 else ''} - {date_str}"
        elif warning_alerts:
            count = len(warning_alerts)
            return f"⚡ WARNING: {count} quality alert{'s' if count != 1 else ''} - {date_str}"
        else:
            return f"✓ Quality Alert Digest - {date_str}"
    
    def _generate_html_body(self,
                           critical_alerts: List[Dict],
                           warning_alerts: List[Dict],
                           info_alerts: List[Dict],
                           digest_date: datetime) -> str:
        """Generate HTML email body.
        
        Args:
            critical_alerts: Critical-severity alerts
            warning_alerts: Warning-severity alerts
            info_alerts: Info-severity alerts
            digest_date: Date of digest
        
        Returns:
            HTML string
        """
        date_str = digest_date.strftime('%B %d, %Y at %H:%M UTC')
        
        html = f"""
        <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; color: #333; }}
                    .header {{ background-color: #f8f9fa; padding: 20px; border-bottom: 2px solid #dee2e6; }}
                    .header h1 {{ margin: 0; color: #333; }}
                    .header p {{ margin: 10px 0 0 0; color: #666; font-size: 14px; }}
                    .summary {{ background-color: #fff; padding: 20px; margin: 20px 0; border-left: 4px solid #007bff; }}
                    .summary-item {{ margin: 10px 0; }}
                    .summary-item .label {{ font-weight: bold; color: #333; }}
                    .summary-item .value {{ color: #666; margin-left: 10px; }}
                    .alerts-section {{ margin: 20px 0; }}
                    .alerts-section h2 {{ margin-top: 0; padding: 10px; background-color: #f8f9fa; border-left: 4px solid #dc3545; color: #dc3545; }}
                    .alerts-section.warning h2 {{ border-left-color: #ffc107; color: #ffc107; }}
                    .alerts-section.info h2 {{ border-left-color: #17a2b8; color: #17a2b8; }}
                    .alert-item {{ padding: 15px; margin: 10px 0; background-color: #fff; border-left: 4px solid #dc3545; }}
                    .alert-item.warning {{ border-left-color: #ffc107; }}
                    .alert-item.info {{ border-left-color: #17a2b8; }}
                    .alert-type {{ font-weight: bold; color: #666; text-transform: uppercase; font-size: 12px; }}
                    .alert-message {{ margin: 10px 0; color: #333; }}
                    .alert-details {{ font-size: 13px; color: #666; margin-top: 8px; }}
                    .alert-details-row {{ margin: 5px 0; }}
                    .footer {{ text-align: center; padding: 20px; color: #999; font-size: 12px; border-top: 1px solid #dee2e6; }}
                    .timestamp {{ color: #999; font-size: 12px; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>📊 Quality Alert Digest</h1>
                    <p>Generated on {date_str}</p>
                </div>
                
                <div class="summary">
                    <div class="summary-item">
                        <span class="label">Total Alerts:</span>
                        <span class="value">{len(critical_alerts) + len(warning_alerts) + len(info_alerts)}</span>
                    </div>
                    <div class="summary-item">
                        <span class="label">🔴 Critical:</span>
                        <span class="value">{len(critical_alerts)}</span>
                    </div>
                    <div class="summary-item">
                        <span class="label">🟡 Warning:</span>
                        <span class="value">{len(warning_alerts)}</span>
                    </div>
                    <div class="summary-item">
                        <span class="label">ℹ️ Info:</span>
                        <span class="value">{len(info_alerts)}</span>
                    </div>
                </div>
                
                {self._generate_alerts_html(critical_alerts, 'critical')}
                {self._generate_alerts_html(warning_alerts, 'warning')}
                {self._generate_alerts_html(info_alerts, 'info')}
                
                <div class="footer">
                    <p>This is an automated alert digest from Draft Queen.</p>
                    <p class="timestamp">For questions or to manage alert settings, contact your system administrator.</p>
                </div>
            </body>
        </html>
        """
        return html.strip()
    
    def _generate_alerts_html(self,
                             alerts: List[Dict],
                             severity: str) -> str:
        """Generate HTML for alert section.
        
        Args:
            alerts: List of alerts
            severity: Severity level ('critical', 'warning', 'info')
        
        Returns:
            HTML string for alerts section
        """
        if not alerts:
            return ""
        
        severity_icons = {
            'critical': '🔴 CRITICAL ALERTS',
            'warning': '🟡 WARNING ALERTS',
            'info': 'ℹ️ INFO ALERTS',
        }
        
        alerts_html = f"""
        <div class="alerts-section {severity}">
            <h2>{severity_icons.get(severity, 'ALERTS')}</h2>
        """
        
        for alert in alerts:
            position = alert.get('position', 'N/A')
            source = alert.get('grade_source', 'N/A')
            message = alert.get('message', '')
            metric_value = alert.get('metric_value', 'N/A')
            threshold_value = alert.get('threshold_value', 'N/A')
            quality_score = alert.get('quality_score', 'N/A')
            alert_type = alert.get('alert_type', '').replace('_', ' ').title()
            
            alerts_html += f"""
            <div class="alert-item {severity}">
                <div class="alert-type">{alert_type}</div>
                <div class="alert-message">{message}</div>
                <div class="alert-details">
                    <div class="alert-details-row">
                        <strong>Position:</strong> {position} | <strong>Source:</strong> {source}
                    </div>
                    <div class="alert-details-row">
                        <strong>Current Value:</strong> {metric_value:.1f} | <strong>Threshold:</strong> {threshold_value:.1f}
                    </div>
                    <div class="alert-details-row">
                        <strong>Quality Score:</strong> {quality_score:.1f}
                    </div>
                </div>
            </div>
            """
        
        alerts_html += "</div>"
        return alerts_html
    
    def prepare_email_message(self,
                             digest: Dict,
                             recipient_email: str) -> Dict[str, str]:
        """Prepare email message for sending.
        
        Args:
            digest: Email digest dictionary with 'subject' and 'body'
            recipient_email: Recipient email address
        
        Returns:
            Dictionary with 'to', 'subject', 'body', 'is_html'
        """
        return {
            'to': recipient_email,
            'subject': digest['subject'],
            'body': digest['body'],
            'is_html': True,
            'from': f"{self.config.sender_name} <{self.config.sender_email}>",
        }
    
    def generate_summary_text(self, digest: Dict) -> str:
        """Generate plain text summary of digest.
        
        Args:
            digest: Email digest dictionary
        
        Returns:
            Plain text summary
        """
        summary = f"""
QUALITY ALERT DIGEST SUMMARY
============================

Total Alerts: {digest.get('alert_count', 0)}
- Critical: {digest.get('critical_count', 0)}
- Warning: {digest.get('warning_count', 0)}

Email Subject: {digest['subject']}

Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
        """
        return summary.strip()
