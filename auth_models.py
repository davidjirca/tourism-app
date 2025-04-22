from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


# Request Models
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    phone: Optional[str] = None
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenData(BaseModel):
    user_id: int
    email: Optional[str] = None


# Response Models
class Token(BaseModel):
    access_token: str
    token_type: str
    expires_at: datetime
    user_id: int


class UserResponse(BaseModel):
    id: int
    email: str
    phone: Optional[str] = None
    full_name: Optional[str] = None
    created_at: datetime
    is_active: bool

    class Config:
        orm_mode = True


class UserProfileUpdate(BaseModel):
    phone: Optional[str] = None
    full_name: Optional[str] = None

    class Config:
        orm_mode = True