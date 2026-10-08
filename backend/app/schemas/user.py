import re
import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.user import Role

_PASSWORD_COMPLEXITY_RE = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{12,}$"
)

_PASSWORD_POLICY_MSG = (
    "Password must be at least 12 characters with uppercase, "
    "lowercase, digit, and special character"
)


def _validate_password_complexity(v: str) -> str:
    if not _PASSWORD_COMPLEXITY_RE.match(v):
        raise ValueError(_PASSWORD_POLICY_MSG)
    return v


# Shared properties
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    role: Role

# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=12)

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        return _validate_password_complexity(v)

# Properties accepted on update (all optional)
class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[Role] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(default=None, min_length=12)

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return _validate_password_complexity(v)

# Properties to return via API
class UserResponse(UserBase):
    id: uuid.UUID
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    role: Optional[Role] = None
