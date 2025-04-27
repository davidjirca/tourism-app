from fastapi import FastAPI, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.api import api_router
from app.core.config import settings
from app.db.session import get_db
from app.db.init_db import init_db
from app.core.celery_app import celery_app
from app.websockets.notifications import handle_websocket_connection
from app.models.destination import Destination

# Create FastAPI app
app = FastAPI(title=settings.PROJECT_NAME)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


# Root endpoint
@app.get("/")
async def root():
    return {"message": f"Welcome to the {settings.PROJECT_NAME}"}


# WebSocket endpoint for push notifications
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await handle_websocket_connection(websocket)


# Admin endpoint to refresh all data
@app.post("/admin/refresh_data")
async def refresh_data(db: Session = Depends(get_db)):
    """Trigger a data refresh for all destinations. Admin only in production."""
    destinations = db.query(Destination).all()

    # Schedule tasks for each destination
    for destination in destinations:
        from app.tasks.weather import update_weather_data
        from app.tasks.price import update_price_data
        from app.tasks.crime import update_crime_data

        update_weather_data.delay(destination.id)
        update_price_data.delay(destination.id)
        update_crime_data.delay(destination.id)

    return {
        "message": f"Data refresh tasks scheduled for {len(destinations)} destinations"
    }


# Setup Celery periodic tasks
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Set up periodic tasks for Celery."""
    db = next(get_db())
    destinations = db.query(Destination).all()

    # Set up periodic tasks for each destination
    for destination in destinations:
        # Update weather data every hour
        sender.add_periodic_task(
            3600,
            "app.tasks.weather.update_weather_data",
            args=(destination.id,),
            name=f'update_weather_for_{destination.name}'
        )

        # Update flight prices every 6 hours
        sender.add_periodic_task(
            21600,
            "app.tasks.price.update_price_data",
            args=(destination.id,),
            name=f'update_prices_for_{destination.name}'
        )

        # Update crime data daily
        sender.add_periodic_task(
            86400,
            "app.tasks.crime.update_crime_data",
            args=(destination.id,),
            name=f'update_crime_for_{destination.name}'
        )


# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database on application startup."""
    db = next(get_db())
    init_db(db)