import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_current_user, require_role
from app.db.database import get_db
from app.models.account import Account
from app.models.customer import Customer
from app.models.holding import ProductHolding
from app.models.risk_incident import RiskIncident
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.account import AccountResponse
from app.schemas.common import APIResponse
from app.schemas.customer import CustomerResponse
from app.schemas.holding import HoldingResponse
from app.schemas.risk_incident import RiskIncidentResponse
from app.schemas.transaction import TransactionResponse

router = APIRouter()

_CUSTOMER_LIST_ROLES = ["admin", "risk_analyst", "fraud_investigator", "compliance_officer"]

@router.get("", response_model=APIResponse[list[CustomerResponse]], dependencies=[Depends(require_role(_CUSTOMER_LIST_ROLES))])
async def list_customers(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    offset = (page - 1) * size
    query = select(Customer).offset(offset).limit(size)
    result = await db.execute(query)
    customers = result.scalars().all()

    return APIResponse(
        status="success",
        data=[CustomerResponse.model_validate(c) for c in customers],
        meta={"page": page, "size": size, "count": len(customers)}
    )

_CUSTOMER_ROLES = ["admin", "risk_analyst", "fraud_investigator", "compliance_officer"]

@router.get("/{customer_id}", response_model=APIResponse[CustomerResponse], dependencies=[Depends(require_role(_CUSTOMER_ROLES))])
async def get_customer(
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Customer).where(Customer.id == customer_id)
    result = await db.execute(query)
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return APIResponse(status="success", data=CustomerResponse.model_validate(customer))

@router.get("/{customer_id}/accounts", response_model=APIResponse[list[AccountResponse]], dependencies=[Depends(require_role(_CUSTOMER_ROLES))])
async def get_customer_accounts(
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Account).where(Account.customer_id == customer_id)
    result = await db.execute(query)
    accounts = result.scalars().all()
    return APIResponse(status="success", data=[AccountResponse.model_validate(a) for a in accounts])

@router.get("/{customer_id}/holdings", response_model=APIResponse[list[HoldingResponse]], dependencies=[Depends(require_role(_CUSTOMER_ROLES))])
async def get_customer_holdings(
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(ProductHolding).where(ProductHolding.customer_id == customer_id)
    result = await db.execute(query)
    holdings = result.scalars().all()
    return APIResponse(status="success", data=[HoldingResponse.model_validate(h) for h in holdings])

@router.get("/{customer_id}/transactions", response_model=APIResponse[list[TransactionResponse]], dependencies=[Depends(require_role(_CUSTOMER_ROLES))])
async def get_customer_transactions(
    customer_id: uuid.UUID,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    offset = (page - 1) * size
    query = (
        select(Transaction)
        .join(Account)
        .where(Account.customer_id == customer_id)
        .offset(offset)
        .limit(size)
    )
    result = await db.execute(query)
    txns = result.scalars().all()
    return APIResponse(
        status="success",
        data=[TransactionResponse.model_validate(t) for t in txns],
        meta={"page": page, "size": size, "count": len(txns)},
    )

@router.get("/{customer_id}/risk-incidents", response_model=APIResponse[list[RiskIncidentResponse]], dependencies=[Depends(require_role(["admin", "risk_analyst", "fraud_investigator", "compliance_officer"]))])
async def get_customer_risk_incidents(
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(RiskIncident).where(RiskIncident.customer_id == customer_id)
    result = await db.execute(query)
    incidents = result.scalars().all()
    return APIResponse(status="success", data=[RiskIncidentResponse.model_validate(r) for r in incidents])
