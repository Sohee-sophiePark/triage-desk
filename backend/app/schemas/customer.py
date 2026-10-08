import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.customer import IncomeBracket, KYCStatus, RiskTolerance, Segment


class CustomerBase(BaseModel):
    external_id: str
    first_name: str
    last_name: str
    date_of_birth: date
    email: EmailStr
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    income_bracket: IncomeBracket
    annual_income: Optional[float] = None
    credit_score: Optional[int] = Field(None, ge=300, le=850)
    risk_tolerance: Optional[RiskTolerance] = None
    segment: Optional[Segment] = None
    kyc_status: Optional[KYCStatus] = None

class CustomerCreate(CustomerBase):
    pass

class CustomerResponse(CustomerBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
