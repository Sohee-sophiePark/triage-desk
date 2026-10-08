import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel

from app.models.holding import ProductCategory


class HoldingBase(BaseModel):
    customer_id: uuid.UUID
    product_id: uuid.UUID
    product_type: Optional[ProductCategory] = None
    quantity: Optional[float] = None
    current_value: Optional[float] = None
    acquisition_date: Optional[date] = None
    acquisition_price: Optional[float] = None

class HoldingCreate(HoldingBase):
    pass

class HoldingResponse(HoldingBase):
    id: uuid.UUID

    class Config:
        from_attributes = True
