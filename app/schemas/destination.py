from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class DestinationBase(BaseModel):
    name: str
    airport_code: str
    country: str
    description: Optional[str] = None


class DestinationCreate(DestinationBase):
    latitude: float
    longitude: float


class DestinationUpdate(BaseModel):
    name: Optional[str] = None
    airport_code: Optional[str] = None
    country: Optional[str] = None
    description: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class DestinationDB(DestinationBase):
    id: int
    latitude: float
    longitude: float

    class Config:
        orm_mode = True


class DestinationResponse(DestinationBase):
    id: int
    current_flight_price: Optional[float] = None
    current_hotel_price: Optional[float] = None

    class Config:
        orm_mode = True


class PriceHistoryPoint(BaseModel):
    date: str
    flight_price: float
    hotel_price: float


class PriceHistoryResponse(BaseModel):
    destination: str
    data_points: int
    prices: List[PriceHistoryPoint]


class WeatherDataResponse(BaseModel):
    temperature: float
    condition: str
    weather_score: float
    timestamp: datetime

    class Config:
        orm_mode = True


class CrimeDataResponse(BaseModel):
    crime_index: float
    safety_index: float
    timestamp: datetime

    class Config:
        orm_mode = True