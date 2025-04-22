import requests
import redis
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
from celery import Celery
from twilio.rest import Client
from datetime import datetime, timedelta
import os

# Import database models
from database import (
    get_db, User, Destination, PriceHistory, WeatherData, CrimeData, AlertPreference,
    create_tables, initialize_destinations, SessionLocal
)

# Import authentication modules
from auth import get_current_active_user, get_optional_current_user
from auth_routes import router as auth_router
from auth_models import UserResponse, DestinationResponse, AlertPreferenceCreate, AlertPreferenceResponse

app = FastAPI(title="Travel Recommendation & Price Alert System")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include authentication routes
app.include_router(auth_router)

# API Keys (Should use environment variables in production)
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "your_openweather_api_key")
SKYSCANNER_API_KEY = os.getenv("SKYSCANNER_API_KEY", "your_skyscanner_api_key")
NUMBEO_API_KEY = os.getenv("NUMBEO_API_KEY", "your_numbeo_api_key")

# Twilio Config
TWILIO_SID = os.getenv("TWILIO_SID", "your_twilio_sid")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "your_twilio_auth_token")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "+1234567890")

# Redis Configuration (now used primarily for caching)
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
WEATHER_CACHE_EXPIRATION = 3600  # 1 hour for weather
PRICE_CACHE_EXPIRATION = 21600  # 6 hours for prices

# Email Configuration
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "your_email@gmail.com")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "your_email_password")

# Redis Client (for caching)
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

# Celery Configuration
celery_app = Celery("tasks", broker=f"redis://{REDIS_HOST}:{REDIS_PORT}/0")

# WebSockets (for push notifications)
connected_clients = []

# Twilio Client
twilio_client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)


# ===== Helper Functions =====

def get_destination_by_name(db: Session, name: str):
    return db.query(Destination).filter(Destination.name == name).first()


def get_latest_price(db: Session, destination_id: int):
    return db.query(PriceHistory).filter(
        PriceHistory.destination_id == destination_id
    ).order_by(PriceHistory.timestamp.desc()).first()


def get_latest_weather(db: Session, destination_id: int):
    return db.query(WeatherData).filter(
        WeatherData.destination_id == destination_id
    ).order_by(WeatherData.timestamp.desc()).first()


def get_latest_crime_data(db: Session, destination_id: int):
    return db.query(CrimeData).filter(
        CrimeData.destination_id == destination_id
    ).order_by(CrimeData.timestamp.desc()).first()


# ===== Celery Tasks =====

@celery_app.task
def update_weather_data(destination_id: int):
    db = SessionLocal()
    try:
        destination = db.query(Destination).filter(Destination.id == destination_id).first()
        if not destination:
            return f"Destination with ID {destination_id} not found"

        # Cache check
        cache_key = f"weather:{destination.name}"
        cached_data = redis_client.get(cache_key)
        if cached_data:
            # Return early if we have cached data
            return f"Using cached weather data for {destination.name}"

        # Fetch from OpenWeather API
        url = f"http://api.openweathermap.org/data/2.5/weather?lat={destination.latitude}&lon={destination.longitude}&appid={OPENWEATHER_API_KEY}&units=metric"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            temp = data["main"]["temp"]
            condition = data["weather"][0]["main"]

            # Weather Scoring Logic
            weather_score = 9.5 if (22 <= temp <= 30 and condition == "Clear") else \
                8.5 if (18 <= temp < 22) else \
                    7.5 if (30 < temp <= 35 or condition == "Clouds") else \
                        5.0 if condition in ["Rain", "Thunderstorm", "Snow"] else \
                            6.5

            # Save to database
            weather_data = WeatherData(
                destination_id=destination.id,
                temperature=temp,
                condition=condition,
                weather_score=weather_score
            )
            db.add(weather_data)
            db.commit()

            # Save to cache
            redis_client.setex(cache_key, WEATHER_CACHE_EXPIRATION, weather_score)

            return f"Updated weather data for {destination.name}: {weather_score}"
    finally:
        db.close()


