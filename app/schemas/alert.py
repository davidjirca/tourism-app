from pydantic import BaseModel
from typing import Optional
from app.schemas.destination import DestinationResponse


class AlertPreferenceBase(BaseModel):
    price_threshold: Optional[float] = None
    alert_email: bool = True
    alert_sms: bool = False
    alert_push: bool = False
    frequency: str = "immediate"  # immediate, daily, weekly


class AlertPreferenceCreate(AlertPreferenceBase):
    destination_id: int


class AlertPreferenceUpdate(AlertPreferenceBase):
    pass


class AlertPreferenceDB(AlertPreferenceBase):
    id: int
    user_id: int
    destination_id: int

    class Config:
        orm_mode = True


class AlertPreferenceResponse(AlertPreferenceBase):
    id: int
    destination: DestinationResponse

    class Config:
        orm_mode = True
