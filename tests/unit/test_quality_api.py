"""Tests for quality and alert API service."""

import pytest
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from unittest.mock import Mock, patch, MagicMock

from backend.api.quality_schemas import (
    AlertResponse, AlertListResponse, AlertSummaryResponse,
    AlertDigestResponse
)
from backend.api.quality_service import QualityAPIService


class TestQualityAPIService:
    """Tests for QualityAPIService."""
    
    def test_service_initialization(self):
        """Test QualityAPIService initialization."""
        mock_session = Mock()
        
        with patch('backend.api.quality_service.AlertGenerator'):
            with patch('backend.api.quality_service.EmailNotificationService'):
                with patch('backend.api.quality_service.AlertRepository'):
                    with patch('backend.api.quality_service.AlertManager'):
                        service = QualityAPIService(mock_session)
                        assert service.session == mock_session
                        assert service.alert_generator is not None
                        assert service.email_service is not None
                        assert service.alert_repository is not None
                        assert service.alert_manager is not None
    
    def test_get_recent_alerts_success(self):
        """Test getting recent alerts."""
        mock_session = Mock()
        
        with patch('backend.api.quality_service.AlertGenerator'):
            with patch('backend.api.quality_service.EmailNotificationService'):
                with patch('backend.api.quality_service.AlertRepository'):
                    with patch('backend.api.quality_service.AlertManager'):
                        service = QualityAPIService(mock_session)
                        
                        # Setup mock repository
                        mock_repo = Mock()
                        service.alert_repository = mock_repo
                        
                        alert_dict = {
                            'id': str(uuid4()),
                            'alert_type': 'low_coverage',
                            'severity': 'critical',
                            'message': 'Coverage below threshold',
                            'position': 'QB',
                            'grade_source': 'pff',
                            'metric_value': 65.0,
                            'threshold_value': 70.0,
                            'quality_score': 72.0,
                            'generated_at': datetime.utcnow(),
                            'acknowledged': False
                        }
                        
                        mock_repo.get_recent_alerts.return_value = [alert_dict]
                        
                        # Call method
                        result = service.get_recent_alerts(days=7, skip=0, limit=50)
                        
                        # Assertions
                        assert isinstance(result, AlertListResponse)
                        assert result.total_count == 1
                        assert result.returned_count == 1
                        assert result.critical_count == 1
                        assert len(result.alerts) == 1
    
    def test_get_recent_alerts_with_filters(self):
        """Test getting recent alerts with filters."""
        mock_session = Mock()
        
        with patch('backend.api.quality_service.AlertGenerator'):
            with patch('backend.api.quality_service.EmailNotificationService'):
                with patch('backend.api.quality_service.AlertRepository'):
                    with patch('backend.api.quality_service.AlertManager'):
                        service = QualityAPIService(mock_session)
                        
                        mock_repo = Mock()
                        service.alert_repository = mock_repo
                        mock_repo.get_recent_alerts.return_value = []
                        
                        result = service.get_recent_alerts(
                            days=7,
                            severity='critical',
                            position='QB',
                            source='pff'
                        )
                        
                        # Verify repository was called with correct filters
                        mock_repo.get_recent_alerts.assert_called_once()
                        assert result.total_count == 0
    
    def test_get_alerts_by_position(self):
        """Test getting alerts by position."""
        mock_session = Mock()
        
        with patch('backend.api.quality_service.AlertGenerator'):
            with patch('backend.api.quality_service.EmailNotificationService'):
                with patch('backend.api.quality_service.AlertRepository'):
                    with patch('backend.api.quality_service.AlertManager'):
                        service = QualityAPIService(mock_session)
                        
                        mock_repo = Mock()
                        service.alert_repository = mock_repo
                        
                        alert_dict = {
                            'id': str(uuid4()),
                            'alert_type': 'low_coverage',
                            'severity': 'warning',
                            'message': 'Low coverage',
                            'position': 'QB',
                            'grade_source': 'espn',
                            'metric_value': 75.0,
                            'threshold_value': 80.0,
                            'quality_score': 78.0,
                            'generated_at': datetime.utcnow(),
                            'acknowledged': False
                        }
                        
                        mock_repo.get_alerts_by_position.return_value = [alert_dict]
                        
                        result = service.get_alerts_by_position('QB', days=7)
                        
                        assert result.total_count == 1
                        assert result.warning_count == 1
                        mock_repo.get_alerts_by_position.assert_called_once()
    
    def test_acknowledge_alert(self):
        """Test acknowledging a single alert."""
        mock_session = Mock()
        alert_id = str(uuid4())
        
        with patch('backend.api.quality_service.AlertGenerator'):
            with patch('backend.api.quality_service.EmailNotificationService'):
                with patch('backend.api.quality_service.AlertRepository'):
                    with patch('backend.api.quality_service.AlertManager'):
                        service = QualityAPIService(mock_session)
                        
                        mock_repo = Mock()
                        service.alert_repository = mock_repo
                        
                        alert_dict = {
                            'id': alert_id,
                            'alert_type': 'low_validation',
                            'severity': 'warning',
                            'message': 'Validation low',
                            'position': 'WR',
                            'grade_source': 'espn',
                            'metric_value': 75.0,
                            'threshold_value': 85.0,
                            'quality_score': 70.0,
                            'generated_at': datetime.utcnow(),
                            'acknowledged': True,
                            'acknowledged_by': 'admin',
                            'acknowledged_at': datetime.utcnow()
                        }
                        
                        mock_repo.acknowledge_alert.return_value = None
                        mock_repo.get_recent_alerts.return_value = [alert_dict]
                        
                        result = service.acknowledge_alert(alert_id, 'admin')
                        
                        assert isinstance(result, AlertResponse)
                        assert result.acknowledged is True
                        assert result.acknowledged_by == 'admin'
    
    def test_acknowledge_multiple_alerts(self):
        """Test acknowledging multiple alerts."""
        mock_session = Mock()
        alert_ids = [str(uuid4()), str(uuid4()), str(uuid4())]
        
        with patch('backend.api.quality_service.AlertGenerator'):
            with patch('backend.api.quality_service.EmailNotificationService'):
                with patch('backend.api.quality_service.AlertRepository'):
                    with patch('backend.api.quality_service.AlertManager'):
                        service = QualityAPIService(mock_session)
                        
                        mock_repo = Mock()
                        service.alert_repository = mock_repo
                        mock_repo.acknowledge_alert.return_value = None
                        
                        result = service.acknowledge_multiple_alerts(alert_ids, 'admin')
                        
                        assert result.acknowledged == 3
                        assert result.failed == 0
                        assert len(result.alert_ids) == 3