@celery_app.task
def update_price_data(destination_id: int):
    db = SessionLocal()
    try:
        destination = db.query(Destination).filter(Destination.id == destination_id).first()
        if not destination:
            return f"Destination with ID {destination_id} not found"

        # Cache check for flight price
        cache_key = f"flight_price:{destination.name}"
        cached_price = redis_client.get(cache_key)
        if cached_price:
            # Return early if we have cached data
            return f"Using cached price data for {destination.name}"

        # Fetch from Skyscanner API
        url = f"https://partners.api.skyscanner.net/apiservices/browsequotes/v1.0/US/USD/en-US/LAX-sky/{destination.airport_code}/cheapest?apiKey={SKYSCANNER_API_KEY}"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            flight_price = data.get("Quotes", [{}])[0].get("MinPrice", 500)  # Default to $500 if no data
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
            redis_client.setex(cache_key, PRICE_CACHE_EXPIRATION, flight_price)
            redis_client.setex(f"hotel_price:{destination.name}", PRICE_CACHE_EXPIRATION, hotel_price)

            # Check for alerts
            check_price_alerts.delay(destination.id, flight_price)

            return f"Updated price data for {destination.name}: Flight=${flight_price}, Hotel=${hotel_price}"
    finally:
        db.close()


@celery_app.task
def update_crime_data(destination_id: int):
    db = SessionLocal()
    try:
        destination = db.query(Destination).filter(Destination.id == destination_id).first()
        if not destination:
            return f"Destination with ID {destination_id} not found"

        # Cache check
        cache_key = f"crime_index:{destination.name}"
        cached_data = redis_client.get(cache_key)
        if cached_data:
            # Return early if we have cached data
            return f"Using cached crime data for {destination.name}"

        # Fetch from Numbeo API
        url = f"https://www.numbeo.com/api/city_crime?api_key={NUMBEO_API_KEY}&query={destination.name}"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            crime_index = data.get("crime_index", 50)  # Default to 50 if no data
            safety_index = data.get("safety_index", 50)

            # Save to database
            crime_data = CrimeData(
                destination_id=destination.id,
                crime_index=crime_index,
                safety_index=safety_index
            )
            db.add(crime_data)
            db.commit()

            # Save to cache
            redis_client.setex(cache_key, PRICE_CACHE_EXPIRATION, crime_index)

            return f"Updated crime data for {destination.name}: Crime Index={crime_index}"
    finally:
        db.close()


@celery_app.task
def check_price_alerts(destination_id: int, current_price: float):
    db = SessionLocal()
    try:
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
    finally:
        db.close()


# ===== Notification Functions =====

def send_email_alert(user_email, destination, old_price, new_price):
    subject = f"🔥 Price Drop Alert: {destination}!"
    body = f"""
    Great news! The flight price for {destination} has dropped!

    🏷️ **Previous Price:** ${old_price}
    💰 **New Price:** ${new_price}

    Hurry, book now before prices go up! ✈️
    """

    msg = MIMEMultipart()
    msg["From"] = EMAIL_SENDER
    msg["To"] = user_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, user_email, msg.as_string())
        server.quit()
        print(f"✅ Email sent to {user_email} for {destination}")
    except Exception as e:
        print(f"❌ Error sending email: {e}")


def send_sms_alert(user_phone, destination, old_price, new_price):
    try:
        message = twilio_client.messages.create(
            body=f"🔥 Flight to {destination} just dropped from ${old_price} to ${new_price}! Book now!",
            from_=TWILIO_PHONE_NUMBER,
            to=user_phone
        )
        print(f"✅ SMS sent to {user_phone}: {message.sid}")
    except Exception as e:
        print(f"❌ Error sending SMS: {e}")


def send_push_notification(destination, old_price, new_price):
    notification_data = json.dumps({
        "type": "price_drop",
        "destination": destination,
        "old_price": old_price,
        "new_price": new_price,
        "message": f"Price drop alert! {destination} is now ${new_price}!"
    })

    for client in connected_clients:
        try:
            client.send_text(notification_data)
        except Exception as e:
            print(f"❌ Error sending WebSocket notification: {e}")


# ===== API Routes =====

@app.get("/")
async def root():
    return {"message": "Welcome to the Travel Recommendation & Price Alert System"}


