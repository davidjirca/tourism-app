from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.services.price import update_destination_price


@celery_app.task
def update_price_data(destination_id: int):
    """Celery task to update price data for a destination."""
    db = SessionLocal()
    try:
        result = update_destination_price(db, destination_id)
        return result
    finally:
        db.close()