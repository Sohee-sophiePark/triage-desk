"""
Account lockout tests (SC-01 / A07).

Covers:
- 10 failed attempts lock the account
- 11th attempt returns 403 "Account temporarily locked"
- Successful login resets the counter
- Locked account writes an audit trail entry

Note: The login rate limiter (RATE_LIMIT_LOGIN_MAX=5) fires before we can reach
the lockout threshold of 10. These tests reset _login_counts between individual
attempts so that only the account lockout logic is under test here, not rate
limiting. Rate limiting is tested separately in test_rate_limiting.py.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.future import select

from app.core.security import get_password_hash
from app.middleware.rate_limiter import _login_counts
from app.models.user import Role, User
from tests.conftest import TEST_PASSWORD as LOCKOUT_PASSWORD
from tests.conftest import WRONG_PASSWORD


@pytest.fixture
async def lockout_user(db):
    """A fresh user created specifically for lockout tests."""
    user = User(
        id=uuid.uuid4(),
        email=f"lockout-{uuid.uuid4().hex[:8]}@test.com",
        hashed_password=get_password_hash(LOCKOUT_PASSWORD),
        role=Role.RISK_ANALYST,
        is_active=True,
        full_name="Lockout Test User",
        failed_login_attempts=0,
        locked_until=None,
    )
    db.add(user)
    await db.commit()
    return user


async def _login(client, email: str, password: str):
    # Reset IP-based login rate limit before each attempt so the lockout
    # threshold (10) is reachable without hitting the rate limit (5/window).
    _login_counts.clear()
    return await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )


# ── Lockout after threshold ───────────────────────────────────────────────────

async def test_account_locked_after_threshold(client, db, lockout_user):
    """10 failed attempts → account locked; 11th returns 403."""
    from app.core.config import settings

    # 9 failed attempts — all should return 400 (wrong password)
    for _ in range(settings.ACCOUNT_LOCKOUT_THRESHOLD - 1):
        r = await _login(client, lockout_user.email, WRONG_PASSWORD)
        assert r.status_code == 400, f"Expected 400, got {r.status_code}"

    # 10th attempt — triggers lockout, still returns 400 (wrong password)
    r = await _login(client, lockout_user.email, WRONG_PASSWORD)
    assert r.status_code == 400

    # Refresh the user from DB to check lockout state
    await db.refresh(lockout_user)
    assert lockout_user.locked_until is not None

    # 11th attempt — account is now locked → 403
    r = await _login(client, lockout_user.email, WRONG_PASSWORD)
    assert r.status_code == 403
    assert "locked" in r.json()["detail"].lower()


async def test_correct_password_also_blocked_when_locked(client, db, lockout_user):
    """Once locked, even the correct password is rejected with 403."""
    from app.core.config import settings

    for _ in range(settings.ACCOUNT_LOCKOUT_THRESHOLD):
        await _login(client, lockout_user.email, WRONG_PASSWORD)

    await db.refresh(lockout_user)
    assert lockout_user.locked_until is not None

    r = await _login(client, lockout_user.email, LOCKOUT_PASSWORD)
    assert r.status_code == 403


# ── Counter reset on success ──────────────────────────────────────────────────

async def test_successful_login_resets_counter(client, db, lockout_user):
    """A successful login clears failed_login_attempts and locked_until."""
    # Simulate some prior failures (below threshold)
    lockout_user.failed_login_attempts = 3
    await db.commit()

    r = await _login(client, lockout_user.email, LOCKOUT_PASSWORD)
    assert r.status_code == 200

    await db.refresh(lockout_user)
    assert lockout_user.failed_login_attempts == 0
    assert lockout_user.locked_until is None


# ── Lock expiry ───────────────────────────────────────────────────────────────

async def test_expired_lock_allows_login(client, db, lockout_user):
    """When locked_until is in the past, login proceeds normally."""
    lockout_user.failed_login_attempts = 10
    lockout_user.locked_until = datetime.now(timezone.utc) - timedelta(seconds=1)
    await db.commit()

    r = await _login(client, lockout_user.email, LOCKOUT_PASSWORD)
    assert r.status_code == 200

    await db.refresh(lockout_user)
    assert lockout_user.failed_login_attempts == 0
    assert lockout_user.locked_until is None


# ── Audit trail ───────────────────────────────────────────────────────────────

async def test_lockout_writes_audit_trail(client, db, lockout_user):
    """Reaching the threshold should produce an account_locked audit entry."""
    from app.core.config import settings
    from app.models.audit_trail import AuditTrail

    for _ in range(settings.ACCOUNT_LOCKOUT_THRESHOLD):
        await _login(client, lockout_user.email, WRONG_PASSWORD)

    result = await db.execute(
        select(AuditTrail).where(
            AuditTrail.entity_type == "User",
            AuditTrail.entity_id == str(lockout_user.id),
            AuditTrail.action == "account_locked",
        )
    )
    audit_entry = result.scalar_one_or_none()
    assert audit_entry is not None
    assert audit_entry.changes.get("reason") == "failed_login_threshold_reached"