# Destination Routes
@app.get("/destinations/", response_model=List[DestinationResponse])
def get_destinations(db: Session = Depends(get_db), current_user: User = Depends(get_optional_current_user)):
    destinations = db.query(Destination).all()

    # Enrich with current prices
    result = []
    for dest in destinations:
        latest_price = get_latest_price(db, dest.id)

        dest_response = DestinationResponse(
            id=dest.id,
            name=dest.name,
            airport_code=dest.airport_code,
            country=dest.country,
            description=dest.description,
            current_flight_price=latest_price.flight_price if latest_price else None,
            current_hotel_price=latest_price.hotel_price if latest_price else None
        )
        result.append(dest_response)

    return result


@app.get("/destinations/{destination_id}", response_model=DestinationResponse)
def get_destination(destination_id: int, db: Session = Depends(get_db)):
    destination = db.query(Destination).filter(Destination.id == destination_id).first()
    if not destination:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Destination not found"
        )

    latest_price = get_latest_price(db, destination.id)

    return DestinationResponse(
        id=destination.id,
        name=destination.name,
        airport_code=destination.airport_code,
        country=destination.country,
        description=destination.description,
        current_flight_price=latest_price.flight_price if latest_price else None,
        current_hotel_price=latest_price.hotel_price if latest_price else None
    )


# Price History Routes - PROTECTED
@app.get("/destinations/{destination_id}/price_history")
def get_price_history(
        destination_id: int,
        days: int = 30,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)  # Only authenticated users can access
):
    destination = db.query(Destination).filter(Destination.id == destination_id).first()
    if not destination:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Destination not found"
        )

    # Get price history for the last X days
    cutoff_date = datetime.now() - timedelta(days=days)
    history = db.query(PriceHistory).filter(
        PriceHistory.destination_id == destination_id,
        PriceHistory.timestamp >= cutoff_date
    ).order_by(PriceHistory.timestamp).all()

    return {
        "destination": destination.name,
        "data_points": len(history),
        "prices": [
            {
                "date": item.timestamp.strftime("%Y-%m-%d"),
                "flight_price": item.flight_price,
                "hotel_price": item.hotel_price
            }
            for item in history
        ]
    }


# Alert Preference Routes - PROTECTED
@app.post("/alerts/", response_model=AlertPreferenceResponse)
def create_alert(
        alert: AlertPreferenceCreate,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)  # Only authenticated users can create alerts
):
    destination = db.query(Destination).filter(Destination.id == alert.destination_id).first()
    if not destination:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Destination not found"
        )

    # Check if alert already exists for this user and destination
    existing_alert = db.query(AlertPreference).filter(
        AlertPreference.user_id == current_user.id,
        AlertPreference.destination_id == alert.destination_id
    ).first()

    if existing_alert:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Alert already exists for this destination. Use PUT to update."
        )

    # Create alert preference
    db_alert = AlertPreference(
        user_id=current_user.id,
        destination_id=alert.destination_id,
        price_threshold=alert.price_threshold,
        alert_email=alert.alert_email,
        alert_sms=alert.alert_sms,
        alert_push=alert.alert_push,
        frequency=alert.frequency
    )
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)

    # Trigger initial data update
    background_tasks.add_task(update_price_data, destination.id)

    return AlertPreferenceResponse(
        id=db_alert.id,
        destination=destination,
        price_threshold=db_alert.price_threshold,
        alert_email=db_alert.alert_email,
        alert_sms=db_alert.alert_sms,
        alert_push=db_alert.alert_push,
        frequency=db_alert.frequency
    )


@app.get("/alerts/", response_model=List[AlertPreferenceResponse])
def get_alerts(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)  # Only authenticated users can view their alerts
):
    alerts = db.query(AlertPreference).filter(AlertPreference.user_id == current_user.id).all()

    result = []
    for alert in alerts:
        destination = db.query(Destination).filter(Destination.id == alert.destination_id).first()
        alert_response = AlertPreferenceResponse(
            id=alert.id,
            destination=destination,
            price_threshold=alert.price_threshold,
            alert_email=alert.alert_email,
            alert_sms=alert.alert_sms,
            alert_push=alert.alert_push,
            frequency=alert.frequency
        )
        result.append(alert_response)

    return result


