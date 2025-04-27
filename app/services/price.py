import requests
import redis
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.destination import Destination
from app.models.price import PriceHistory
from app.models.alert import AlertPreference
from app.models.user import User
from app.services.notification import send_email_alert, send_sms_alert, send_push_notification

# Redis client for caching
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=0,
    decode_responses=True
)


def fetch_flight_price(destination: Destination) -> float:
    """Fetch flight price data from Skyscanner API."""
    url = f"https://partners.api.skyscanner.net/apiservices/browsequotes/v1.0/US/USD/en-US/LAX-sky/{destination.airport_code}/cheapest?apiKey={settings.SKYSCANNER_API_KEY}"

    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise exception for HTTP errors

        data = response.json()
        flight_price = data.get("Quotes", [{}])[0].get("MinPrice", 500)  # Default to $500 if no data
        return flight_price
    except requests.RequestException as e:
        print(f"Error fetching flight price data: {e}")
        return 500  # Default price


def update_destination_price(db: Session, destination_id: int) -> dict:
    """Update price data for a destination."""
    destination = db.query(Destination).filter(Destination.id == destination_id).first()
    if not destination:
        return {"success": False, "message": f"Destination with ID {destination_id} not found"}

    # Cache check for flight price
    cache_key = f"flight_price:{destination.name}"
    cached_price = redis_client.get(cache_key)
    if cached_price:
        # Return early if we have cached data
        flight_price = float(cached_price)
        hotel_price = float(redis_client.get(f"hotel_price:{destination.name}") or flight_price * 0.8)

        return {
            "success": True,
            "message": f"Using cached price data for {destination.name}",
            "cached": True,
            "flight_price": flight_price,
            "hotel_price": hotel_price
        }

    # Fetch price data
    flight_price = fetch_flight_price(destination)
    hotel_price = flight_price * 0.8  # Mock hotel price (80% of flight cost)

    # Save to database
    price_history = PriceHistory(
        destination_id=destination.id,
        flight_price=flight_price,
        hotel_price=hotel_price
    )
    db.add(price_history)
    db.commit()

    # Save to cache
    redis_client.setex(cache_key, settings.PRICE_CACHE_EXPIRATION, flight_price)
    redis_client.setex(f"hotel_price:{destination.name}", settings.PRICE_CACHE_EXPIRATION, hotel_price)

    # Check for alerts
    check_price_alerts(db, destination.id, flight_price)

    return {
        "success": True,
        "message": f"Updated price data for {destination.name}",
        "cached": False,
        "flight_price": flight_price,
        "hotel_price": hotel_price
    }


def check_price_alerts(db: Session, destination_id: int, current_price: float):
    """Check if any alerts should be triggered based on the new price."""
    # Get all alert preferences for this destination
    alerts = db.query(AlertPreference).filter(
        AlertPreference.destination_id == destination_id
    ).all()

    for alert in alerts:
        # Skip if no threshold set or price above threshold
        if not alert.price_threshold or current_price > alert.price_threshold:
            continue

        # Get user and destination info
        user = db.query(User).filter(User.id == alert.user_id).first()
        destination = db.query(Destination).filter(Destination.id == destination_id).first()

        # Get previous price for comparison
        prev_prices = db.query(PriceHistory).filter(
            PriceHistory.destination_id == destination_id
        ).order_by(PriceHistory.timestamp.desc()).limit(2).all()

        # If we have at least 2 price points and the price dropped
        if len(prev_prices) >= 2 and prev_prices[1].flight_price > current_price:
            old_price = prev_prices[1].flight_price

            # Send alerts based on user preferences
            if alert.alert_email:
                send_email_alert(user.email, destination.name, old_price, current_price)

            if alert.alert_sms and user.phone:
                send_sms_alert(user.phone, destination.name, old_price, current_price)

            if alert.alert_push:
                send_push_notification(destination.name, old_price, current_price)