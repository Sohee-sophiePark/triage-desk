import enum
import uuid

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class TransactionType(str, enum.Enum):
    debit = "debit"
    credit = "credit"
    transfer = "transfer"
    payment = "payment"
    withdrawal = "withdrawal"
    deposit = "deposit"

class TransactionChannel(str, enum.Enum):
    online = "online"
    mobile = "mobile"
    branch = "branch"
    atm = "atm"
    phone = "phone"

class TransactionStatus(str, enum.Enum):
    completed = "completed"
    pending = "pending"
    failed = "failed"
    reversed = "reversed"

class Transaction(Base, UUIDMixin):
    __tablename__ = "transactions"

    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id"), index=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    transaction_type: Mapped[TransactionType] = mapped_column(Enum(TransactionType), nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=True)
    merchant: Mapped[str] = mapped_column(String(255), nullable=True)
    channel: Mapped[TransactionChannel] = mapped_column(Enum(TransactionChannel), nullable=True)
    status: Mapped[TransactionStatus] = mapped_column(Enum(TransactionStatus), nullable=True)
    risk_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    timestamp: Mapped[DateTime] = mapped_column(DateTime, nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(500), nullable=True)

    account = relationship("Account", back_populates="transactions")