@app.put("/alerts/{alert_id}", response_model=AlertPreferenceResponse)
def update_alert(
        alert_id: int,
        alert_data: AlertPreferenceCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    # Find the alert
    db_alert = db.query(AlertPreference).filter(
        AlertPreference.id == alert_id,
        AlertPreference.user_id == current_user.id
    ).first()

    if not db_alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found or does not belong to current user"
        )

    # Update alert fields
    db_alert.price_threshold = alert_data.price_threshold
    db_alert.alert_email = alert_data.alert_email
    db_alert.alert_sms = alert_data.alert_sms
    db_alert.alert_push = alert_data.alert_push
    db_alert.frequency = alert_data.frequency

    db.commit()
    db.refresh(db_alert)

    destination = db.query(Destination).filter(Destination.id == db_alert.destination_id).first()

    return AlertPreferenceResponse(
        id=db_alert.id,
        destination=destination,
        price_threshold=db_alert.price_threshold,
        alert_email=db_alert.alert_email,
        alert_sms=db_alert.alert_sms,
        alert_push=db_alert.alert_push,
        frequency=db_alert.frequency
    )


@app.delete("/alerts/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alert(
        alert_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    # Find the alert
    db_alert = db.query(AlertPreference).filter(
        AlertPreference.id == alert_id,
        AlertPreference.user_id == current_user.id
    ).first()

    if not db_alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found or does not belong to current user"
        )

    # Delete the alert
    db.delete(db_alert)
    db.commit()

    return None


# Data Update Routes - ADMIN ONLY
@app.post("/admin/refresh_data")
async def refresh_data(
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    # Check if user is admin
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to perform this action"
        )

    destinations = db.query(Destination).all()

    for destination in destinations:
        background_tasks.add_task(update_weather_data, destination.id)
        background_tasks.add_task(update_price_data, destination.id)
        background_tasks.add_task(update_crime_data, destination.id)

    return {
        "message": f"Data refresh tasks scheduled for {len(destinations)} destinations"
    }


# User's favorite destinations
@app.post("/destinations/{destination_id}/favorite", status_code=status.HTTP_200_OK)
def add_favorite_destination(
        destination_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    destination = db.query(Destination).filter(Destination.id == destination_id).first()
    if not destination:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Destination not found"
        )

    # Check if already favorited
    if destination in current_user.destinations:
        return {"message": "Destination already in favorites"}

    # Add to favorites
    current_user.destinations.append(destination)
    db.commit()

    return {"message": f"Added {destination.name} to favorites"}


@app.delete("/destinations/{destination_id}/favorite", status_code=status.HTTP_200_OK)
def remove_favorite_destination(
        destination_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    destination = db.query(Destination).filter(Destination.id == destination_id).first()
    if not destination:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Destination not found"
        )

    # Check if in favorites
    if destination not in current_user.destinations:
        return {"message": "Destination not in favorites"}

    # Remove from favorites
    current_user.destinations.remove(destination)
    db.commit()

    return {"message": f"Removed {destination.name} from favorites"}


@app.get("/favorites", response_model=List[DestinationResponse])
def get_favorite_destinations(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    favorites = []

    for destination in current_user.destinations:
        latest_price = get_latest_price(db, destination.id)

        dest_response = DestinationResponse(
            id=destination.id,
            name=destination.name,
            airport_code=destination.airport_code,
            country=destination.country,
            description=destination.description,
            current_flight_price=latest_price.flight_price if latest_price else None,
            current_hotel_price=latest_price.hotel_price if latest_price else None
        )
        favorites.append(dest_response)

    return favorites


# WebSocket Route for Push Notifications
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        connected_clients.remove(websocket)


# Celery periodic tasks
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Run once at startup to ensure all tables exist
    create_tables()
    initialize_destinations()

    db = SessionLocal()
    destinations = db.query(Destination).all()
    db.close()

    # Set up periodic tasks for each destination
    for destination in destinations:
        # Update weather data every hour
        sender.add_periodic_task(
            3600,
            update_weather_data.s(destination.id),
            name=f'update_weather_for_{destination.name}'
        )

        # Update flight prices every 6 hours
        sender.add_periodic_task(
            21600,
            update_price_data.s(destination.id),
            name=f'update_prices_for_{destination.name}'
        )

        # Update crime data daily
        sender.add_periodic_task(
            86400,
            update_crime_data.s(destination.id),
            name=f'update_crime_for_{destination.name}'
        )


if __name__ == "__main__":
    import uvicorn

    # Create DB tables
    create_tables()
    # Initialize data
    initialize_destinations()
    # Run app
    uvicorn.run(app, host="0.0.0.0", port=8000)