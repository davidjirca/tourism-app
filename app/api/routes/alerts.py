from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

from app.api.deps import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.destination import Destination
from app.models.alert import AlertPreference
from app.schemas.alert import AlertPreferenceCreate, AlertPreferenceResponse, AlertPreferenceUpdate
from app.tasks.price import update_price_data

router = APIRouter(prefix="/alerts", tags=["Price Alerts"])


@router.post("/", response_model=AlertPreferenceResponse)
def create_alert(
        alert: AlertPreferenceCreate,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Create a new price alert for a destination."""
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

    # Create response
    response = AlertPreferenceResponse(
        id=db_alert.id,
        destination=destination,
        price_threshold=db_alert.price_threshold,
        alert_email=db_alert.alert_email,
        alert_sms=db_alert.alert_sms,
        alert_push=db_alert.alert_push,
        frequency=db_alert.frequency
    )

    return response


@router.get("/", response_model=List[AlertPreferenceResponse])
def get_alerts(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Get all alerts for the current user."""
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


@router.put("/{alert_id}", response_model=AlertPreferenceResponse)
def update_alert(
        alert_id: int,
        alert_data: AlertPreferenceUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Update an existing alert."""
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


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alert(
        alert_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """Delete an alert."""
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