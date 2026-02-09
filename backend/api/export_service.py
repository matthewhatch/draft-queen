"""Export service for generating prospect data exports in various formats."""

import io
import json
import logging
from typing import List, Optional, BinaryIO
from enum import Enum

from sqlalchemy.orm import Session
import pandas as pd

from backend.database.models import Prospect
from backend.api.schemas import QueryFilterSchema

logger = logging.getLogger(__name__)


class ExportFormat(str, Enum):
    """Supported export formats."""
    JSON = "json"
    JSONL = "jsonl"  # JSON Lines (one JSON object per line)
    CSV = "csv"
    PARQUET = "parquet"


class ExportService:
    """Service for exporting prospect data in various formats."""
    
    @staticmethod
    def _query_prospects(
        db: Session,
        filters: Optional[QueryFilterSchema] = None
    ) -> List[Prospect]:
        """Query prospects with optional filters."""
        from backend.api.query_service import QueryService
        
        if filters is None:
            filters = QueryFilterSchema(skip=0, limit=500)
        
        prospects, _, _, _ = QueryService.execute_query(db, filters)
        return prospects
    
    @staticmethod
    def _prospect_to_dict(prospect: Prospect) -> dict:
        """Convert prospect model to dictionary."""
        return {
            "id": str(prospect.id),
            "name": prospect.name,
            "position": prospect.position,
            "college": prospect.college,
            "height": float(prospect.height) if prospect.height else None,
            "weight": prospect.weight,
            "draft_grade": float(prospect.draft_grade) if prospect.draft_grade else None,
            "round_projection": prospect.round_projection,
            "status": prospect.status,
            "created_at": prospect.created_at.isoformat() if prospect.created_at else None,
            "updated_at": prospect.updated_at.isoformat() if prospect.updated_at else None,
        }
    
    @staticmethod
    def export_json(
        db: Session,
        filters: Optional[QueryFilterSchema] = None,
        pretty: bool = True
    ) -> str:
        """
        Export prospects as JSON.
        
        Args:
            db: Database session
            filters: Optional query filters
            pretty: Whether to pretty-print JSON (default True)
        
        Returns:
            JSON string
        """
        prospects = ExportService._query_prospects(db, filters)
        data = [ExportService._prospect_to_dict(p) for p in prospects]
        
        if pretty:
            return json.dumps(data, indent=2)
        else:
            return json.dumps(data)
    
    @staticmethod
    def export_jsonl(
        db: Session,
        filters: Optional[QueryFilterSchema] = None
    ) -> str:
        """
        Export prospects as JSON Lines (one JSON object per line).
        
        Args:
            db: Database session
            filters: Optional query filters
        
        Returns:
            JSON Lines string
        """
        prospects = ExportService._query_prospects(db, filters)
        lines = [
            json.dumps(ExportService._prospect_to_dict(p))
            for p in prospects
        ]
        return "\n".join(lines)
    
    @staticmethod
    def export_csv(
        db: Session,
        filters: Optional[QueryFilterSchema] = None
    ) -> str:
        """
        Export prospects as CSV.
        
        Args:
            db: Database session
            filters: Optional query filters
        
        Returns:
            CSV string
        """
        prospects = ExportService._query_prospects(db, filters)
        data = [ExportService._prospect_to_dict(p) for p in prospects]
        
        if not data:
            return ""
        
        df = pd.DataFrame(data)
        return df.to_csv(index=False)
    
    @staticmethod
    def export_parquet(
        db: Session,
        filters: Optional[QueryFilterSchema] = None
    ) -> bytes:
        """
        Export prospects as Parquet.
        
        Args:
            db: Database session
            filters: Optional query filters
        
        Returns:
            Parquet bytes
        """
        try:
            import pyarrow.parquet as pq
            import pyarrow as pa
        except ImportError:
            raise ImportError(
                "pyarrow is required for Parquet export. "
                "Install it with: poetry add pyarrow"
            )
        
        prospects = ExportService._query_prospects(db, filters)
        data = [ExportService._prospect_to_dict(p) for p in prospects]
        
        if not data:
            # Return empty parquet with schema
            df = pd.DataFrame()
        else:
            df = pd.DataFrame(data)
        
        # Convert to Parquet
        output = io.BytesIO()
        df.to_parquet(output, engine='pyarrow', index=False)
        output.seek(0)
        return output.getvalue()
    
    @staticmethod
    def export_to_format(
        db: Session,
        format: ExportFormat,
        filters: Optional[QueryFilterSchema] = None,
        pretty: bool = True
    ):
        """
        Export prospects in specified format.
        
        Args:
            db: Database session
            format: Export format (json, jsonl, csv, parquet)
            filters: Optional query filters
            pretty: Whether to pretty-print (for JSON formats)
        
        Returns:
            Exported data (str or bytes depending on format)
        
        Raises:
            ValueError: If format is not supported
        """
        logger.info(f"Exporting prospects in {format.value} format")
        
        if format == ExportFormat.JSON:
            return ExportService.export_json(db, filters, pretty)
        elif format == ExportFormat.JSONL:
            return ExportService.export_jsonl(db, filters)
        elif format == ExportFormat.CSV:
            return ExportService.export_csv(db, filters)
        elif format == ExportFormat.PARQUET:
            return ExportService.export_parquet(db, filters)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    @staticmethod
    def get_file_extension(format: ExportFormat) -> str:
        """Get file extension for export format."""
        extensions = {
            ExportFormat.JSON: "json",
            ExportFormat.JSONL: "jsonl",
            ExportFormat.CSV: "csv",
            ExportFormat.PARQUET: "parquet",
        }
        return extensions.get(format, format.value)
    
    @staticmethod
    def get_content_type(format: ExportFormat) -> str:
        """Get MIME content type for export format."""
        content_types = {
            ExportFormat.JSON: "application/json",
            ExportFormat.JSONL: "application/x-ndjson",
            ExportFormat.CSV: "text/csv",
            ExportFormat.PARQUET: "application/octet-stream",
        }
        return content_types.get(format, "application/octet-stream")
