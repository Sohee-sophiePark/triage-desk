import enum

from sqlalchemy import Enum, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class CatalogCategory(str, enum.Enum):
    deposit = "deposit"
    equity = "equity"
    bond = "bond"
    fund = "fund"
    insurance = "insurance"
    loan = "loan"

class ProductRiskLevel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"

class ProductCatalog(Base, UUIDMixin):
    __tablename__ = "product_catalog"

    name: Mapped[str] = mapped_column(String(255), nullable=True)
    category: Mapped[CatalogCategory] = mapped_column(Enum(CatalogCategory), nullable=True)
    risk_level: Mapped[ProductRiskLevel] = mapped_column(Enum(ProductRiskLevel), nullable=True)
    min_investment: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True)
    expected_return_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=True)
    fee_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
