"""
Tests for global rate limiting middleware (SC-06).
Covers: login brute-force protection and per-user API rate limits.
"""
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import app
from app.middleware.rate_limiter import _api_counts, _login_counts
from tests.conftest import WRONG_PASSWORD


@pytest.fixture(autouse=True)
def _clear_stores():
    _login_counts.clear()
    _api_counts.clear()
    yield
    _login_counts.clear()
    _api_counts.clear()


@pytest.fixture
async def anon_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ── Login brute-force protection ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_rate_limit_blocks_on_threshold(anon_client):
    """6th login attempt from the same IP must return 429."""
    max_attempts = settings.RATE_LIMIT_LOGIN_MAX
    payload = {"username": "nobody@test.com", "password": WRONG_PASSWORD}

    for _ in range(max_attempts):
        r = await anon_client.post("/api/v1/auth/login", data=payload)
        assert r.status_code != 429

    r = await anon_client.post("/api/v1/auth/login", data=payload)
    assert r.status_code == 429
    assert "Retry-After" in r.headers


@pytest.mark.asyncio
async def test_login_rate_limit_includes_retry_after(anon_client):
    max_attempts = settings.RATE_LIMIT_LOGIN_MAX
    payload = {"username": "nobody@test.com", "password": WRONG_PASSWORD}

    for _ in range(max_attempts + 1):
        r = await anon_client.post("/api/v1/auth/login", data=payload)

    assert r.status_code == 429
    retry_after = int(r.headers["Retry-After"])
    assert retry_after > 0
    assert retry_after <= settings.RATE_LIMIT_LOGIN_WINDOW


@pytest.mark.asyncio
async def test_health_endpoint_not_rate_limited(anon_client):
    """Health endpoint must always respond regardless of rate limits."""
    for _ in range(200):
        r = await anon_client.get("/health")
        assert r.status_code == 200


# ── Per-user API rate limit ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_api_rate_limit_blocks_after_rpm(analyst_headers):
    """User exceeding RATE_LIMIT_DEFAULT_RPM on a single endpoint gets 429."""
    rpm = settings.RATE_LIMIT_DEFAULT_RPM

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        for _ in range(rpm):
            r = await ac.get("/api/v1/customers", headers=analyst_headers)
            assert r.status_code != 429

        r = await ac.get("/api/v1/customers", headers=analyst_headers)
        assert r.status_code == 429
        assert "Retry-After" in r.headers
        assert r.headers["Retry-After"] == "60"


@pytest.mark.asyncio
async def test_api_rate_limit_is_per_user(admin_headers, analyst_headers):
    """Exhausting one user's limit must not affect a different user."""
    rpm = settings.RATE_LIMIT_DEFAULT_RPM

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Exhaust analyst's limit
        for _ in range(rpm + 1):
            await ac.get("/api/v1/customers", headers=analyst_headers)

        # Admin should still be fine
        r = await ac.get("/api/v1/customers", headers=admin_headers)
        assert r.status_code != 429


@pytest.mark.asyncio
async def test_unauthenticated_request_not_rate_limited_by_middleware(anon_client):
    """Unauthenticated requests fall through to auth dependency (not blocked by middleware)."""
    # With no bearer token the middleware skips rate-limiting and auth dep returns 401
    r = await anon_client.get("/api/v1/customers")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_options_preflight_not_rate_limited(anon_client):
    """CORS preflight OPTIONS requests must not be counted or blocked."""
    for _ in range(200):
        r = await anon_client.options(
            "/api/v1/customers",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        # CORS middleware may return 400 for missing headers but never 429
        assert r.status_code != 429
