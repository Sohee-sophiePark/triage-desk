import enum
import uuid

from sqlalchemy import Date, Enum, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class ProductCategory(str, enum.Enum):
    deposit = "deposit"
    equity = "equity"
    bond = "bond"
    mutual_fund = "mutual_fund"
    etf = "etf"
    insurance = "insurance"
    loan = "loan"

class ProductHolding(Base, UUIDMixin):
    __tablename__ = "product_holdings"

    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("product_catalog.id"))
    product_type: Mapped[ProductCategory] = mapped_column(Enum(ProductCategory), nullable=True)
    quantity: Mapped[float] = mapped_column(Numeric(15, 4), nullable=True)
    current_value: Mapped[float] = mapped_column(Numeric(15, 2), nullable=True)
    acquisition_date: Mapped[str] = mapped_column(Date, nullable=True)
    acquisition_price: Mapped[float] = mapped_column(Numeric(15, 2), nullable=True)

    customer = relationship("Customer", back_populates="holdings")
    product = relationship("ProductCatalog")
