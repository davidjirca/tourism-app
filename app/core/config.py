from pydantic import BaseSettings, EmailStr, validator, SecretStr
from typing import Optional, List, Any
import os
from urllib.parse import quote


class Settings(BaseSettings):
    # Project information
    PROJECT_NAME: str = "Travel Recommendation & Price Alert System"
    API_V1_STR: str = ""
    VERSION: str = "1.0.0"

    # Security
    SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY", "change_this_to_a_long_random_string_in_production"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    ALGORITHM: str = "HS256"

    @validator("SECRET_KEY")
    def validate_secret_key(cls, v):
        if v == "change_this_to_a_long_random_string_in_production":
            # Allow the default in development mode only
            if os.getenv("ENVIRONMENT", "development") == "production":
                raise ValueError("Secret key must be changed in production")
        elif len(v) < 32:
            raise ValueError("Secret key should be at least 32 characters long")
        return v

    # Database
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", 5432))
    DB_USER: str = os.getenv("DB_USER", "username")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "password")
    DB_NAME: str = os.getenv("DB_NAME", "travel_app")
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")

    @validator("DATABASE_URL", pre=True)
    def assemble_db_url(cls, v, values):
        if v is not None:
            return v

        return f"postgresql://{values['DB_USER']}:{quote(values['DB_PASSWORD'])}@{values['DB_HOST']}:{values['DB_PORT']}/{values['DB_NAME']}"

    # Redis
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD")
    REDIS_DB: int = int(os.getenv("REDIS_DB", 0))

    # Cache expiration times (in seconds)
    WEATHER_CACHE_EXPIRATION: int = int(
        os.getenv("WEATHER_CACHE_EXPIRATION", 3600)
    )  # 1 hour for weather
    PRICE_CACHE_EXPIRATION: int = int(
        os.getenv("PRICE_CACHE_EXPIRATION", 21600)
    )  # 6 hours for prices

    # External APIs
    OPENWEATHER_API_KEY: str = os.getenv(
        "OPENWEATHER_API_KEY", "your_openweather_api_key"
    )
    SKYSCANNER_API_KEY: str = os.getenv("SKYSCANNER_API_KEY", "your_skyscanner_api_key")
    NUMBEO_API_KEY: str = os.getenv("NUMBEO_API_KEY", "your_numbeo_api_key")

    @validator("OPENWEATHER_API_KEY", "SKYSCANNER_API_KEY", "NUMBEO_API_KEY")
    def validate_api_keys(cls, v, values, field):
        default_value = f"your_{field.name.lower()}"
        if v == default_value:
            if os.getenv("ENVIRONMENT", "development") == "production":
                raise ValueError(f"{field.name} must be set in production")
        return v

    # Twilio
    TWILIO_SID: str = os.getenv("TWILIO_SID", "your_twilio_sid")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "your_twilio_auth_token")
    TWILIO_PHONE_NUMBER: str = os.getenv("TWILIO_PHONE_NUMBER", "+1234567890")

    # Email
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
    EMAIL_SENDER: str = os.getenv("EMAIL_SENDER", "your_email@gmail.com")
    EMAIL_PASSWORD: SecretStr = os.getenv("EMAIL_PASSWORD", "your_email_password")

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str] | str:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Concurrency settings
    API_WORKERS: int = int(os.getenv("API_WORKERS", 4))
    CELERY_WORKERS: int = int(os.getenv("CELERY_WORKERS", 2))

    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()
