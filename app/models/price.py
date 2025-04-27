from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True)
    destination_id = Column(Integer, ForeignKey("destinations.id"))
    flight_price = Column(Float)
    hotel_price = Column(Float)
    timestamp = Column(DateTime, server_default=func.now())

    # Relationships
    destination = relationship("Destination", back_populates="price_history")