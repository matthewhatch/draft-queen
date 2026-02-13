"""Database loaders for NFL prospect data."""

import logging
from typing import List, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
from backend.database import db
from backend.database.models import (
    Prospect,
    ProspectMeasurable,
    StagingProspect,
    DataLoadAudit,
)
from data_pipeline.validators import (
    SchemaValidator,
    BusinessRuleValidator,
    DuplicateDetector,
)
from data_pipeline.models import ProspectDataSchema, ProspectMeasurableSchema

logger = logging.getLogger(__name__)


class ProspectLoader:
    """Loads validated prospect data into PostgreSQL."""

    @staticmethod
    def load_prospects(
        prospects: List[Dict[str, Any]], source: str = "nfl_com"
    ) -> Dict[str, Any]:
        """
        Load prospects into database with validation and duplicate detection.

        Args:
            prospects: List of prospect dictionaries
            source: Data source identifier

        Returns:
            Load result statistics
        """
        logger.info(f"Starting prospect load: {len(prospects)} records from {source}")

        load_id = datetime.utcnow().isoformat()
        result = {
            "load_id": load_id,
            "source": source,
            "load_date": datetime.utcnow(),
            "total_received": len(prospects),
            "total_validated": 0,
            "total_inserted": 0,
            "total_updated": 0,
            "total_failed": 0,
            "errors": [],
        }

        try:
            # Step 1: Schema validation
            logger.info("Step 1: Validating prospect schemas")
            valid_count = 0
            invalid_prospects = []

            for prospect_data in prospects:
                validation_result = SchemaValidator.validate_prospect(prospect_data)
                if validation_result.is_valid:
                    valid_count += 1
                else:
                    invalid_prospects.append(
                        {
                            "data": prospect_data,
                            "errors": validation_result.errors,
                        }
                    )

            result["total_validated"] = valid_count
            result["total_failed"] = len(invalid_prospects)

            if invalid_prospects:
                logger.warning(
                    f"Schema validation failed for {len(invalid_prospects)} prospects"
                )
                for invalid in invalid_prospects[:5]:  # Log first 5
                    logger.warning(
                        f"  Prospect: {invalid['data'].get('name', 'UNKNOWN')}, "
                        f"Errors: {invalid['errors']}"
                    )

            # Step 2: Business rule validation
            logger.info("Step 2: Validating business rules")
            validated_prospects = []
            for prospect_data in prospects:
                validation_result = SchemaValidator.validate_prospect(prospect_data)
                if validation_result.is_valid:
                    business_result = BusinessRuleValidator.validate_prospect_completeness(
                        prospect_data
                    )
                    if business_result.is_valid:
                        validated_prospects.append(prospect_data)
                    else:
                        logger.warning(
                            f"Business rule validation failed for {prospect_data.get('name')}: "
                            f"{business_result.errors}"
                        )

            logger.info(f"Business rule validation: {len(validated_prospects)} passed")

            # Step 3: Duplicate detection
            logger.info("Step 3: Detecting duplicates")
            duplicate_dict = DuplicateDetector.detect_duplicates_in_batch(
                validated_prospects
            )
            duplicates = []
            for key, indices in duplicate_dict.items():
                if len(indices) > 0:
                    duplicates.append(validated_prospects[indices[0]])
            
            if duplicates:
                logger.warning(f"Found {len(duplicates)} duplicate prospects")
                # Filter out duplicates, keeping only first occurrence
                seen_keys = set()
                filtered_prospects = []
                for p in validated_prospects:
                    key = DuplicateDetector.get_duplicate_key(p)
                    if key not in seen_keys:
                        filtered_prospects.append(p)
                        seen_keys.add(key)
                validated_prospects = filtered_prospects
            
            logger.info(f"After duplicate removal: {len(validated_prospects)} prospects")

            # Step 4: Database upsert
            logger.info(f"Step 4: Upserting {len(validated_prospects)} prospects")
            from backend.database import DatabaseConnection
            db_conn = DatabaseConnection()
            session = db_conn.get_session()

            try:
                for prospect_data in validated_prospects:
                    # Find existing prospect
                    existing = session.query(Prospect).filter_by(
                        name=prospect_data["name"],
                        position=prospect_data["position"],
                        college=prospect_data["college"],
                    ).first()

                    if existing:
                        # Update existing
                        existing.height = prospect_data.get("height")
                        existing.weight = prospect_data.get("weight")
                        existing.draft_grade = prospect_data.get("draft_grade")
                        existing.round_projection = prospect_data.get(
                            "round_projection"
                        )
                        existing.status = prospect_data.get("status", "active")
                        existing.updated_at = datetime.utcnow()
                        result["total_updated"] += 1
                        logger.debug(f"Updated prospect: {prospect_data['name']}")
                    else:
                        # Insert new
                        prospect = Prospect(
                            name=prospect_data["name"],
                            position=prospect_data["position"],
                            college=prospect_data["college"],
                            height=prospect_data.get("height"),
                            weight=prospect_data.get("weight"),
                            draft_grade=prospect_data.get("draft_grade"),
                            round_projection=prospect_data.get("round_projection"),
                            status=prospect_data.get("status", "active"),
                        )
                        session.add(prospect)
                        result["total_inserted"] += 1
                        logger.debug(f"Inserted prospect: {prospect_data['name']}")

                # Commit transaction
                session.commit()
                logger.info(
                    f"Prospect load completed: "
                    f"{result['total_inserted']} inserted, "
                    f"{result['total_updated']} updated"
                )

            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Database error during prospect load: {e}")
                result["errors"].append(f"Database error: {str(e)}")
                raise
            finally:
                session.close()

            # Step 5: Record audit trail
            ProspectLoader._record_audit(result)

            return result

        except Exception as e:
            logger.error(f"Prospect load failed: {e}", exc_info=True)
            result["errors"].append(str(e))
            ProspectLoader._record_audit(result)
            raise

    @staticmethod
    def _record_audit(result: Dict[str, Any]) -> None:
        """Record load audit trail."""
        try:
            from backend.database import DatabaseConnection
            db_conn = DatabaseConnection()
            session = db_conn.get_session()
            
            audit = DataLoadAudit(
                data_source=result["source"],
                load_date=result["load_date"],
                total_records_received=result["total_received"],
                records_validated=result["total_validated"],
                records_inserted=result["total_inserted"],
                records_updated=result["total_updated"],
                records_failed=result["total_failed"],
                status="success" if result["total_failed"] == 0 else "partial",
                error_summary=(
                    "\n".join(result["errors"]) if result["errors"] else None
                ),
                duration_seconds=0,  # Could calculate if needed
            )
            session.add(audit)
            session.commit()
            session.close()
            logger.info(f"Audit trail recorded for load {result['load_id']}")
        except Exception as e:
            logger.error(f"Failed to record audit trail: {e}")


def load_nfl_com_data() -> Dict[str, Any]:
    """
    Main entry point for NFL.com data loading.

    Returns:
        Load result statistics
    """
    from data_pipeline.sources import MockNFLComConnector

    logger.info("Starting NFL.com data load process")

    try:
        # Use mock connector for now (replace with real connector in production)
        connector = MockNFLComConnector()

        # Check API health
        if not connector.health_check():
            logger.warning("NFL.com API health check failed, proceeding anyway")

        # Fetch prospects
        prospects = connector.fetch_prospects()
        logger.info(f"Fetched {len(prospects)} prospects")

        # Load into database
        result = ProspectLoader.load_prospects(prospects)

        connector.close()

        return result

    except Exception as e:
        logger.error(f"NFL.com data load failed: {e}", exc_info=True)
        raise
