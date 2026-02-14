"""ProspectGrade model re-export from backend for data pipeline compatibility."""

# Import from backend where the model is actually defined
from backend.database.models import ProspectGrade

__all__ = ["ProspectGrade"]


    # Relationship back to Prospect
    prospect = relationship("Prospect", back_populates="grades")

    __table_args__ = (
        UniqueConstraint("prospect_id", "source", "grade_date", name="uq_prospect_grade_source_date"),
        Index("idx_grade_source", "source"),
        Index("idx_grade_prospect", "prospect_id"),
    )
