import enum

from sqlalchemy import Date, Enum, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class IncomeBracket(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    very_high = "very_high"

class RiskTolerance(str, enum.Enum):
    conservative = "conservative"
    moderate = "moderate"
    aggressive = "aggressive"

class Segment(str, enum.Enum):
    mass = "mass"
    affluent = "affluent"
    hnw = "hnw"
    uhnw = "uhnw"

class KYCStatus(str, enum.Enum):
    pending = "pending"
    verified = "verified"
    expired = "expired"
    flagged = "flagged"

class Customer(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "customers"

    external_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    date_of_birth: Mapped[str] = mapped_column(Date, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=True)
    address_line1: Mapped[str] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=True)
    state: Mapped[str] = mapped_column(String(50), nullable=True)
    zip_code: Mapped[str] = mapped_column(String(10), nullable=True)

    income_bracket: Mapped[IncomeBracket] = mapped_column(Enum(IncomeBracket), nullable=False)
    annual_income: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True)
    credit_score: Mapped[int] = mapped_column(nullable=True)
    risk_tolerance: Mapped[RiskTolerance] = mapped_column(Enum(RiskTolerance), nullable=True)
    segment: Mapped[Segment] = mapped_column(Enum(Segment), nullable=True)
    kyc_status: Mapped[KYCStatus] = mapped_column(Enum(KYCStatus), nullable=True)

    accounts = relationship("Account", back_populates="customer")
    holdings = relationship("ProductHolding", back_populates="customer")
    risk_incidents = relationship("RiskIncident", back_populates="customer")
