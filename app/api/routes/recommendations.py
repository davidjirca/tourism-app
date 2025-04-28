from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.api.deps import get_db
from app.core.security import get_current_active_user, get_optional_current_user
from app.models.user import User
from app.services.recommendations import get_personalized_recommendations, get_top_destinations

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.get("/", response_model=List[Dict[str, Any]])
def get_recommendations(
        limit: int = Query(5, ge=1, le=20, description="Maximum number of recommendations to return"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """
    Get personalized destination recommendations for the current user.

    If the user has favorite destinations, recommendations are based on destinations
    similar to their favorites. Otherwise, top destinations by weather and price
    are returned.
    """
    return get_personalized_recommendations(db, current_user.id, limit)


@router.get("/discover", response_model=List[Dict[str, Any]])
def discover_destinations(
        limit: int = Query(5, ge=1, le=20, description="Maximum number of destinations to return"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_optional_current_user)
):
    """
    Discover top destinations based on current weather and prices.

    This endpoint is accessible to both authenticated and unauthenticated users.
    If the user is authenticated, a personalized experience may be provided.
    """
    if current_user:
        # For authenticated users, check if they have favorites
        if current_user.destinations:
            # If they have favorites, give personalized recommendations
            return get_personalized_recommendations(db, current_user.id, limit)

    # For unauthenticated users or those without favorites
    return get_top_destinations(db, limit)