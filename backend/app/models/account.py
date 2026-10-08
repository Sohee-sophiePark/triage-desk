import enum
import uuid

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class AccountType(str, enum.Enum):
    checking = "checking"
    savings = "savings"
    investment = "investment"
    loan = "loan"
    credit_card = "credit_card"

class AccountStatus(str, enum.Enum):
    active = "active"
    dormant = "dormant"
    closed = "closed"
    frozen = "frozen"

class Account(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "accounts"

    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), index=True)
    account_number: Mapped[str] = mapped_column(String(20), unique=True)
    account_type: Mapped[AccountType] = mapped_column(Enum(AccountType), nullable=False)
    balance: Mapped[float] = mapped_column(Numeric(15, 2), default=0)
    currency: Mapped[str] = mapped_column(String(3), default='USD')
    status: Mapped[AccountStatus] = mapped_column(Enum(AccountStatus), default=AccountStatus.active)
    opened_date: Mapped[str] = mapped_column(Date, nullable=False)
    closed_date: Mapped[str] = mapped_column(Date, nullable=True)

    customer = relationship("Customer", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account")
