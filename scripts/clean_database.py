"""Clean the database - delete all prospects."""

from backend.database import db
from backend.database.models import Prospect

def clean_database():
    """Delete all prospect records."""
    session = db.SessionLocal()
    
    try:
        # Count before
        count_before = session.query(Prospect).count()
        print(f"Prospects before: {count_before}")
        
        # Delete all
        session.query(Prospect).delete()
        session.commit()
        
        # Count after
        count_after = session.query(Prospect).count()
        print(f"Prospects after: {count_after}")
        print("✓ Database cleaned successfully")
    
    except Exception as e:
        print(f"✗ Error cleaning database: {e}")
        session.rollback()
    
    finally:
        session.close()

if __name__ == "__main__":
    clean_database()
