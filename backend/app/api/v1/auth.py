from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.db.database import get_db
from app.models.audit_trail import AuditTrail
from app.models.user import User
from app.schemas.user import Token, UserResponse

router = APIRouter()

@router.post("/login", response_model=Token)
async def login_access_token(
    db: AsyncSession = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> dict:
    """OAuth2 compatible token login, getting an access token for future requests."""
    query = select(User).where(User.email == form_data.username)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    # Unknown user — generic error (no user enumeration)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    now = datetime.now(timezone.utc)

    # Check if account is currently locked
    if user.locked_until is not None:
        locked_until_aware = user.locked_until.replace(tzinfo=timezone.utc)
        if locked_until_aware > now:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account temporarily locked",
            )
        # Lock has expired — reset counter
        user.failed_login_attempts = 0
        user.locked_until = None

    # Verify password
    if not verify_password(form_data.password, user.hashed_password):
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        if user.failed_login_attempts >= settings.ACCOUNT_LOCKOUT_THRESHOLD:
            user.locked_until = now + timedelta(seconds=settings.ACCOUNT_LOCKOUT_DURATION)
            db.add(AuditTrail(
                entity_type="User",
                entity_id=str(user.id),
                action="account_locked",
                changes={
                    "reason": "failed_login_threshold_reached",
                    "attempts": user.failed_login_attempts,
                    "locked_until": user.locked_until.isoformat(),
                },
                actor_id="auth_system",
            ))
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )

    # Successful login — reset counter
    user.failed_login_attempts = 0
    user.locked_until = None
    await db.commit()

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.id, role=user.role.value, expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }

@router.post("/test-token", response_model=UserResponse)
async def test_token(
    current_user: User = Depends(get_current_user)
) -> Any:
    """Test access token validity by returning the active user."""
    return current_user
