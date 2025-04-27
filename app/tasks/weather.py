from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.services.weather import update_destination_weather


@celery_app.task
def update_weather_data(destination_id: int):
    """Celery task to update weather data for a destination."""
    db = SessionLocal()
    try:
        result = update_destination_weather(db, destination_id)
        return result
    finally:
        db.close()