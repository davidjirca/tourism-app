from typing import List
from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.services.price import (
    update_destination_price,
    batch_update_prices,
    check_price_alerts,
)


@celery_app.task
def update_price_data(destination_id: int):
    """Celery task to update price data for a destination."""
    db = SessionLocal()
    try:
        result = update_destination_price(db, destination_id)
        return result
    finally:
        db.close()


@celery_app.task
def batch_update_prices_task(destination_ids: List[int]):
    """Celery task to update prices for multiple destinations in a single task."""
    db = SessionLocal()
    try:
        results = batch_update_prices(db, destination_ids)
        return results
    finally:
        db.close()


@celery_app.task
def check_price_alerts_task(destination_id: int, current_price: float):
    """Celery task to check price alerts for a destination."""
    db = SessionLocal()
    try:
        check_price_alerts(db, destination_id, current_price)
        return f"Price alerts checked for destination {destination_id}"
    finally:
        db.close()
