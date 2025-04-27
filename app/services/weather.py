import requests
import redis
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.destination import Destination
from app.models.weather import WeatherData

# Redis client for caching
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=0,
    decode_responses=True
)


def fetch_weather_data(destination: Destination):
    """Fetch weather data from OpenWeather API."""
    url = f"http://api.openweathermap.org/data/2.5/weather?lat={destination.latitude}&lon={destination.longitude}&appid={settings.OPENWEATHER_API_KEY}&units=metric"

    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise exception for HTTP errors

        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching weather data: {e}")
        return None


def calculate_weather_score(temperature: float, condition: str) -> float:
    """Calculate a weather score based on temperature and condition."""
    # Weather Scoring Logic
    if 22 <= temperature <= 30 and condition == "Clear":
        return 9.5
    elif 18 <= temperature < 22:
        return 8.5
    elif 30 < temperature <= 35 or condition == "Clouds":
        return 7.5
    elif condition in ["Rain", "Thunderstorm", "Snow"]:
        return 5.0
    else:
        return 6.5


def update_destination_weather(db: Session, destination_id: int) -> dict:
    """Update weather data for a destination."""
    destination = db.query(Destination).filter(Destination.id == destination_id).first()
    if not destination:
        return {"success": False, "message": f"Destination with ID {destination_id} not found"}

    # Cache check
    cache_key = f"weather:{destination.name}"
    cached_data = redis_client.get(cache_key)
    if cached_data:
        # Return early if we have cached data
        return {
            "success": True,
            "message": f"Using cached weather data for {destination.name}",
            "cached": True,
            "weather_score": float(cached_data)
        }

    # Fetch from OpenWeather API
    weather_data = fetch_weather_data(destination)
    if not weather_data:
        return {"success": False, "message": f"Failed to fetch weather data for {destination.name}"}

    temp = weather_data["main"]["temp"]
    condition = weather_data["weather"][0]["main"]

    # Calculate weather score
    weather_score = calculate_weather_score(temp, condition)

    # Save to database
    db_weather_data = WeatherData(
        destination_id=destination.id,
        temperature=temp,
        condition=condition,
        weather_score=weather_score
    )
    db.add(db_weather_data)
    db.commit()

    # Save to cache
    redis_client.setex(cache_key, settings.WEATHER_CACHE_EXPIRATION, weather_score)

    return {
        "success": True,
        "message": f"Updated weather data for {destination.name}",
        "cached": False,
        "temperature": temp,
        "condition": condition,
        "weather_score": weather_score
    }