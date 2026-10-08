from fastapi import APIRouter

from app.api.v1 import analytics, auth, customers, products, risk, users, workflow

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(customers.router, prefix="/customers", tags=["customers"])
api_router.include_router(risk.router, prefix="/risk", tags=["risk"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(workflow.router, prefix="/workflow", tags=["workflow"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
