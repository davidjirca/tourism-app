# Import all models here for easy access and to ensure they're loaded before Base.metadata.create_all()

from app.models.user import User
from app.models.destination import Destination, user_destinations
from app.models.price import PriceHistory
from app.models.weather import WeatherData
from app.models.crime import CrimeData
from app.models.alert import AlertPreference