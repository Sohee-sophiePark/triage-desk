from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_current_user, require_role
from app.db.database import get_db
from app.models.risk_incident import RiskIncident
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.risk_incident import RiskIncidentResponse

router = APIRouter()

@router.get("/incidents", response_model=APIResponse[list[RiskIncidentResponse]], dependencies=[Depends(require_role(["admin", "risk_analyst"]))])
async def get_all_risk_incidents(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    offset = (page - 1) * size
    query = select(RiskIncident).offset(offset).limit(size)
    result = await db.execute(query)
    incidents = result.scalars().all()

    return APIResponse(
        status="success",
        data=[RiskIncidentResponse.model_validate(i) for i in incidents],
        meta={"page": page, "size": size, "count": len(incidents)}
    )
