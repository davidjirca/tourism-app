from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import redis
from typing import Dict, Any

from app.api.deps import get_db
from app.core.config import settings

router = APIRouter(prefix="/health", tags=["Health Checks"])


@router.get("/")
async def health_check() -> Dict[str, str]:
    """
    Simple health check to verify the API service is running.
    """
    return {"status": "ok", "service": settings.PROJECT_NAME}


@router.get("/readiness")
async def readiness_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Check if the application is ready to accept traffic.

    This checks database connectivity and Redis connectivity.
    """
    # Check database connection
    db_status = "ok"
    try:
        db.execute("SELECT 1")
    except Exception as e:
        db_status = f"error: {str(e)}"

    # Check Redis connection
    redis_status = "ok"
    try:
        # Create a Redis client
        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            socket_timeout=2  # Short timeout for health check
        )
        # Check connection
        redis_client.ping()
    except Exception as e:
        redis_status = f"error: {str(e)}"

    # Overall status
    all_healthy = all(s == "ok" for s in [db_status, redis_status])

    return {
        "status": "ok" if all_healthy else "degraded",
        "database": db_status,
        "redis": redis_status,
        "version": settings.VERSION
    }


@router.get("/version")
async def version_info() -> Dict[str, str]:
    """
    Get application version information.
    """
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION
    }