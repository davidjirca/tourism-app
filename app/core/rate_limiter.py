import time
import redis
from fastapi import Request, HTTPException, status
from typing import Callable, Dict, Optional, Union

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Redis client for rate limiting
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    password=settings.REDIS_PASSWORD,
    decode_responses=True,
)


class RateLimiter:
    """
    Rate limiter using Redis for storage.

    This implements a sliding window rate limit algorithm.
    """

    def __init__(
        self, times: int = 5, seconds: int = 60, key_func: Optional[Callable] = None
    ):
        """
        Initialize the rate limiter.

        Args:
            times: Maximum number of requests allowed in the time window
            seconds: Time window in seconds
            key_func: Function to extract the key from the request (defaults to client IP)
        """
        self.times = times
        self.seconds = seconds
        self.key_func = key_func or self._default_key_func

    def _default_key_func(self, request: Request) -> str:
        """
        Default function to extract key from request (uses client IP).

        Args:
            request: FastAPI request object

        Returns:
            String key for rate limiting
        """
        # Get forwarded IP if behind a proxy, otherwise use client host
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Get the first IP if multiple are chained
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host

        return f"rate_limit:{client_ip}"

    async def is_rate_limited(
        self, request: Request
    ) -> Dict[str, Union[bool, int, float]]:
        """
        Check if the request is rate limited.

        Args:
            request: FastAPI request object

        Returns:
            Dictionary with rate limit information
        """
        key = self.key_func(request)
        now = time.time()
        window_start = now - self.seconds

        # Get all requests in the current window
        try:
            # Remove old requests outside the window
            redis_client.zremrangebyscore(key, 0, window_start)

            # Count requests in the current window
            current_count = redis_client.zcard(key)

            # Add the current request
            redis_client.zadd(key, {str(now): now})

            # Set expiry on the key
            redis_client.expire(key, self.seconds)

            # Calculate remaining requests and reset time
            remaining = max(0, self.times - current_count - 1)
            reset_at = now + self.seconds

            return {
                "limited": current_count >= self.times,
                "remaining": remaining,
                "reset_at": reset_at,
                "current": current_count + 1,
            }
        except redis.RedisError as e:
            # Log the error but don't rate limit if Redis fails
            logger.error(f"Rate limiter Redis error: {e}", extra={"key": key})
            return {
                "limited": False,
                "remaining": self.times - 1,
                "reset_at": now + self.seconds,
                "current": 1,
            }

    async def __call__(self, request: Request):
        """
        Rate limit middleware function.

        Args:
            request: FastAPI request object

        Raises:
            HTTPException: If rate limit is exceeded
        """
        result = await self.is_rate_limited(request)

        # Add rate limit headers to the response
        request.state.rate_limit = result

        if result["limited"]:
            reset_in = int(result["reset_at"] - time.time())
            logger.warning(
                "Rate limit exceeded",
                extra={
                    "client_ip": request.client.host,
                    "path": request.url.path,
                    "reset_in": reset_in,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {reset_in} seconds.",
            )


def add_rate_limit_headers(request: Request, response):
    """
    Add rate limit headers to the response.

    Args:
        request: FastAPI request object
        response: Response object
    """
    if hasattr(request.state, "rate_limit"):
        rate_limit = request.state.rate_limit
        response.headers["X-RateLimit-Limit"] = str(rate_limit.get("times", 0))
        response.headers["X-RateLimit-Remaining"] = str(rate_limit.get("remaining", 0))
        response.headers["X-RateLimit-Reset"] = str(int(rate_limit.get("reset_at", 0)))


# Rate limiters for different routes
auth_limiter = RateLimiter(times=5, seconds=60)  # 5 requests per minute for auth
api_limiter = RateLimiter(
    times=60, seconds=60
)  # 60 requests per minute for general API
