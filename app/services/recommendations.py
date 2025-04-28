import numpy as np
import redis
import json
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta

from app.core.config import settings
from app.models.destination import Destination
from app.models.user import User
from app.models.price import PriceHistory
from app.models.weather import WeatherData
from app.models.crime import CrimeData

# Redis client for caching
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True,
    password=settings.REDIS_PASSWORD
)


def _get_feature_matrix(db: Session) -> Tuple[List[int], np.ndarray]:
    """
    Create a feature matrix for all destinations with their attributes.

    Returns:
        Tuple of (destination_ids, feature_matrix)
    """
    # Fetch all destinations
    destinations = db.query(Destination).all()
    destination_ids = [d.id for d in destinations]

    # Initialize features array
    features = []

    # For each destination, get its features
    for dest in destinations:
        # Get latest weather data
        weather = db.query(WeatherData).filter(
            WeatherData.destination_id == dest.id
        ).order_by(WeatherData.timestamp.desc()).first()

        # Get latest crime data
        crime = db.query(CrimeData).filter(
            CrimeData.destination_id == dest.id
        ).order_by(CrimeData.timestamp.desc()).first()

        # Get latest price data
        price = db.query(PriceHistory).filter(
            PriceHistory.destination_id == dest.id
        ).order_by(PriceHistory.timestamp.desc()).first()

        # Create feature vector
        feature_vector = [
            dest.latitude,
            dest.longitude,
            weather.temperature if weather else 25.0,  # default temp
            weather.weather_score if weather else 7.0,  # default weather score
            crime.safety_index if crime else 50.0,  # default safety
            price.flight_price if price else 500.0,  # default flight price
            price.hotel_price if price else 400.0,  # default hotel price
        ]

        features.append(feature_vector)

    # Convert to numpy array
    feature_matrix = np.array(features)

    # Normalize features to have mean 0 and variance 1
    # This ensures that no single feature dominates the similarity calculation
    feature_matrix = (feature_matrix - np.mean(feature_matrix, axis=0)) / np.std(feature_matrix, axis=0)

    return destination_ids, feature_matrix


def compute_destination_similarity(db: Session) -> Dict[str, Any]:
    """
    Compute similarity matrix between destinations.

    Returns:
        Dictionary with destination_ids and similarity_matrix
    """
    destination_ids, feature_matrix = _get_feature_matrix(db)

    # Compute similarity matrix (cosine similarity)
    similarity_matrix = np.dot(feature_matrix, feature_matrix.T)

    # Normalize to range [0, 1]
    min_val = np.min(similarity_matrix)
    max_val = np.max(similarity_matrix)
    if max_val > min_val:  # Avoid division by zero
        similarity_matrix = (similarity_matrix - min_val) / (max_val - min_val)

    # Save to Redis cache
    cache_key = "destination_similarity"
    data = {
        "destination_ids": destination_ids,
        "similarity_matrix": similarity_matrix.tolist(),
        "updated_at": datetime.now().isoformat()
    }
    redis_client.setex(cache_key, 86400, json.dumps(data))  # Cache for 24 hours

    return data


