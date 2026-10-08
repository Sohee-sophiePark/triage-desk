import json
import logging
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_current_user, require_role
from app.api.deps_limiter import rate_limit_evaluations
from app.db.database import get_db
from app.models.audit_trail import AuditTrail
from app.models.user import User
from app.models.workflow_case import CaseStatus, CaseType, WorkflowCase
from app.schemas.workflow_case import HumanDecisionRequest, WorkflowCaseResponse
from app.services.data_service import DataService
from app.services.workflow_service import WorkflowService

logger = logging.getLogger(__name__)

router = APIRouter()

_ALL_CASE_ROLES = ["admin", "risk_analyst", "fraud_investigator", "compliance_officer"]

# Which case types each role can see. None = no restriction (admin / risk_analyst see all).
_ROLE_CASE_TYPES: dict[str, list[CaseType] | None] = {
    "admin": None,
    "risk_analyst": None,
    "fraud_investigator": [CaseType.fraud],
    "compliance_officer": [CaseType.compliance],
}


# ── Create case ────────────────────────────────────────────────────────────────

@router.post(
    "/cases/{incident_id}",
    dependencies=[Depends(require_role(["admin", "risk_analyst"]))],
)
async def create_case(
    incident_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Initialize a workflow case for a risk incident."""
    try:
        case = await WorkflowService.create_case_from_incident(db, incident_id)
        return {"status": "success", "case_id": str(case.id)}
    except Exception as e:
        logger.warning("create_case failed for incident %s: %s", incident_id, e)
        raise HTTPException(status_code=400, detail="Unable to create case for this incident.")


# ── Evaluate case ──────────────────────────────────────────────────────────────

@router.post(
    "/cases/{case_id}/evaluate",
    dependencies=[
        Depends(require_role(["admin", "risk_analyst"])),
        Depends(rate_limit_evaluations(max_requests=5)),
    ],
)
async def evaluate_case(
    case_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger the AI multi-agent evaluation for a case."""
    try:
        result = await WorkflowService.run_ai_evaluation(db, case_id)
        return {
            "status": "success",
            "ai_justification": result["justification"],
            "confidence_score": result.get("confidence_score"),
            "case_status": result["status"],
        }
    except Exception as e:
        logger.warning("evaluate_case failed for case %s: %s", case_id, e)
        raise HTTPException(status_code=400, detail="AI evaluation failed. Please try again or contact support.")


# ── List cases ─────────────────────────────────────────────────────────────────

@router.get(
    "/cases",
    response_model=List[WorkflowCaseResponse],
    dependencies=[Depends(require_role(_ALL_CASE_ROLES))],
)
async def list_cases(
    status: Optional[CaseStatus] = Query(None),
    case_type: Optional[CaseType] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List workflow cases filtered by role and optional status/type."""
    query = select(WorkflowCase).order_by(WorkflowCase.created_at.desc())

    # Role-based case type scoping
    role_types = _ROLE_CASE_TYPES.get(current_user.role)
    if role_types is not None:
        query = query.where(WorkflowCase.case_type.in_(role_types))

    if status:
        query = query.where(WorkflowCase.status == status)
    if case_type:
        query = query.where(WorkflowCase.case_type == case_type)
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    cases = result.scalars().all()
    return cases


# ── Case detail ────────────────────────────────────────────────────────────────

@router.get(
    "/cases/{case_id}",
    response_model=WorkflowCaseResponse,
    dependencies=[Depends(require_role(_ALL_CASE_ROLES))],
)
async def get_case(
    case_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get full case detail including AI evaluation snapshot."""
    result = await db.execute(select(WorkflowCase).where(WorkflowCase.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    return case


# ── Case audit trail ───────────────────────────────────────────────────────────

@router.get(
    "/cases/{case_id}/audit",
    dependencies=[Depends(require_role(_ALL_CASE_ROLES))],
)
async def get_case_audit(
    case_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve immutable audit trail for a case."""
    result = await db.execute(
        select(WorkflowCase).where(WorkflowCase.id == case_id)
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")

    audit_rows = await DataService.get_case_audit(db, case_id)
    return {"status": "success", "case_id": str(case_id), "audit_trail": audit_rows}


# ── Human decision ─────────────────────────────────────────────────────────────

@router.post(
    "/cases/{case_id}/decide",
    dependencies=[Depends(require_role(_ALL_CASE_ROLES))],
)
async def submit_human_decision(
    case_id: uuid.UUID,
    body: HumanDecisionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit a human decision on a case (approve/reject/escalate)."""
    result = await db.execute(select(WorkflowCase).where(WorkflowCase.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")

    allowed_statuses = {
        CaseStatus.pending_review,
        CaseStatus.in_review,
        CaseStatus.ai_evaluated,
    }
    if case.status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Case cannot be decided in status: {case.status}",
        )

    decision_map = {
        "approve": CaseStatus.human_decided,
        "reject": CaseStatus.human_decided,
        "escalate": CaseStatus.escalated,
    }
    new_status = decision_map[body.decision]
    now = datetime.now(timezone.utc)

    case.human_decision = {
        "decision": body.decision,
        "reasoning": body.reasoning,
        "decided_by": str(current_user.id),
        "decided_at": now.isoformat(),
    }
    case.status = new_status
    case.assigned_to = current_user.id
    case.updated_at = now

    audit = AuditTrail(
        entity_type="WorkflowCase",
        entity_id=str(case_id),
        action="human_decision",
        changes={
            "decision": body.decision,
            "reasoning": body.reasoning,
            "new_status": new_status,
        },
        actor_id=str(current_user.id),
    )
    db.add(audit)
    await db.commit()

    return {
        "status": "success",
        "case_id": str(case_id),
        "decision": body.decision,
        "new_status": new_status,
    }


# ── SSE streaming ──────────────────────────────────────────────────────────────

@router.get(
    "/cases/{case_id}/stream",
    dependencies=[Depends(require_role(_ALL_CASE_ROLES))],
)
async def stream_case_evaluation(
    case_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    SSE stream — replays the stored agent progress events for a case.
    Emits each audit trail event and then the final evaluation state.
    """
    result = await db.execute(select(WorkflowCase).where(WorkflowCase.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")

    audit_rows = await DataService.get_case_audit(db, case_id)
    ai_eval = case.ai_evaluation or {}

    async def event_generator() -> AsyncGenerator[str, None]:
        for row in audit_rows:
            payload = {
                "event": row["action"],
                "actor": row["actor_id"],
                "changes": row["changes"],
                "timestamp": row["created_at"],
            }
            yield f"data: {json.dumps(payload)}\n\n"

        # Emit structured agent result events from the stored snapshot
        if ai_eval.get("risk_assessment"):
            ra = ai_eval["risk_assessment"]
            yield f"data: {json.dumps({'event': 'investigator_complete', 'confidence': ra.get('confidence'), 'is_fraud': ra.get('is_fraud')})}\n\n"

        if ai_eval.get("compliance_result"):
            cr = ai_eval["compliance_result"]
            yield f"data: {json.dumps({'event': 'compliance_complete', 'passed': cr.get('passed')})}\n\n"

        if ai_eval.get("evaluation"):
            ev = ai_eval["evaluation"]
            yield f"data: {json.dumps({'event': 'evaluator_complete', 'confidence_score': ev.get('confidence_score')})}\n\n"

        yield f"data: {json.dumps({'event': 'done', 'status': case.status.value if case.status else 'unknown'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
