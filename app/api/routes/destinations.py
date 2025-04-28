from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from typing import List
from datetime import datetime, timedelta

from app.api.deps import get_db
from app.core.security import get_current_active_user, get_optional_current_user
from app.models.user import User
from app.models.destination import Destination
from app.models.price import PriceHistory
from app.schemas.destination import DestinationResponse, PriceHistoryResponse, PriceHistoryPoint
from app.core.exceptions import NotFoundError

router = APIRouter(prefix="/destinations", tags=["Destinations"])


def get_latest_price(db: Session, destination_id: int):
    """Get latest price history for a destination."""
    return db.query(PriceHistory).filter(
        PriceHistory.destination_id == destination_id
    ).order_by(PriceHistory.timestamp.desc()).first()


@router.get("/", response_model=List[DestinationResponse])
def get_destinations(db: Session = Depends(get_db), current_user: User = Depends(get_optional_current_user)):
    """Get all destinations with current prices."""
    # Create a subquery to get the latest price for each destination
    latest_price_subq = db.query(
        PriceHistory.destination_id,
        PriceHistory.flight_price,
        PriceHistory.hotel_price,
        func.row_number().over(
            partition_by=PriceHistory.destination_id,
            order_by=PriceHistory.timestamp.desc()
        ).label("row_num")
    ).subquery()

    latest_prices = db.query(latest_price_subq).filter(
        latest_price_subq.c.row_num == 1
    ).subquery()

    # Join destinations with their latest prices in a single query
    query = db.query(
        Destination,
        latest_prices.c.flight_price,
        latest_prices.c.hotel_price
    ).outerjoin(
        latest_prices,
        Destination.id == latest_prices.c.destination_id
    ).all()

    # Map to response model
    result = [
        DestinationResponse(
            id=dest.id,
            name=dest.name,
            airport_code=dest.airport_code,
            country=dest.country,
            description=dest.description,
            current_flight_price=flight_price,
            current_hotel_price=hotel_price
        )
        for dest, flight_price, hotel_price in query
    ]

    return result


@router.get("/{destination_id}", response_model=DestinationResponse)
def get_destination(destination_id: int, db: Session = Depends(get_db)):
    """Get a specific destination by ID."""
    # Join with latest price in a single query
    query = db.query(
        Destination,
        PriceHistory.flight_price,
        PriceHistory.hotel_price
    ).outerjoin(
        PriceHistory,
        Destination.id == PriceHistory.destination_id
    ).filter(
        Destination.id == destination_id
    ).order_by(
        PriceHistory.timestamp.desc()
    ).first()

    if not query:
        raise NotFoundError(f"Destination with ID {destination_id} not found")

    destination, flight_price, hotel_price = query

    return DestinationResponse(
        id=destination.id,
        name=destination.name,
        airport_code=destination.airport_code,
        country=destination.country,
        description=destination.description,
        current_flight_price=flight_price,
        current_hotel_price=hotel_price
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
        raise NotFoundError(f"Destination with ID {destination_id} not found")

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
        raise NotFoundError(f"Destination with ID {destination_id} not found")

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
        raise NotFoundError(f"Destination with ID {destination_id} not found")

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
    # Get favorite destination IDs
    favorite_ids = [d.id for d in current_user.destinations]

    if not favorite_ids:
        return []

    # Use optimized query with a single join
    latest_price_subq = db.query(
        PriceHistory.destination_id,
        PriceHistory.flight_price,
        PriceHistory.hotel_price,
        func.row_number().over(
            partition_by=PriceHistory.destination_id,
            order_by=PriceHistory.timestamp.desc()
        ).label("row_num")
    ).filter(
        PriceHistory.destination_id.in_(favorite_ids)
    ).subquery()

    latest_prices = db.query(latest_price_subq).filter(
        latest_price_subq.c.row_num == 1
    ).subquery()

    # Join destinations with their latest prices
    query = db.query(
        Destination,
        latest_prices.c.flight_price,
        latest_prices.c.hotel_price
    ).join(
        latest_prices,
        Destination.id == latest_prices.c.destination_id
    ).filter(
        Destination.id.in_(favorite_ids)
    ).all()

    # Map to response model
    result = [
        DestinationResponse(
            id=dest.id,
            name=dest.name,
            airport_code=dest.airport_code,
            country=dest.country,
            description=dest.description,
            current_flight_price=flight_price,
            current_hotel_price=hotel_price
        )
        for dest, flight_price, hotel_price in query
    ]

    return result