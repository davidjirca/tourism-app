from sqlalchemy import Column, Integer, Float, Boolean, String, ForeignKey
from sqlalchemy.orm import relationship

from app.db.session import Base


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
