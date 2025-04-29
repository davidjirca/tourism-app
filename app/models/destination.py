from sqlalchemy import Column, Integer, String, Float, ForeignKey, Table
from sqlalchemy.orm import relationship

from app.db.session import Base

# Association table for many-to-many relationship between users and destinations
user_destinations = Table(
    "user_destinations",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id")),
    Column("destination_id", Integer, ForeignKey("destinations.id")),
)


class Destination(Base):
    __tablename__ = "destinations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    airport_code = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    country = Column(String)
    description = Column(String, nullable=True)

    # Relationships
    price_history = relationship(
        "PriceHistory", back_populates="destination", cascade="all, delete-orphan"
    )
    users = relationship(
        "User", secondary=user_destinations, back_populates="destinations"
    )
    crime_data = relationship(
        "CrimeData", back_populates="destination", cascade="all, delete-orphan"
    )
    weather_data = relationship(
        "WeatherData", back_populates="destination", cascade="all, delete-orphan"
    )
