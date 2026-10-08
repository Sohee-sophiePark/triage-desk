from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_current_user
from app.db.database import get_db
from app.models.product_catalog import ProductCatalog
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.product_catalog import ProductCatalogResponse

router = APIRouter()

@router.get("", response_model=APIResponse[list[ProductCatalogResponse]])
async def get_products(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(ProductCatalog)
    result = await db.execute(query)
    products = result.scalars().all()
    return APIResponse(status="success", data=[ProductCatalogResponse.model_validate(p) for p in products])
