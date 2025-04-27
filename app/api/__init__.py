from fastapi import APIRouter
from app.api.routes import auth, destinations, alerts

# Create API router
api_router = APIRouter()

# Include all route modules
api_router.include_router(auth.router)
api_router.include_router(destinations.router)
api_router.include_router(alerts.router)