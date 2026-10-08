import time
from collections import defaultdict

from fastapi import Depends, HTTPException

from app.api.deps import get_current_user
from app.models.user import User

# Simple In-Memory Rate Limiter (For Dev/UAT)
# In production, use Redis for distributed throttling.
_request_counts = defaultdict(list)

def rate_limit_evaluations(max_requests: int = 5, window_seconds: int = 60):
    """Dependency to throttle AI evaluations per authenticated user (not by IP)."""
    async def limiter(current_user: User = Depends(get_current_user)):
        # Key on user ID — not on client IP, which is spoofable behind a reverse proxy.
        key = str(current_user.id)
        now = time.time()

        # Clean up old requests outside the window
        _request_counts[key] = [t for t in _request_counts[key] if t > now - window_seconds]

        if len(_request_counts[key]) >= max_requests:
            raise HTTPException(
                status_code=429,
                detail="Too many AI evaluation requests. Please wait a minute before trying again."
            )

        _request_counts[key].append(now)
    return limiter
