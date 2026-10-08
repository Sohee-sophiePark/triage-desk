import time
from collections import defaultdict

from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings

# In-memory sliding-window stores (Redis is the production path)
_login_counts: dict[str, list[float]] = defaultdict(list)
_api_counts: dict[str, list[float]] = defaultdict(list)


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _extract_user_id(request: Request) -> str | None:
    """Best-effort JWT decode for rate-limit keying — no DB lookup."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth[len("Bearer "):]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method

        # Skip health endpoint and CORS preflights
        if path == "/health" or method == "OPTIONS":
            return await call_next(request)

        now = time.time()

        # Login endpoint — IP-keyed, brute-force limit
        if path == "/api/v1/auth/login" and method == "POST":
            ip = _get_client_ip(request)
            window = settings.RATE_LIMIT_LOGIN_WINDOW
            max_req = settings.RATE_LIMIT_LOGIN_MAX
            _login_counts[ip] = [t for t in _login_counts[ip] if t > now - window]
            if len(_login_counts[ip]) >= max_req:
                oldest = min(_login_counts[ip])
                retry_after = max(1, int(window - (now - oldest)))
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many login attempts. Please try again later."},
                    headers={"Retry-After": str(retry_after)},
                )
            _login_counts[ip].append(now)
            return await call_next(request)

        # All other /api/ endpoints — per-user per-path sliding window
        if path.startswith("/api/"):
            user_id = _extract_user_id(request)
            if user_id is None:
                # No valid JWT — let the auth dependency handle it
                return await call_next(request)
            window = 60
            max_req = settings.RATE_LIMIT_DEFAULT_RPM
            key = f"{user_id}:{path}"
            _api_counts[key] = [t for t in _api_counts[key] if t > now - window]
            if len(_api_counts[key]) >= max_req:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Please slow down."},
                    headers={"Retry-After": "60"},
                )
            _api_counts[key].append(now)

        return await call_next(request)
