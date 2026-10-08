import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.product_catalog import CatalogCategory, ProductRiskLevel


class ProductCatalogBase(BaseModel):
    name: Optional[str] = None
    category: Optional[CatalogCategory] = None
    risk_level: Optional[ProductRiskLevel] = None
    min_investment: Optional[float] = None
    expected_return_pct: Optional[float] = None
    fee_pct: Optional[float] = None
    description: Optional[str] = None

class ProductCatalogCreate(ProductCatalogBase):
    pass

class ProductCatalogResponse(ProductCatalogBase):
    id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)
