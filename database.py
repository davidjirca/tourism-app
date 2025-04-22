# database.py - Database Models and Configuration

from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from typing import List, Optional
import os
from datetime import datetime
from pydantic import BaseModel

# Database URL (should use environment variables in production)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://username:password@localhost/travel_app")

# Create SQLAlchemy engine and session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Association table for many-to-many relationship between users and destinations
user_destinations = Table(
    "user_destinations",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id")),
    Column("destination_id", Integer, ForeignKey("destinations.id"))
)


# Database Models
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    phone = Column(String, nullable=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    is_active = Column(Boolean, default=True)

    # Relationships
    alert_preferences = relationship("AlertPreference", back_populates="user")
    destinations = relationship("Destination", secondary=user_destinations, back_populates="users")


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
    price_history = relationship("PriceHistory", back_populates="destination")
    users = relationship("User", secondary=user_destinations, back_populates="destinations")
    crime_data = relationship("CrimeData", back_populates="destination")
    weather_data = relationship("WeatherData", back_populates="destination")


class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True)
    destination_id = Column(Integer, ForeignKey("destinations.id"))
    flight_price = Column(Float)
    hotel_price = Column(Float)
    timestamp = Column(DateTime, server_default=func.now())

    # Relationships
    destination = relationship("Destination", back_populates="price_history")


class CrimeData(Base):
    __tablename__ = "crime_data"

    id = Column(Integer, primary_key=True, index=True)
    destination_id = Column(Integer, ForeignKey("destinations.id"))
    crime_index = Column(Float)
    safety_index = Column(Float)
    timestamp = Column(DateTime, server_default=func.now())

    # Relationships
    destination = relationship("Destination", back_populates="crime_data")


class WeatherData(Base):
    __tablename__ = "weather_data"

    id = Column(Integer, primary_key=True, index=True)
    destination_id = Column(Integer, ForeignKey("destinations.id"))
    temperature = Column(Float)
    condition = Column(String)
    weather_score = Column(Float)
    timestamp = Column(DateTime, server_default=func.now())

    # Relationships
    destination = relationship("Destination", back_populates="weather_data")


class AlertPreference(Base):
    __tablename__ = "alert_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    destination_id = Column(Integer, ForeignKey("destinations.id"))
    price_threshold = Column(Float, nullable=True)
    alert_email = Column(Boolean, default=True)
    alert_sms = Column(Boolean, default=False)
    alert_push = Column(Boolean, default=False)
    frequency = Column(String, default="immediate")  # immediate, daily, weekly

    # Relationships
    user = relationship("User", back_populates="alert_preferences")


# Pydantic Models for API
class UserCreate(BaseModel):
    email: str
    password: str
    phone: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    email: str
    phone: Optional[str] = None
    created_at: datetime

    class Config:
        orm_mode = True


class DestinationCreate(BaseModel):
    name: str
    airport_code: str
    latitude: float
    longitude: float
    country: str
    description: Optional[str] = None


class DestinationResponse(BaseModel):
    id: int
    name: str
    airport_code: str
    country: str
    description: Optional[str] = None
    current_flight_price: Optional[float] = None
    current_hotel_price: Optional[float] = None

    class Config:
        orm_mode = True


class AlertPreferenceCreate(BaseModel):
    destination_id: int
    price_threshold: Optional[float] = None
    alert_email: bool = True
    alert_sms: bool = False
    alert_push: bool = False
    frequency: str = "immediate"


class AlertPreferenceResponse(BaseModel):
    id: int
    destination: DestinationResponse
    price_threshold: Optional[float] = None
    alert_email: bool
    alert_sms: bool
    alert_push: bool
    frequency: str

    class Config:
        orm_mode = True


# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Create all tables
def create_tables():
    Base.metadata.create_all(bind=engine)


# Initialize with sample destinations
def initialize_destinations():
    db = SessionLocal()

    # Check if destinations already exist
    if db.query(Destination).count() == 0:
        destinations = [
            Destination(
                name="Bali, Indonesia",
                airport_code="DPS",
                latitude=-8.3405,
                longitude=115.092,
                country="Indonesia",
                description="Beautiful island paradise with beaches, temples, and rich culture"
            ),
            Destination(
                name="Phuket, Thailand",
                airport_code="HKT",
                latitude=7.8804,
                longitude=98.3923,
                country="Thailand",
                description="Thailand's largest island with stunning beaches and nightlife"
            ),
            # Add more destinations as needed
        ]

        db.add_all(destinations)
        db.commit()

    db.close()