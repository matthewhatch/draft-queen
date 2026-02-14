"""Integration tests for email alert system."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, call
from sqlalchemy.orm import Session

from src.backend.email_scheduler import EmailAlertScheduler, setup_email_scheduler
from src.data_pipeline.quality.alert_manager import AlertManager
from src.data_pipeline.quality.email_service import EmailConfig


@pytest.fixture
def mock_session():
    """Create mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def mock_settings():
    """Create mock settings object."""
    settings = Mock()
    settings.smtp_host = 'smtp.test.com'
    settings.smtp_port = 587
    settings.sender_email = 'test@example.com'
    settings.sender_name = 'Test Alerts'
    settings.use_tls = True
    settings.alert_recipients = 'user1@example.com,user2@example.com'
    return settings


class TestEmailAlertScheduler:
    """Integration tests for EmailAlertScheduler."""

    def test_initialization_with_settings(self, mock_session, mock_settings):
        """Test scheduler initializes with correct configuration."""
        with patch('src.backend.email_scheduler.settings', mock_settings):
            scheduler = EmailAlertScheduler(mock_session)
            assert scheduler.session is mock_session
            assert scheduler.email_config is not None
            assert len(scheduler.recipient_list) == 2

    def test_load_email_config(self, mock_session, mock_settings):
        """Test email config loading from settings."""
        with patch('src.backend.email_scheduler.settings', mock_settings):
            scheduler = EmailAlertScheduler(mock_session)
            config = scheduler.email_config
            assert isinstance(config, EmailConfig)
            assert config.smtp_host == 'smtp.test.com'
            assert config.sender_email == 'test@example.com'

    def test_load_recipients(self, mock_session, mock_settings):
        """Test recipient list loading."""
        with patch('src.backend.email_scheduler.settings', mock_settings):
            scheduler = EmailAlertScheduler(mock_session)
            assert len(scheduler.recipient_list) == 2
            assert 'user1@example.com' in scheduler.recipient_list
            assert 'user2@example.com' in scheduler.recipient_list

    def test_load_recipients_empty(self, mock_session, mock_settings):
        """Test handling of empty recipient list."""
        mock_settings.alert_recipients = ''
        with patch('src.backend.email_scheduler.settings', mock_settings):
            scheduler = EmailAlertScheduler(mock_session)
            assert scheduler.recipient_list == []

    def test_load_recipients_with_whitespace(self, mock_session, mock_settings):
        """Test recipient parsing with whitespace."""
        mock_settings.alert_recipients = '  user1@example.com  ,  user2@example.com  '
        with patch('src.backend.email_scheduler.settings', mock_settings):
            scheduler = EmailAlertScheduler(mock_session)
            assert len(scheduler.recipient_list) == 2
            assert scheduler.recipient_list[0] == 'user1@example.com'
            assert scheduler.recipient_list[1] == 'user2@example.com'

    def test_start_scheduler(self, mock_session, mock_settings):
        """Test scheduler startup."""
        with patch('src.backend.email_scheduler.settings', mock_settings):
            scheduler = EmailAlertScheduler(mock_session)
            assert scheduler.scheduler is None
            scheduler.start()
            assert scheduler.scheduler is not None
            assert scheduler.scheduler.running is True
            scheduler.stop()

    def test_stop_scheduler(self, mock_session, mock_settings):
        """Test scheduler shutdown."""
        with patch('src.backend.email_scheduler.settings', mock_settings):
            scheduler = EmailAlertScheduler(mock_session)
            scheduler.start()
            assert scheduler.scheduler.running is True
            scheduler.stop()
            assert scheduler.scheduler is None

    def test_schedule_daily_digest_job(self, mock_session, mock_settings):
        """Test daily digest job is scheduled."""
        with patch('src.backend.email_scheduler.settings', mock_settings):
            scheduler = EmailAlertScheduler(mock_session)
            scheduler.start()
            jobs = scheduler.scheduler.get_jobs()
            job_ids = [j.id for j in jobs]
            assert 'daily_alert_digest' in job_ids
            scheduler.stop()

    def test_schedule_morning_summary_job(self, mock_session, mock_settings):
        """Test morning summary job is scheduled."""
        with patch('src.backend.email_scheduler.settings', mock_settings):
            scheduler = EmailAlertScheduler(mock_session)
            scheduler.start()
            jobs = scheduler.scheduler.get_jobs()
            job_ids = [j.id for j in jobs]
            assert 'morning_alert_summary' in job_ids
            scheduler.stop()

    def test_send_daily_digest_with_alerts(self, mock_session, mock_settings):
        """Test sending daily digest with alerts."""
        with patch('src.backend.email_scheduler.settings', mock_settings):
            with patch('src.backend.email_scheduler.AlertManager') as MockAlertManager:
                mock_alert_manager = Mock()
                MockAlertManager.return_value = mock_alert_manager
                mock_alert_manager.generate_daily_digest.return_value = {
                    'alert_count': 5,
                    'critical_count': 2,
                }

                scheduler = EmailAlertScheduler(mock_session)
                scheduler.alert_manager = mock_alert_manager

                with patch(
                    'src.backend.email_scheduler.EmailNotificationService'
                ):
                    scheduler._send_daily_digest()

                mock_alert_manager.generate_daily_digest.assert_called_once()
                assert (
                    mock_alert_manager.send_alert_notification.call_count == 2
                )

    def test_send_daily_digest_no_alerts(self, mock_session, mock_settings):
        """Test daily digest skipped when no alerts."""
        with patch('src.backend.email_scheduler.settings', mock_settings):
            with patch('src.backend.email_scheduler.AlertManager') as MockAlertManager:
                mock_alert_manager = Mock()
                MockAlertManager.return_value = mock_alert_manager
                mock_alert_manager.generate_daily_digest.return_value = {
                    'alert_count': 0
                }

                scheduler = EmailAlertScheduler(mock_session)
                scheduler.alert_manager = mock_alert_manager

                with patch(
                    'src.backend.email_scheduler.EmailNotificationService'
                ) as MockEmailService:
                    scheduler._send_daily_digest()

                mock_alert_manager.generate_daily_digest.assert_called_once()
                # Should not call send_alert_notification for zero alerts
                mock_alert_manager.send_alert_notification.assert_not_called()

    def test_send_daily_digest_to_multiple_recipients(self, mock_session, mock_settings):
        """Test digest sent to all recipients."""
        with patch('src.backend.email_scheduler.settings', mock_settings):
            with patch('src.backend.email_scheduler.AlertManager') as MockAlertManager:
                mock_alert_manager = Mock()
                MockAlertManager.return_value = mock_alert_manager
                mock_alert_manager.generate_daily_digest.return_value = {
                    'alert_count': 3
                }

                scheduler = EmailAlertScheduler(mock_session)
                scheduler.alert_manager = mock_alert_manager

                with patch(
                    'src.backend.email_scheduler.EmailNotificationService'
                ):
                    scheduler._send_daily_digest()

                # Verify send was attempted for each recipient
                assert (
                    mock_alert_manager.send_alert_notification.call_count == 2
                )

    def test_format_summary_email(self, mock_session, mock_settings):
        """Test email formatting."""
        with patch('src.backend.email_scheduler.settings', mock_settings):
            scheduler = EmailAlertScheduler(mock_session)

        summary = {
            'total_alerts': 10,
            'by_severity': {
                'critical': 3,
                'warning': 5,
                'info': 2,
            },
        }

        html = scheduler._format_summary_email(summary)

        assert 'Quality Alert Summary' in html
        assert '10' in html  # Total count
        assert '3' in html  # Critical count
        assert 'Dashboard' in html

    def test_format_summary_email_with_zeros(self, mock_session, mock_settings):
        """Test email formatting with zero alerts."""
        with patch('src.backend.email_scheduler.settings', mock_settings):
            scheduler = EmailAlertScheduler(mock_session)

        summary = {
            'total_alerts': 0,
            'by_severity': {
                'critical': 0,
                'warning': 0,
                'info': 0,
            },
        }

        html = scheduler._format_summary_email(summary)

        assert 'Quality Alert Summary' in html
        assert '0' in html

    def test_send_morning_summary(self, mock_session, mock_settings):
        """Test morning summary generation."""
        with patch('src.backend.email_scheduler.settings', mock_settings):
            with patch('src.backend.email_scheduler.AlertManager') as MockAlertManager:
                mock_alert_manager = Mock()
                MockAlertManager.return_value = mock_alert_manager
                mock_alert_manager.get_alert_summary.return_value = {
                    'total_alerts': 5,
                    'by_severity': {'critical': 1, 'warning': 2, 'info': 2},
                }

                scheduler = EmailAlertScheduler(mock_session)
                scheduler.alert_manager = mock_alert_manager

                scheduler._send_morning_summary()

                mock_alert_manager.get_alert_summary.assert_called_once_with(
                    days=1
                )

    def test_send_immediate_critical_alert(self, mock_session, mock_settings):
        """Test sending immediate critical alert."""
        with patch('src.backend.email_scheduler.settings', mock_settings):
            scheduler = EmailAlertScheduler(mock_session)
            scheduler.send_immediate_critical_alert('Test critical alert')
            # Should not raise any exception

    def test_cleanup_old_alerts(self, mock_session, mock_settings):
        """Test cleanup of old alerts."""
        with patch('src.backend.email_scheduler.settings', mock_settings):
            with patch('src.backend.email_scheduler.AlertManager') as MockAlertManager:
                mock_alert_manager = Mock()
                MockAlertManager.return_value = mock_alert_manager
                mock_alert_manager.cleanup_old_alerts.return_value = 42

                scheduler = EmailAlertScheduler(mock_session)
                scheduler.alert_manager = mock_alert_manager
                scheduler.cleanup_old_alerts()

                mock_alert_manager.cleanup_old_alerts.assert_called_once_with(
                    days_to_keep=90
                )

    def test_scheduler_handles_no_recipients(self, mock_session, mock_settings):
        """Test scheduler handles empty recipient list gracefully."""
        mock_settings.alert_recipients = ''
        with patch('src.backend.email_scheduler.settings', mock_settings):
            with patch('src.backend.email_scheduler.AlertManager'):
                scheduler = EmailAlertScheduler(mock_session)
                assert scheduler.recipient_list == []
                # Should not raise error
                scheduler._send_daily_digest()


