from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey,
    UniqueConstraint, Index, func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from backend.database.models import Base


class ProspectGrade(Base):
    __tablename__ = "prospect_grades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    prospect_id = Column(UUID(as_uuid=True), ForeignKey("prospects.id", ondelete="CASCADE"), nullable=False, index=True)
    source = Column(String(50), nullable=False, index=True)          # "pff", "espn", "nfl", etc.
    grade_overall = Column(Float, nullable=True)                      # PFF 0–100 scale (store raw)
    grade_normalized = Column(Float, nullable=True)                   # Normalized to 5.0–10.0 scale
    grade_position = Column(String(10), nullable=True)                # Position at time of grading (PFF-native, e.g. "LT")
    match_confidence = Column(Float, nullable=True)                   # Fuzzy-match score 0–100
    grade_date = Column(DateTime, nullable=True)                      # Date grade was issued
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50), default="pff_loader")

    # Relationship back to Prospect
    prospect = relationship("Prospect", back_populates="grades")

    __table_args__ = (
        UniqueConstraint("prospect_id", "source", "grade_date", name="uq_prospect_grade_source_date"),
        Index("idx_grade_source", "source"),
        Index("idx_grade_prospect", "prospect_id"),
    )
