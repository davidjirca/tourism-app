from sqlalchemy.orm import Session
from app.db.session import Base, engine
from app.models.destination import Destination


def create_tables():
    """Create database tables."""
    Base.metadata.create_all(bind=engine)


def initialize_destinations(db: Session):
    """Initialize sample destinations if none exist."""
    # Check if destinations already exist
    if db.query(Destination).count() == 0:
        destinations = [
            Destination(
                name="Bali, Indonesia",
                airport_code="DPS",
                latitude=-8.3405,
                longitude=115.092,
                country="Indonesia",
                description="Beautiful island paradise with beaches, temples, and rich culture",
            ),
            Destination(
                name="Phuket, Thailand",
                airport_code="HKT",
                latitude=7.8804,
                longitude=98.3923,
                country="Thailand",
                description="Thailand's largest island with stunning beaches and nightlife",
            ),
            Destination(
                name="Paris, France",
                airport_code="CDG",
                latitude=48.8566,
                longitude=2.3522,
                country="France",
                description="The City of Light with iconic landmarks, art, and cuisine",
            ),
            Destination(
                name="Tokyo, Japan",
                airport_code="HND",
                latitude=35.6762,
                longitude=139.6503,
                country="Japan",
                description="Modern metropolis with traditional charm, tech, and amazing food",
            ),
            Destination(
                name="Barcelona, Spain",
                airport_code="BCN",
                latitude=41.3851,
                longitude=2.1734,
                country="Spain",
                description="Vibrant coastal city with stunning architecture and beach lifestyle",
            ),
        ]

        db.add_all(destinations)
        db.commit()


def init_db(db: Session):
    """Initialize database (create tables and add sample data)."""
    create_tables()
    initialize_destinations(db)
