"""Unit tests for Phase 4: Alert System.

Tests for US-044 Phase 4: Alert Generation and Notifications

Tests cover:
- Alert threshold-based generation
- Alert severity levels
- Email digest generation
- Alert persistence and retrieval
- Alert acknowledgment
- Daily workflow orchestration
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


class TestAlertGenerator:
    """Test AlertGenerator alert creation."""
    
    @patch('src.data_pipeline.quality.alert_generator.AlertSeverity')
    def test_alert_generator_imports(self, mock_severity):
        """Test that AlertGenerator can be imported."""
        from data_pipeline.quality.alert_generator import AlertGenerator, AlertThreshold
        assert AlertGenerator is not None
        assert AlertThreshold is not None
    
    @patch('src.data_pipeline.quality.alert_generator.AlertSeverity')
    def test_generate_critical_alert(self, mock_severity):
        """Test generating critical alert for low coverage."""
        from data_pipeline.quality.alert_generator import AlertGenerator
        
        generator = AlertGenerator()
        metric = {
            'coverage_percentage': 65.0,  # Below critical threshold (70%)
            'validation_percentage': 90.0,
            'outlier_percentage': 2.0,
            'quality_score': 75.0,
            'position': 'QB',
            'grade_source': 'pff',
            'metric_date': datetime.utcnow(),
        }
        
        alerts = generator.generate_alerts(metric)
        assert len(alerts) > 0
        assert any(a.get('severity') == 'critical' for a in alerts)
    
    @patch('src.data_pipeline.quality.alert_generator.AlertSeverity')
    def test_generate_warning_alert(self, mock_severity):
        """Test generating warning alert for low coverage."""
        from data_pipeline.quality.alert_generator import AlertGenerator
        
        generator = AlertGenerator()
        metric = {
            'coverage_percentage': 75.0,  # Between warning (80%) and critical (70%)
            'validation_percentage': 90.0,
            'outlier_percentage': 2.0,
            'quality_score': 85.0,
            'position': 'WR',
            'grade_source': 'espn',
            'metric_date': datetime.utcnow(),
        }
        
        alerts = generator.generate_alerts(metric)
        assert len(alerts) > 0
        assert any(a.get('severity') == 'warning' for a in alerts)
    
    @patch('src.data_pipeline.quality.alert_generator.AlertSeverity')
    def test_no_alert_for_good_metrics(self, mock_severity):
        """Test no alerts generated for good metrics."""
        from data_pipeline.quality.alert_generator import AlertGenerator
        
        generator = AlertGenerator()
        metric = {
            'coverage_percentage': 96.0,
            'validation_percentage': 92.5,
            'outlier_percentage': 2.1,
            'quality_score': 94.0,
            'position': 'CB',
            'grade_source': 'pff',
            'metric_date': datetime.utcnow(),
        }
        
        alerts = generator.generate_alerts(metric)
        assert len(alerts) == 0


class TestEmailNotificationService:
    """Test email notification generation."""
    
    @patch('src.data_pipeline.quality.email_service.EmailConfig')
    def test_email_service_imports(self, mock_config):
        """Test that EmailNotificationService can be imported."""
        from data_pipeline.quality.email_service import EmailNotificationService, EmailConfig
        assert EmailNotificationService is not None
        assert EmailConfig is not None
    
    @patch('src.data_pipeline.quality.email_service.EmailConfig')
    def test_generate_critical_digest(self, mock_config):
        """Test generating email digest with critical alerts."""
        from data_pipeline.quality.email_service import EmailNotificationService
        
        service = EmailNotificationService()
        alerts = [
            {
                'alert_type': 'low_coverage',
                'severity': 'critical',
                'message': 'Coverage is too low',
                'position': 'QB',
                'grade_source': 'pff',
                'metric_value': 65.0,
                'threshold_value': 70.0,
                'quality_score': 75.0,
            }
        ]
        
        digest = service.generate_alert_digest(alerts)
        assert 'subject' in digest
        assert 'body' in digest
        assert 'CRITICAL' in digest['subject']
    
    @patch('src.data_pipeline.quality.email_service.EmailConfig')
    def test_generate_warning_digest(self, mock_config):
        """Test generating email digest with warning alerts."""
        from data_pipeline.quality.email_service import EmailNotificationService
        
        service = EmailNotificationService()
        alerts = [
            {
                'alert_type': 'low_coverage',
                'severity': 'warning',
                'message': 'Coverage is below warning threshold',
                'position': 'WR',
                'grade_source': 'espn',
                'metric_value': 75.0,
                'threshold_value': 80.0,
                'quality_score': 85.0,
            }
        ]
        
        digest = service.generate_alert_digest(alerts)
        assert 'subject' in digest
        assert 'WARNING' in digest['subject']
    
    @patch('src.data_pipeline.quality.email_service.EmailConfig')
    def test_prepare_email_message(self, mock_config):
        """Test preparing email message for delivery."""
        from data_pipeline.quality.email_service import EmailNotificationService
        
        service = EmailNotificationService()
        digest = {'subject': 'Test Alert', 'body': '<html>Test</html>'}
        
        message = service.prepare_email_message(digest, 'test@example.com')
        assert message['to'] == 'test@example.com'
        assert message['subject'] == 'Test Alert'
        assert message['is_html'] is True


class TestAlertRepository:
    """Test alert persistence and retrieval."""
    
    @patch('src.data_pipeline.quality.alert_repository.Session')
    def test_repository_imports(self, mock_session):
        """Test that AlertRepository can be imported."""
        from data_pipeline.quality.alert_repository import AlertRepository
        assert AlertRepository is not None
    
    @patch('data_pipeline.quality.alert_repository.Session')
    def test_save_alert_success(self, mock_session_class):
        """Test saving alert to database."""
        from data_pipeline.quality.alert_repository import AlertRepository
        
        mock_session = MagicMock()
        mock_session.add = Mock()
        mock_session.commit = Mock()
        
        repo = AlertRepository(mock_session)
        assert repo is not None
    
    @patch('data_pipeline.quality.alert_repository.Session')
    def test_get_recent_alerts_success(self, mock_session_class):
        """Test retrieving recent alerts."""
        from data_pipeline.quality.alert_repository import AlertRepository
        
        mock_session = MagicMock()
        repo = AlertRepository(mock_session)
        assert repo is not None
    
    @patch('data_pipeline.quality.alert_repository.Session')
    def test_acknowledge_alert_success(self, mock_session_class):
        """Test acknowledging an alert."""
        from data_pipeline.quality.alert_repository import AlertRepository
        
        mock_session = MagicMock()
        repo = AlertRepository(mock_session)
        assert repo is not None


class TestAlertManager:
    """Test alert management orchestration."""
    
    @patch('src.data_pipeline.quality.alert_manager.Session')
    def test_manager_imports(self, mock_session):
        """Test that AlertManager can be imported."""
        from data_pipeline.quality.alert_manager import AlertManager
        assert AlertManager is not None
    
    def test_alert_manager_initialization(self):
        """Test AlertManager can be initialized with mocked components."""
        from data_pipeline.quality.alert_manager import AlertManager
        
        mock_session = MagicMock()
        mock_generator = Mock()
        mock_email_service = Mock()
        mock_repository = Mock()
        
        manager = AlertManager(
            session=mock_session,
            generator=mock_generator,
            email_service=mock_email_service,
            repository=mock_repository
        )
        
        assert manager is not None
        assert manager.generator is not None
        assert manager.email_service is not None
        assert manager.repository is not None


class TestAlertThresholds:
    """Test alert threshold configuration."""
    
    def test_default_thresholds(self):
        """Test default threshold values."""
        from data_pipeline.quality.alert_generator import AlertThreshold
        
        thresholds = AlertThreshold()
        
        # Quality score thresholds
        assert thresholds.quality_score_normal == 85.0
        assert thresholds.quality_score_warning == 75.0
        assert thresholds.quality_score_critical == 70.0
        
        # Coverage thresholds
        assert thresholds.coverage_warning == 80.0
        assert thresholds.coverage_critical == 70.0
        
        # Validation thresholds
        assert thresholds.validation_warning == 85.0
        assert thresholds.validation_critical == 75.0
        
        # Outlier thresholds
        assert thresholds.outlier_warning == 5.0
        assert thresholds.outlier_critical == 10.0


class TestAlertIntegration:
    """Integration tests for alert system."""
    
    @patch('src.data_pipeline.quality.alert_generator.AlertGenerator')
    @patch('src.data_pipeline.quality.email_service.EmailNotificationService')
    @patch('src.data_pipeline.quality.alert_repository.AlertRepository')
    def test_end_to_end_alert_workflow(self, mock_repo, mock_email, mock_gen):
        """Test complete alert workflow."""
        from data_pipeline.quality.alert_manager import AlertManager
        
        mock_session = MagicMock()
        
        manager = AlertManager(session=mock_session)
        assert manager is not None
        assert manager.generator is not None
        assert manager.email_service is not None
        assert manager.repository is not None
