"""ProspectGrade model re-export from backend for data pipeline compatibility."""

# Import from backend where the model is actually defined
from backend.database.models import ProspectGrade

__all__ = ["ProspectGrade"]
