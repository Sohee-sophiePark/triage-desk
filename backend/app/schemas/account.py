import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel

from app.models.account import AccountStatus, AccountType


class AccountBase(BaseModel):
    customer_id: uuid.UUID
    account_number: str
    account_type: AccountType
    balance: float = 0
    currency: str = "USD"
    status: AccountStatus = AccountStatus.active
    opened_date: date
    closed_date: Optional[date] = None

class AccountCreate(AccountBase):
    pass

class AccountResponse(AccountBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
