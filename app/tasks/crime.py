from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.services.crime import update_destination_crime_data


@celery_app.task
def update_crime_data(destination_id: int):
    """Celery task to update crime data for a destination."""
    db = SessionLocal()
    try:
        result = update_destination_crime_data(db, destination_id)
        return result
    finally:
        db.close()