#!/usr/bin/env python
"""Generate test quality alerts for development."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from config import settings
from backend.database.models import Base, Prospect
from data_pipeline.models.quality import QualityAlert
import uuid

def generate_test_alerts():
    """Generate test alerts in the database."""
    engine = create_engine(settings.database_url)
    # Tables already exist from migrations
    # Base.metadata.create_all(engine)
    
    with Session(engine) as session:
        # First, ensure we have a test prospect
        test_prospect = session.query(Prospect).first()
        
        if not test_prospect:
            test_prospect = Prospect(
                id=uuid.uuid4(),
                name="Test Prospect",
                position="QB",
                college="Test University",
                status="active",
                created_by="test_script"
            )
            session.add(test_prospect)
            session.flush()
        
        prospect_id = test_prospect.id
        
        # Generate test alerts
        alerts_data = [
            {
                "alert_type": "outlier",
                "severity": "critical",
                "grade_source": "nfl",
                "field_name": "grade_overall",
                "field_value": "3.2",
                "expected_value": "7.5",
                "review_notes": "Low overall grade detected",
            },
            {
                "alert_type": "grade_change",
                "severity": "warning",
                "grade_source": "espn",
                "field_name": "grade_change",
                "field_value": "-2.1",
                "expected_value": "stable",
                "review_notes": "Significant grade drop noted",
            },
            {
                "alert_type": "data_completeness",
                "severity": "info",
                "grade_source": "nfl",
                "field_name": "combine_metrics",
                "field_value": "complete",
                "expected_value": "complete",
                "review_notes": "All combine data collected",
            },
        ]
        
        # Add the alerts
        now = datetime.utcnow()
        for i, alert_data in enumerate(alerts_data):
            alert = QualityAlert(
                prospect_id=prospect_id,
                alert_type=alert_data["alert_type"],
                severity=alert_data["severity"],
                grade_source=alert_data["grade_source"],
                field_name=alert_data["field_name"],
                field_value=alert_data["field_value"],
                expected_value=alert_data["expected_value"],
                review_notes=alert_data.get("review_notes"),
                created_at=now - timedelta(hours=i),
            )
            session.add(alert)
        
        session.commit()
        print("✅ Test alerts generated successfully!")
        print(f"   - Prospect: {test_prospect.name} ({test_prospect.position})")
        print(f"   - Total alerts: {len(alerts_data)}")
        print(f"   - Critical: 1, Warning: 1, Info: 1")

if __name__ == "__main__":
    try:
        generate_test_alerts()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