def get_personalized_recommendations(
        db: Session, user_id: int, limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Get personalized destination recommendations for a user.

    Args:
        db: Database session
        user_id: User ID to get recommendations for
        limit: Maximum number of recommendations to return

    Returns:
        List of destination dictionaries with similarity scores
    """
    # Get user's favorite destinations
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return []

    favorite_ids = [d.id for d in user.destinations]

    # If no favorites, return top destinations by weather score
    if not favorite_ids:
        return get_top_destinations(db, limit)

    # Try to get similarity matrix from cache
    cache_key = "destination_similarity"
    cached_data = redis_client.get(cache_key)

    similarity_data = None
    if cached_data:
        try:
            similarity_data = json.loads(cached_data)
            # Check if cache is recent (< 24 hours)
            updated_at = datetime.fromisoformat(similarity_data["updated_at"])
            if updated_at < datetime.now() - timedelta(days=1):
                similarity_data = None
        except (json.JSONDecodeError, KeyError):
            similarity_data = None

    # Compute similarity if not in cache
    if not similarity_data:
        similarity_data = compute_destination_similarity(db)

    # Get destination IDs and similarity matrix
    destination_ids = similarity_data["destination_ids"]
    similarity_matrix = np.array(similarity_data["similarity_matrix"])

    # Create a map from destination ID to matrix index
    id_to_index = {dest_id: i for i, dest_id in enumerate(destination_ids)}

    # For each favorite, find similar destinations
    similar_destinations = {}
    for fav_id in favorite_ids:
        if fav_id not in id_to_index:
            continue

        fav_index = id_to_index[fav_id]

        # Get similarity scores for all destinations compared to this favorite
        scores = similarity_matrix[fav_index]

        # For each destination, update its similarity score
        for dest_id, dest_index in id_to_index.items():
            # Skip if it's already a favorite
            if dest_id in favorite_ids:
                continue

            similarity = scores[dest_index]

            # Update the maximum similarity score for this destination
            if dest_id in similar_destinations:
                similar_destinations[dest_id] = max(similar_destinations[dest_id], similarity)
            else:
                similar_destinations[dest_id] = similarity

    # Sort destinations by similarity score
    sorted_destinations = sorted(
        similar_destinations.items(),
        key=lambda x: x[1],
        reverse=True
    )[:limit]

    # Get full destination details
    recommendation_ids = [dest_id for dest_id, _ in sorted_destinations]
    recommendations = []

    if recommendation_ids:
        destinations = db.query(Destination).filter(
            Destination.id.in_(recommendation_ids)
        ).all()

        # Create a map from ID to destination object
        dest_map = {d.id: d for d in destinations}

        # Build result in order of similarity
        for dest_id, similarity in sorted_destinations:
            if dest_id in dest_map:
                dest = dest_map[dest_id]

                # Get latest price
                price = db.query(PriceHistory).filter(
                    PriceHistory.destination_id == dest.id
                ).order_by(PriceHistory.timestamp.desc()).first()

                recommendations.append({
                    "id": dest.id,
                    "name": dest.name,
                    "country": dest.country,
                    "description": dest.description,
                    "similarity_score": round(similarity * 100),  # Convert to percentage
                    "current_flight_price": price.flight_price if price else None,
                    "current_hotel_price": price.hotel_price if price else None,
                })

    return recommendations


def get_top_destinations(db: Session, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Get top destinations based on weather score and price.
    Used for users with no favorites.

    Returns:
        List of destination dictionaries
    """
    # Get recent weather data (within last week)
    one_week_ago = datetime.now() - timedelta(days=7)

    # Get destinations with good weather
    weather_subq = db.query(
        WeatherData.destination_id,
        WeatherData.weather_score
    ).filter(
        WeatherData.timestamp >= one_week_ago
    ).order_by(
        WeatherData.destination_id,
        WeatherData.timestamp.desc()
    ).distinct(
        WeatherData.destination_id
    ).subquery()

    # Get latest prices
    price_subq = db.query(
        PriceHistory.destination_id,
        PriceHistory.flight_price,
        PriceHistory.hotel_price
    ).order_by(
        PriceHistory.destination_id,
        PriceHistory.timestamp.desc()
    ).distinct(
        PriceHistory.destination_id
    ).subquery()

    # Join destination data with weather and price
    query = db.query(
        Destination,
        weather_subq.c.weather_score,
        price_subq.c.flight_price,
        price_subq.c.hotel_price
    ).join(
        weather_subq,
        Destination.id == weather_subq.c.destination_id
    ).join(
        price_subq,
        Destination.id == price_subq.c.destination_id
    ).order_by(
        weather_subq.c.weather_score.desc()
    ).limit(limit).all()

    # Format results
    results = []
    for dest, weather_score, flight_price, hotel_price in query:
        results.append({
            "id": dest.id,
            "name": dest.name,
            "country": dest.country,
            "description": dest.description,
            "weather_score": round(weather_score * 10) if weather_score else None,  # Scale to 0-100
            "current_flight_price": flight_price,
            "current_hotel_price": hotel_price,
        })

    return results