class TestEmailSchedulerIntegration:
    """Integration tests with mock FastAPI app."""

    def test_full_digest_workflow(self, mock_session, mock_settings):
        """Test complete digest generation and sending workflow."""
        with patch('src.backend.email_scheduler.settings', mock_settings):
            with patch('src.backend.email_scheduler.AlertManager') as MockAlertManager:
                with patch(
                    'src.backend.email_scheduler.EmailNotificationService'
                ) as MockEmailService:
                    mock_manager = Mock()
                    MockAlertManager.return_value = mock_manager
                    mock_manager.generate_daily_digest.return_value = {
                        'alert_count': 5,
                        'critical_count': 2,
                    }
                    mock_manager.send_alert_notification.return_value = True

                    scheduler = EmailAlertScheduler(mock_session)
                    scheduler.alert_manager = mock_manager

                    scheduler._send_daily_digest()

                    mock_manager.generate_daily_digest.assert_called_once()
                    assert mock_manager.send_alert_notification.call_count == 2

    def test_scheduler_maintains_state(self, mock_session, mock_settings):
        """Test scheduler maintains state across operations."""
        with patch('src.backend.email_scheduler.settings', mock_settings):
            scheduler = EmailAlertScheduler(mock_session)

            # Initial state
            assert scheduler.scheduler is None

            # After start
            scheduler.start()
            scheduler_instance = scheduler.scheduler
            assert scheduler_instance is not None

            # After stop
            scheduler.stop()
            assert scheduler.scheduler is None

    def test_setup_email_scheduler_function(self, mock_session, mock_settings):
        """Test setup_email_scheduler convenience function."""
        with patch('src.backend.email_scheduler.settings', mock_settings):
            scheduler = setup_email_scheduler(mock_session)
            assert scheduler is not None
            assert scheduler.scheduler is not None
            scheduler.stop()


