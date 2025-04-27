from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class CrimeData(Base):
    __tablename__ = "crime_data"

    id = Column(Integer, primary_key=True, index=True)
    destination_id = Column(Integer, ForeignKey("destinations.id"))
    crime_index = Column(Float)
    safety_index = Column(Float)
    timestamp = Column(DateTime, server_default=func.now())

    # Relationships
    destination = relationship("Destination", back_populates="crime_data")