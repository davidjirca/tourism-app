from fastapi import FastAPI, WebSocket, Depends, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import uuid
import time
from typing import List

from app.api import api_router
from app.core.config import settings
from app.db.session import get_db
from app.db.init_db import init_db
from app.core.celery_app import celery_app
from app.core.logging import setup_logging
from app.core.rate_limiter import add_rate_limit_headers
from app.websockets.notifications import handle_websocket_connection
from app.models.destination import Destination

# Setup structured logging
logger = setup_logging("app", "INFO")

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="""
    Travel Recommendation & Price Alert System API.

    ## Features

    * 🌍 Browse destinations with real-time pricing
    * 💰 Set price alerts for your favorite destinations
    * 🔔 Receive notifications via email, SMS, or push
    * ❤️ Save your favorite destinations for quick access
    * 🧠 Get personalized destination recommendations

    ## Authentication

    This API uses JWT Bearer tokens for authentication.
    Register and login to obtain your token.
    """,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    logger.info(
        "Request started",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "client_ip": request.client.host,
        },
    )

    # Add request_id to request state for use in route handlers
    request.state.request_id = request_id

    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    # Add rate limit headers if present
    add_rate_limit_headers(request, response)

    # Add request ID header
    response.headers["X-Request-ID"] = request_id

    # Add security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
    )

    logger.info(
        "Request completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(process_time * 1000),
            "content_length": response.headers.get("content-length", 0),
        },
    )

    return response


# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


# Root endpoint
@app.get("/")
async def root():
    return {"message": f"Welcome to the {settings.PROJECT_NAME}"}


# Health check endpoints
@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/health/readiness")
async def readiness_check(db: Session = Depends(get_db)):
    # Check database connection
    try:
        db.execute("SELECT 1")
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)}"

    all_healthy = db_status == "ok"

    return {"status": "ok" if all_healthy else "degraded", "database": db_status}


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

    # Get all destination IDs
    destination_ids = [d.id for d in destinations]
    chunk_size = 5  # Process 5 destinations per task

    # Create batched tasks for better efficiency
    from app.tasks.price import batch_update_prices

    for i in range(0, len(destination_ids), chunk_size):
        chunk = destination_ids[i : i + chunk_size]
        sender.add_periodic_task(
            21600,  # 6 hours
            batch_update_prices.s(chunk),
            name=f"batch_update_prices_{i // chunk_size}",
        )

    # Still update weather data per destination as it might need more frequent updates
    for destination in destinations:
        # Update weather data every hour
        sender.add_periodic_task(
            3600,
            "app.tasks.weather.update_weather_data",
            args=(destination.id,),
            name=f"update_weather_for_{destination.name}",
        )

        # Update crime data daily
        sender.add_periodic_task(
            86400,
            "app.tasks.crime.update_crime_data",
            args=(destination.id,),
            name=f"update_crime_for_{destination.name}",
        )


# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database on application startup."""
    db = next(get_db())
    init_db(db)
