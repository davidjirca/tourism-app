from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


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
