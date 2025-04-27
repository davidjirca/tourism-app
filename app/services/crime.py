import requests
import redis
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.destination import Destination
from app.models.crime import CrimeData

# Redis client for caching
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=0,
    decode_responses=True
)


def fetch_crime_data(destination: Destination):
    """Fetch crime data from Numbeo API."""
    url = f"https://www.numbeo.com/api/city_crime?api_key={settings.NUMBEO_API_KEY}&query={destination.name}"

    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise exception for HTTP errors

        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching crime data: {e}")
        return None


def update_destination_crime_data(db: Session, destination_id: int) -> dict:
    """Update crime data for a destination."""
    destination = db.query(Destination).filter(Destination.id == destination_id).first()
    if not destination:
        return {"success": False, "message": f"Destination with ID {destination_id} not found"}

    # Cache check
    cache_key = f"crime_index:{destination.name}"
    cached_data = redis_client.get(cache_key)
    if cached_data:
        # Return early if we have cached data
        return {
            "success": True,
            "message": f"Using cached crime data for {destination.name}",
            "cached": True,
            "crime_index": float(cached_data)
        }

    # Fetch from Numbeo API
    crime_data = fetch_crime_data(destination)
    if not crime_data:
        # If API fails, use default values
        crime_index = 50
        safety_index = 50
    else:
        crime_index = crime_data.get("crime_index", 50)
        safety_index = crime_data.get("safety_index", 50)

    # Save to database
    db_crime_data = CrimeData(
        destination_id=destination.id,
        crime_index=crime_index,
        safety_index=safety_index
    )
    db.add(db_crime_data)
    db.commit()

    # Save to cache
    redis_client.setex(cache_key, settings.PRICE_CACHE_EXPIRATION, crime_index)

    return {
        "success": True,
        "message": f"Updated crime data for {destination.name}",
        "cached": False,
        "crime_index": crime_index,
        "safety_index": safety_index
    }