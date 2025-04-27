from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta

from app.api.deps import get_db
from app.core.security import get_current_active_user, get_optional_current_user
from app.models.user import User
from app.models.destination import Destination
from app.models.price import PriceHistory
from app.schemas.destination import DestinationResponse, PriceHistoryResponse, PriceHistoryPoint

router = APIRouter(prefix="/destinations", tags=["Destinations"])


def get_latest_price(db: Session, destination_id: int):
    """Get latest price history for a destination."""
    return db.query(PriceHistory).filter(
        PriceHistory.destination_id == destination_id
    ).order_by(PriceHistory.timestamp.desc()).first()


@router.get("/", response_model=List[DestinationResponse])
def get_destinations(db: Session = Depends(get_db), current_user: User = Depends(get_optional_current_user)):
    """Get all destinations with current prices."""
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


@router.get("/{destination_id}", response_model=DestinationResponse)
def get_destination(destination_id: int, db: Session = Depends(get_db)):
    """Get a specific destination by ID."""
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


@router.get("/{destination_id}/price_history", response_model=PriceHistoryResponse)
def get_price_history(
        destination_id: int,
        days: int = 30,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)  # Only authenticated users can access
):
    """Get price history for a destination for the specified number of days."""
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

    # Convert to response model
    history_points = [
        PriceHistoryPoint(
            date=item.timestamp.strftime("%Y-%m-%d"),
            flight_price=item.flight_price,
            hotel_price=item.hotel_price
        )
        for item in history
    ]

    return PriceHistoryResponse(
        destination=destination.name,
        data_points=len(history),
        prices=history_points
    )


@router.post("/{destination_id}/favorite", status_code=status.HTTP_200_OK)
def add_favorite_destination(
        destination_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Add a destination to user's favorites."""
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


@router.delete("/{destination_id}/favorite", status_code=status.HTTP_200_OK)
def remove_favorite_destination(
        destination_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Remove a destination from user's favorites."""
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


@router.get("/favorites", response_model=List[DestinationResponse])
def get_favorite_destinations(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Get all destinations favorited by the current user."""
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