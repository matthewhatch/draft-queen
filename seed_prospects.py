"""Seed the database with test prospect data."""

from backend.database import db
from backend.database.models import Prospect

# Test data
TEST_PROSPECTS = [
    {
        "name": "Patrick Mahomes II",
        "position": "QB",
        "college": "Texas Tech",
        "height": 6.2,
        "weight": 220,
        "draft_grade": 9.5,
    },
    {
        "name": "Derrick Henry",
        "position": "RB",
        "college": "Alabama",
        "height": 6.3,
        "weight": 247,
        "draft_grade": 8.8,
    },
    {
        "name": "DeAndre Washington",
        "position": "RB",
        "college": "Texas Tech",
        "height": 5.83,
        "weight": 211,
        "draft_grade": 7.2,
    },
    {
        "name": "Mike Evans",
        "position": "WR",
        "college": "Texas A&M",
        "height": 6.3,
        "weight": 231,
        "draft_grade": 9.1,
    },
    {
        "name": "Travis Kelce",
        "position": "TE",
        "college": "Cincinnati",
        "height": 6.4,
        "weight": 260,
        "draft_grade": 8.5,
    },
    {
        "name": "Christian McCaffrey",
        "position": "RB",
        "college": "Stanford",
        "height": 6.0,
        "weight": 202,
        "draft_grade": 9.3,
    },
    {
        "name": "Jalen Hurts",
        "position": "QB",
        "college": "Oklahoma",
        "height": 6.1,
        "weight": 212,
        "draft_grade": 8.2,
    },
    {
        "name": "Justin Jefferson",
        "position": "WR",
        "college": "LSU",
        "height": 6.1,
        "weight": 202,
        "draft_grade": 8.9,
    },
]

def seed_database():
    """Add test prospects to database."""
    session = db.SessionLocal()
    
    try:
        # Check if data already exists
        existing_count = session.query(Prospect).count()
        if existing_count > 0:
            print(f"Database already contains {existing_count} prospects. Skipping seed.")
            return
        
        # Add test data
        for prospect_data in TEST_PROSPECTS:
            prospect = Prospect(
                name=prospect_data["name"],
                position=prospect_data["position"],
                college=prospect_data["college"],
                height=prospect_data["height"],
                weight=prospect_data["weight"],
                draft_grade=prospect_data["draft_grade"],
                status="active",
                data_source="seed"
            )
            session.add(prospect)
        
        session.commit()
        print(f"✓ Seeded database with {len(TEST_PROSPECTS)} prospects")
    
    except Exception as e:
        print(f"✗ Error seeding database: {e}")
        session.rollback()
    
    finally:
        session.close()

if __name__ == "__main__":
    seed_database()
