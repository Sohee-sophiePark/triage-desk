import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.agents.graph import run_case
from app.agents.llm import get_client
from app.models.audit_trail import AuditTrail
from app.models.risk_incident import RiskIncident
from app.models.workflow_case import CaseStatus, CaseType, WorkflowCase


class WorkflowService:
    @staticmethod
    async def create_case_from_incident(db: AsyncSession, incident_id: uuid.UUID) -> WorkflowCase:
        result = await db.execute(select(RiskIncident).where(RiskIncident.id == incident_id))
        incident = result.scalar_one_or_none()
        if not incident:
            raise ValueError("Incident not found.")

        now = datetime.now(timezone.utc)
        _INCIDENT_TYPE_TO_CASE_TYPE = {
            "fraud_alert": CaseType.fraud,
            "suspicious_txn": CaseType.fraud,
            "identity_theft": CaseType.fraud,
            "aml_flag": CaseType.compliance,
            "credit_breach": CaseType.risk,
        }
        case_type = _INCIDENT_TYPE_TO_CASE_TYPE.get(
            incident.incident_type.value if incident.incident_type else "",
            CaseType.fraud,
        )

        new_case = WorkflowCase(
            id=uuid.uuid4(),
            case_type=case_type,
            status=CaseStatus.created,
            incident_id=incident_id,
            created_at=now,
            updated_at=now,
        )
        db.add(new_case)

        audit = AuditTrail(
            entity_type="WorkflowCase",
            entity_id=str(new_case.id),
            action="case_created",
            changes={"incident_id": str(incident_id), "status": CaseStatus.created},
            actor_id="system",
        )
        db.add(audit)
        await db.commit()
        return new_case

    @staticmethod
    async def run_ai_evaluation(db: AsyncSession, case_id: uuid.UUID) -> dict:
        """Run the case graph once; store the snapshot and move the case to PENDING_REVIEW or ESCALATED."""
        result = await db.execute(select(WorkflowCase).where(WorkflowCase.id == case_id))
        case = result.scalar_one_or_none()
        if not case:
            raise ValueError("Case not found.")
        if not case.incident_id:
            raise ValueError("Case has no linked incident.")

        case.status = CaseStatus.ai_processing
        case.updated_at = datetime.now(timezone.utc)
        await db.commit()

        out = await run_case(db, get_client(), str(case.id), case.case_type.value, str(case.incident_id))
        snapshot = out["snapshot"]
        final_status = CaseStatus(out["status"])
        confidence = snapshot["evaluation"]["confidence_score"]

        case.status = final_status
        case.confidence_score = confidence
        case.ai_evaluation = snapshot
        case.updated_at = datetime.now(timezone.utc)
        db.add(AuditTrail(
            entity_type="WorkflowCase",
            entity_id=str(case.id),
            action="ai_evaluation_complete",
            changes={
                "lane": out["lane"],
                "specialists": out["plan"],
                "severity": out["severity"],
                "disposition": (snapshot["brief"] or {}).get("disposition"),
                "revisions": out["revisions"],
                "compliance_passed": snapshot["compliance_result"]["passed"],
                "confidence_score": confidence,
                "final_status": final_status,
            },
            actor_id="triage_desk_pipeline",
        ))
        await db.commit()

        return {
            "justification": snapshot["risk_assessment"]["justification"],
            "status": final_status,
            "confidence_score": confidence,
            "risk_assessment": snapshot["risk_assessment"],
            "evaluation": snapshot["evaluation"],
        }
