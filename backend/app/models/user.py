import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, String

from .base import Base, TimestampMixin, UUIDMixin


class Role(str, enum.Enum):
    ADMIN = "admin"
    INVESTIGATOR = "fraud_investigator"
    COMPLIANCE = "compliance_officer"
    RISK_ANALYST = "risk_analyst"

class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(Role), nullable=False, default=Role.INVESTIGATOR)
    is_active = Column(Boolean(), default=True)
    full_name = Column(String(100))
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)