class TestEmailConfigValidation:
    """Tests for email configuration validation."""

    def test_valid_smtp_host_and_port(self, mock_session, mock_settings):
        """Test valid SMTP configuration."""
        mock_settings.smtp_host = 'smtp.gmail.com'
        mock_settings.smtp_port = 587
        with patch('src.backend.email_scheduler.settings', mock_settings):
            scheduler = EmailAlertScheduler(mock_session)
            assert scheduler.email_config.smtp_host == 'smtp.gmail.com'
            assert scheduler.email_config.smtp_port == 587

    def test_alternative_smtp_providers(self, mock_session, mock_settings):
        """Test configuration for different SMTP providers."""
        providers = [
            ('smtp.office365.com', 587),
            ('email-smtp.us-east-1.amazonaws.com', 587),
            ('mail.domain.com', 25),
            ('mail.domain.com', 465),
        ]

        for host, port in providers:
            mock_settings.smtp_host = host
            mock_settings.smtp_port = port
            with patch('src.backend.email_scheduler.settings', mock_settings):
                scheduler = EmailAlertScheduler(mock_session)
                assert scheduler.email_config.smtp_host == host
                assert scheduler.email_config.smtp_port == port


# Fixtures for common test setup


@pytest.fixture
def sample_alert_digest():
    """Create sample alert digest."""
    return {
        'subject': '📊 Daily Quality Alert Digest - 2024-02-21',
        'alert_count': 12,
        'critical_count': 2,
        'warning_count': 5,
        'info_count': 5,
        'by_position': {'QB': 3, 'RB': 2, 'WR': 4, 'TE': 3},
        'by_source': {'pff': 7, 'nfl': 5},
        'generated_at': datetime.utcnow().isoformat(),
    }


@pytest.fixture
def sample_alert_summary():
    """Create sample alert summary."""
    return {
        'total_alerts': 42,
        'unacknowledged': 28,
        'critical': 3,
        'oldest_alert_age_hours': 18,
        'by_severity': {
            'critical': 3,
            'warning': 15,
            'info': 24,
        },
        'by_position': {
            'QB': 8,
            'RB': 6,
            'WR': 12,
            'TE': 9,
            'K': 7,
        },
        'by_source': {
            'pff': 25,
            'nfl': 17,
        },
    }
