from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class Token(BaseModel):
    access_token: str
    token_type: str
    expires_at: datetime
    user_id: int


class TokenData(BaseModel):
    user_id: int
    email: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str
