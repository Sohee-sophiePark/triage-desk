"""
Seed workflow cases across all 4 case types so every persona sees populated dashboards.
Idempotent: skips cases that already exist for an incident.
Dev-only guard: exits if ENVIRONMENT != development.
"""
import asyncio
import os
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.future import select

from app.core.config import settings
from app.db.database import AsyncSessionLocal
from app.models.risk_incident import IncidentType, RiskIncident
from app.models.workflow_case import CaseStatus, CaseType, WorkflowCase

# ── Mappings ──────────────────────────────────────────────────────────────────

_INCIDENT_TO_CASE_TYPE: dict[IncidentType, CaseType] = {
    IncidentType.fraud_alert: CaseType.fraud,
    IncidentType.suspicious_txn: CaseType.fraud,
    IncidentType.identity_theft: CaseType.fraud,
    IncidentType.aml_flag: CaseType.compliance,
    IncidentType.credit_breach: CaseType.risk,
}

# Status distribution weights: pending_review 35%, human_decided 30%,
# escalated 15%, ai_evaluated 10%, created 5%, ai_processing 5%
_STATUS_WEIGHTS = [
    (CaseStatus.pending_review, 35),
    (CaseStatus.human_decided, 30),
    (CaseStatus.escalated, 15),
    (CaseStatus.ai_evaluated, 10),
    (CaseStatus.created, 5),
    (CaseStatus.ai_processing, 5),
]
_STATUSES, _WEIGHTS = zip(*_STATUS_WEIGHTS)


def _pick_status() -> CaseStatus:
    return random.choices(_STATUSES, weights=_WEIGHTS, k=1)[0]


def _fake_ai_evaluation(case_type: CaseType, confidence: float) -> dict:
    return {
        "intent": f"{case_type.value}_investigation",
        "routed_agents": ["triage", case_type.value],
        "risk_assessment": {
            "is_fraud": confidence < 60,
            "confidence": confidence,
            "justification": f"Seeded {case_type.value} case for local development.",
            "evidence": [],
        },
        "compliance_result": {
            "passed": confidence >= 50,
            "reason": "Passed all output gates." if confidence >= 50 else "Flagged for review.",
            "violations": [],
        },
        "evaluation": {
            "confidence_score": confidence,
            "hallucination_flags": [],
            "hallucination_count": 0,
            "compliance_score": 100 if confidence >= 50 else 0,
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        },
        "metadata": {"seeded": True},
    }


def _fake_human_decision(approved: bool) -> dict:
    return {
        "decision": "approve" if approved else "reject",
        "reasoning": "Reviewed and confirmed by human analyst." if approved else "Dismissed after investigation.",
        "decided_at": datetime.now(timezone.utc).isoformat(),
    }


async def seed_cases(target_count: int = 30) -> None:
    if settings.ENVIRONMENT != "development":
        print("Not in development mode. Skipping case seeding.")
        return

    print(f"Seeding up to {target_count} workflow cases…")

    async with AsyncSessionLocal() as session:
        # Fetch all incidents
        result = await session.execute(select(RiskIncident).limit(200))
        incidents = result.scalars().all()

        if not incidents:
            print("No risk incidents found — run the data generator first.")
            return

        # Find incidents that already have a case
        existing_result = await session.execute(
            select(WorkflowCase.incident_id).where(WorkflowCase.incident_id.isnot(None))
        )
        already_linked: set[uuid.UUID] = {row[0] for row in existing_result.all()}

        free_incidents = [i for i in incidents if i.id not in already_linked]
        random.shuffle(free_incidents)
        to_use = free_incidents[:target_count]

        created = 0
        now = datetime.now(timezone.utc)

        # ── Cases from incidents ───────────────────────────────────────────────
        for incident in to_use:
            case_type = _INCIDENT_TO_CASE_TYPE.get(incident.incident_type, CaseType.fraud)
            status = _pick_status()
            confidence = round(random.uniform(40.0, 95.0), 1)

            age_days = random.randint(1, 30)
            created_at = now - timedelta(days=age_days)

            # Populate evidence on the incident if empty
            if not incident.evidence_json:
                incident.evidence_json = {
                    "triggered_rule": f"rule_{case_type.value}_{random.randint(1, 99)}",
                    "risk_score": confidence,
                    "notes": f"Auto-generated evidence for {case_type.value} case.",
                }

            ai_eval = None
            human_decision = None
            if status not in (CaseStatus.created, CaseStatus.ai_processing):
                ai_eval = _fake_ai_evaluation(case_type, confidence)
            if status == CaseStatus.human_decided:
                human_decision = _fake_human_decision(confidence >= 60)

            case = WorkflowCase(
                id=uuid.uuid4(),
                case_type=case_type,
                status=status,
                incident_id=incident.id,
                confidence_score=confidence if ai_eval else None,
                ai_evaluation=ai_eval,
                human_decision=human_decision,
                created_at=created_at,
                updated_at=now,
            )
            session.add(case)
            created += 1

        await session.commit()
        print(f"Seeded {created} workflow cases from incidents.")


if __name__ == "__main__":
    asyncio.run(seed_cases())
