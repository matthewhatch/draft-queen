"""PFF Grade Loader - Integration of PFF grades into the database.

Implements fuzzy matching to link PFF prospects to DB prospects,
and upserts grade records with audit trails.
"""

from datetime import datetime, timezone
import logging
from typing import Optional, Tuple
from rapidfuzz import fuzz, process
from sqlalchemy.orm import Session

from backend.database.models import Prospect, DataLoadAudit
from data_pipeline.models.prospect_grades import ProspectGrade
from data_pipeline.validators.pff_validator import (
    normalize_pff_grade,
    map_pff_position_to_db,
    PFFDataValidator,
)

logger = logging.getLogger(__name__)

# Fuzzy matching thresholds
MATCH_THRESHOLD_HIGH = 90      # Auto-accept
MATCH_THRESHOLD_LOW = 75       # Reject below this


class PFFGradeLoader:
    """Load PFF grades into the database with fuzzy matching."""
    
    def __init__(self, session: Session):
        """Initialize loader with database session.
        
        Args:
            session: SQLAlchemy Session
        """
        self.session = session
        self.stats = {
            "total": 0,
            "matched": 0,
            "inserted": 0,
            "updated": 0,
            "unmatched": 0,
            "errors": 0,
        }
    
    def load(self, pff_prospects: list[dict]) -> dict:
        """Main entry point: load PFF grades into database.
        
        Args:
            pff_prospects: List of raw PFF prospect dicts from scraper
            
        Returns:
            Stats dict with counts (total, matched, inserted, updated, unmatched, errors)
        """
        # 1. Validate input
        validated = PFFDataValidator.validate_batch(pff_prospects)
        self.stats["total"] = len(validated)
        
        if self.stats["total"] == 0:
            logger.warning("No PFF prospects to load after validation")
            self._write_audit()
            return self.stats
        
        # 2. Load all DB prospects for matching (single query)
        db_prospects = self.session.query(Prospect).all()
        prospect_index = self._build_match_index(db_prospects)
        
        # 3. Process each PFF prospect
        for pff_data in validated:
            try:
                self._process_one(pff_data, prospect_index)
            except Exception as e:
                logger.error(f"Error processing {pff_data.get('name')}: {e}")
                self.stats["errors"] += 1
        
        # 4. Commit transaction
        try:
            self.session.commit()
        except Exception as e:
            logger.error(f"Commit error: {e}")
            self.session.rollback()
            self.stats["errors"] += 1
        
        # 5. Log summary
        if self.stats["unmatched"] > 0:
            logger.warning(f"{self.stats['unmatched']} PFF prospects could not be matched")
        
        # 6. Write audit record
        self._write_audit()
        
        return self.stats
    
    def _build_match_index(self, db_prospects: list[Prospect]) -> list[dict]:
        """Pre-process DB prospects into a fuzzy-matchable index.
        
        Args:
            db_prospects: List of Prospect ORM objects
            
        Returns:
            List of dicts with normalized fields for matching
        """
        return [
            {
                "id": p.id,
                "name": p.name.lower().strip() if p.name else "",
                "position": p.position,
                "college": (p.college or "").lower().strip(),
                "obj": p,
            }
            for p in db_prospects
        ]
    
    def _process_one(self, pff_data: dict, prospect_index: list[dict]):
        """Match one PFF prospect and upsert grade.
        
        Args:
            pff_data: Raw PFF prospect dict
            prospect_index: Pre-built index of DB prospects
        """
        match = self._fuzzy_match(pff_data, prospect_index)
        
        if match is None:
            self.stats["unmatched"] += 1
            logger.info(
                f"UNMATCHED: {pff_data['name']} "
                f"({pff_data.get('position')}, {pff_data.get('school')})"
            )
            return
        
        prospect_id, confidence = match
        self.stats["matched"] += 1
        
        # Extract grade data
        pff_grade_raw = float(pff_data["grade"])
        grade_date = (
            datetime.fromisoformat(pff_data["scraped_at"])
            if pff_data.get("scraped_at")
            else datetime.now(timezone.utc)
        )
        
        # Check for existing grade (upsert)
        existing = (
            self.session.query(ProspectGrade)
            .filter_by(prospect_id=prospect_id, source="pff")
            .first()
        )
        
        if existing:
            # Update existing grade
            existing.grade_overall = pff_grade_raw
            existing.grade_normalized = normalize_pff_grade(pff_grade_raw)
            existing.match_confidence = confidence
            existing.grade_position = pff_data.get("position")
            existing.grade_date = grade_date
            existing.updated_at = datetime.now(timezone.utc)
            self.stats["updated"] += 1
            logger.debug(f"UPDATED: {pff_data['name']} (confidence={confidence})")
        else:
            # Insert new grade
            grade = ProspectGrade(
                prospect_id=prospect_id,
                source="pff",
                grade_overall=pff_grade_raw,
                grade_normalized=normalize_pff_grade(pff_grade_raw),
                grade_position=pff_data.get("position"),
                match_confidence=confidence,
                grade_date=grade_date,
            )
            self.session.add(grade)
            self.stats["inserted"] += 1
            logger.debug(f"INSERTED: {pff_data['name']} (confidence={confidence})")
    
    def _fuzzy_match(
        self, pff_data: dict, prospect_index: list[dict]
    ) -> Optional[Tuple]:
        """Weighted fuzzy match: name (60%), position (25%), college (15%).
        
        Args:
            pff_data: Raw PFF prospect dict
            prospect_index: Pre-built index of DB prospects
            
        Returns:
            Tuple of (prospect_id, confidence_score) or None
        """
        pff_name = pff_data["name"].lower().strip()
        pff_position = map_pff_position_to_db(pff_data.get("position", ""))
        # NOTE: PFF key is "school" not "college"
        pff_college = (pff_data.get("school") or "").lower().strip()
        # Guard against em-dash for missing school
        if pff_college == "—":
            pff_college = ""
        
        best_match = None
        best_score = 0.0
        
        for candidate in prospect_index:
            # Name similarity (token_sort handles "John Smith Jr." vs "Smith, John")
            name_score = fuzz.token_sort_ratio(pff_name, candidate["name"])
            
            # Position match (exact after mapping = 100, else 0)
            pos_score = (
                100.0
                if pff_position and pff_position == candidate["position"]
                else 0.0
            )
            
            # College similarity
            college_score = (
                fuzz.token_sort_ratio(pff_college, candidate["college"])
                if pff_college
                else 50.0
            )
            
            # Weighted composite
            composite = (name_score * 0.60) + (pos_score * 0.25) + (college_score * 0.15)
            
            if composite > best_score:
                best_score = composite
                best_match = candidate["id"]
        
        if best_score >= MATCH_THRESHOLD_LOW:
            return (best_match, round(best_score, 1))
        
        return None
    
    def _write_audit(self):
        """Write a DataLoadAudit record for this load run."""
        audit = DataLoadAudit(
            data_source="pff",
            total_records_received=self.stats["total"],
            records_validated=self.stats["matched"],
            records_inserted=self.stats["inserted"],
            records_updated=self.stats["updated"],
            records_skipped=self.stats["unmatched"],
            records_failed=self.stats["errors"],
            status="success" if self.stats["errors"] == 0 else "partial",
            error_summary=f"unmatched={self.stats['unmatched']}, errors={self.stats['errors']}",
            error_details={
                "unmatched": self.stats["unmatched"],
                "errors": self.stats["errors"],
            },
            operator="pff_grade_loader",
        )
        self.session.add(audit)
        try:
            self.session.commit()
        except Exception as e:
            logger.error(f"Failed to write audit record: {e}")
            self.session.rollback()
