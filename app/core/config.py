from pydantic import BaseSettings, EmailStr, validator
import os
from typing import Optional, Dict, Any, List


class Settings(BaseSettings):
    PROJECT_NAME: str = "Travel Recommendation & Price Alert System"
    API_V1_STR: str = ""
    SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "super_secret_key_change_in_production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    ALGORITHM: str = "HS256"

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://username:password@localhost/travel_app")

    # Redis
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    WEATHER_CACHE_EXPIRATION: int = 3600  # 1 hour for weather
    PRICE_CACHE_EXPIRATION: int = 21600  # 6 hours for prices

    # External APIs
    OPENWEATHER_API_KEY: str = os.getenv("OPENWEATHER_API_KEY", "your_openweather_api_key")
    SKYSCANNER_API_KEY: str = os.getenv("SKYSCANNER_API_KEY", "your_skyscanner_api_key")
    NUMBEO_API_KEY: str = os.getenv("NUMBEO_API_KEY", "your_numbeo_api_key")

    # Twilio
    TWILIO_SID: str = os.getenv("TWILIO_SID", "your_twilio_sid")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "your_twilio_auth_token")
    TWILIO_PHONE_NUMBER: str = os.getenv("TWILIO_PHONE_NUMBER", "+1234567890")

    # Email
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
    EMAIL_SENDER: str = os.getenv("EMAIL_SENDER", "your_email@gmail.com")
    EMAIL_PASSWORD: str = os.getenv("EMAIL_PASSWORD", "your_email_password")

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str] | str:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()