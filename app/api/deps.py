from typing import Generator
from sqlalchemy.orm import Session
from app.db.session import SessionLocal

# Database dependency
def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()