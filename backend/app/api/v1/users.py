"""
Admin-only user management endpoints.
GET  /users          — list all users
POST /users          — create a user (409 on duplicate email)
PATCH /users/{id}    — update role / name / active / password

No DELETE: deactivate via is_active=false to preserve audit integrity.
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_db, require_role
from app.core.security import get_password_hash
from app.models.audit_trail import AuditTrail
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, UserUpdate

router = APIRouter()


def _admin_only():
    return require_role(["admin"])


@router.get("", response_model=list[UserResponse])
async def list_users(
    current_user: User = Depends(_admin_only()),
    db: AsyncSession = Depends(get_db),
) -> list[UserResponse]:
    result = await db.execute(select(User).order_by(User.email))
    return result.scalars().all()


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate,
    current_user: User = Depends(_admin_only()),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered.")

    new_user = User(
        id=uuid.uuid4(),
        email=body.email,
        hashed_password=get_password_hash(body.password),
        full_name=body.full_name,
        role=body.role,
        is_active=True,
    )
    db.add(new_user)

    db.add(AuditTrail(
        entity_type="User",
        entity_id=str(new_user.id),
        action="user_created",
        changes={"email": body.email, "role": body.role.value},
        actor_id=str(current_user.id),
    ))
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    current_user: User = Depends(_admin_only()),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    changes: dict = {}
    if body.full_name is not None:
        user.full_name = body.full_name
        changes["full_name"] = body.full_name
    if body.role is not None:
        changes["role"] = {"from": user.role.value, "to": body.role.value}
        user.role = body.role
    if body.is_active is not None:
        changes["is_active"] = {"from": user.is_active, "to": body.is_active}
        user.is_active = body.is_active
    if body.password is not None:
        user.hashed_password = get_password_hash(body.password)
        changes["password"] = "updated"

    if hasattr(user, "updated_at"):
        user.updated_at = datetime.now(timezone.utc)

    db.add(AuditTrail(
        entity_type="User",
        entity_id=str(user.id),
        action="user_updated",
        changes=changes,
        actor_id=str(current_user.id),
    ))
    await db.commit()
    await db.refresh(user)
    return user
