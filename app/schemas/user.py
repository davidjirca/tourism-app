from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    phone: Optional[str] = None
    full_name: Optional[str] = None


class UserUpdate(BaseModel):
    phone: Optional[str] = None
    full_name: Optional[str] = None

    class Config:
        orm_mode = True


class UserDB(UserBase):
    id: int
    phone: Optional[str] = None
    full_name: Optional[str] = None
    created_at: datetime
    is_active: bool
    is_admin: Optional[bool] = None

    class Config:
        orm_mode = True


class PasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8)