class TestAlertListResponse:
    """Tests for AlertListResponse schema."""
    
    def test_alert_list_response_creation(self):
        """Test creating AlertListResponse."""
        alert = AlertResponse(
            id=str(uuid4()),
            alert_type='low_coverage',
            severity='critical',
            message='Test alert',
            position='QB',
            grade_source='pff',
            metric_value=65.0,
            threshold_value=70.0,
            quality_score=72.0,
            generated_at=datetime.utcnow(),
            acknowledged=False
        )
        
        response = AlertListResponse(
            total_count=1,
            returned_count=1,
            alerts=[alert],
            unacknowledged_count=1,
            critical_count=1,
            warning_count=0,
            info_count=0
        )
        
        assert response.total_count == 1
        assert response.critical_count == 1
        assert len(response.alerts) == 1


class TestAlertSummaryResponse:
    """Tests for AlertSummaryResponse schema."""
    
    def test_alert_summary_response_creation(self):
        """Test creating AlertSummaryResponse."""
        response = AlertSummaryResponse(
            total_alerts=10,
            unacknowledged_critical=3,
            unacknowledged_warning=5,
            unacknowledged_info=2,
            by_position={'QB': 5, 'WR': 3, 'RB': 2},
            by_source={'pff': 6, 'espn': 4},
            by_type={'low_coverage': 5, 'high_outliers': 5},
            critical_positions=['QB'],
            critical_sources=['pff'],
            oldest_unacknowledged_alert_age_hours=24.5
        )
        
        assert response.total_alerts == 10
        assert response.unacknowledged_critical == 3
        assert 'QB' in response.by_position
        assert response.oldest_unacknowledged_alert_age_hours == 24.5


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
