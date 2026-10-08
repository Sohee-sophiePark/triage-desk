import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.transaction import TransactionChannel, TransactionStatus, TransactionType


class TransactionBase(BaseModel):
    account_id: uuid.UUID
    amount: float
    transaction_type: Optional[TransactionType] = None
    category: Optional[str] = None
    merchant: Optional[str] = None
    channel: Optional[TransactionChannel] = None
    status: Optional[TransactionStatus] = None
    risk_flag: bool = False
    timestamp: datetime
    description: Optional[str] = None

class TransactionCreate(TransactionBase):
    pass

class TransactionResponse(TransactionBase):
    id: uuid.UUID

    class Config:
        from_attributes = True
