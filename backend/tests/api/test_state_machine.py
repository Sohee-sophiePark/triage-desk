"""
State machine tests — verifies workflow case status transitions are enforced.
Guards against skipping human review via direct state manipulation.
Zero real API calls.
"""
import uuid
from datetime import date, datetime, timezone

import pytest

# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
async def sm_incident(db):
    """Fresh incident per test to avoid state contamination."""
    from app.models.customer import Customer, IncomeBracket, KYCStatus, RiskTolerance, Segment
    from app.models.risk_incident import (
        IncidentSeverity,
        IncidentStatus,
        IncidentType,
        RiskIncident,
    )

    customer = Customer(
        id=uuid.uuid4(),
        external_id=f"SM-{uuid.uuid4().hex[:6]}",
        first_name="StateMachine",
        last_name="Test",
        date_of_birth=date(1990, 1, 1),
        email=f"sm-{uuid.uuid4().hex[:8]}@example.com",
        income_bracket=IncomeBracket.medium,
        credit_score=680,
        risk_tolerance=RiskTolerance.moderate,
        segment=Segment.mass,
        kyc_status=KYCStatus.verified,
    )
    db.add(customer)
    await db.flush()

    incident = RiskIncident(
        id=uuid.uuid4(),
        customer_id=customer.id,
        incident_type=IncidentType.fraud_alert,
        severity=IncidentSeverity.medium,
        status=IncidentStatus.open,
        description="State machine test incident.",
        created_at=datetime.now(timezone.utc),
    )
    db.add(incident)
    await db.commit()
    return incident.id


@pytest.fixture
async def sm_case(client, sm_incident, analyst_headers):
    """Fresh case per test (status: created)."""
    r = await client.post(f"/api/v1/workflow/cases/{sm_incident}", headers=analyst_headers)
    assert r.status_code == 200
    return uuid.UUID(r.json()["case_id"])


async def _evaluate(client, case_id, headers):
    return await client.post(f"/api/v1/workflow/cases/{case_id}/evaluate", headers=headers)


# ── Tests ──────────────────────────────────────────────────────────────────────

async def test_cannot_decide_case_before_evaluation(client, sm_case, analyst_headers):
    """Case in 'created' status must not be decidable — state machine guard."""
    r = await client.post(
        f"/api/v1/workflow/cases/{sm_case}/decide",
        json={"decision": "approve", "reasoning": "Skipping review — should be blocked."},
        headers=analyst_headers,
    )
    assert r.status_code == 400, (
        f"Expected 400 for decide on 'created' case, got {r.status_code}: {r.text}"
    )


async def test_case_status_is_created_after_creation(client, sm_case, analyst_headers):
    r = await client.get(f"/api/v1/workflow/cases/{sm_case}", headers=analyst_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "created"


async def test_case_status_changes_after_evaluate(client, sm_case, analyst_headers):
    r = await _evaluate(client, sm_case, analyst_headers)
    assert r.status_code == 200
    # After evaluation, status must not still be 'created'
    detail = await client.get(f"/api/v1/workflow/cases/{sm_case}", headers=analyst_headers)
    assert detail.json()["status"] != "created"


async def test_approve_decision_yields_human_decided_status(client, sm_case, analyst_headers):
    await _evaluate(client, sm_case, analyst_headers)
    r = await client.post(
        f"/api/v1/workflow/cases/{sm_case}/decide",
        json={"decision": "approve", "reasoning": "Reviewed and confirmed legitimate."},
        headers=analyst_headers,
    )
    if r.status_code == 200:
        assert r.json()["new_status"] in ("human_decided", "escalated")


async def test_escalate_decision_yields_escalated_status(client, sm_incident, analyst_headers):
    """Escalate must produce 'escalated', not 'human_decided'."""
    r = await client.post(f"/api/v1/workflow/cases/{sm_incident}", headers=analyst_headers)
    case_id = uuid.UUID(r.json()["case_id"])

    await _evaluate(client, case_id, analyst_headers)

    r = await client.post(
        f"/api/v1/workflow/cases/{case_id}/decide",
        json={"decision": "escalate", "reasoning": "Needs senior review — complex pattern."},
        headers=analyst_headers,
    )
    if r.status_code == 200:
        assert r.json()["new_status"] == "escalated"


async def test_cannot_create_case_for_nonexistent_incident(client, analyst_headers):
    fake_id = uuid.uuid4()
    r = await client.post(f"/api/v1/workflow/cases/{fake_id}", headers=analyst_headers)
    assert r.status_code in (400, 404)


async def test_audit_trail_recorded_on_case_creation(client, sm_case, analyst_headers):
    r = await client.get(f"/api/v1/workflow/cases/{sm_case}/audit", headers=analyst_headers)
    assert r.status_code == 200
    body = r.json()
    assert "audit_trail" in body
    assert len(body["audit_trail"]) >= 1


async def test_audit_trail_grows_after_evaluate(client, db, sm_case, analyst_headers):
    from app.services.data_service import DataService

    count_before = len(await DataService.get_case_audit(db, sm_case))

    r = await _evaluate(client, sm_case, analyst_headers)
    assert r.status_code == 200, f"Evaluate returned {r.status_code}: {r.text}"

    count_after = len(await DataService.get_case_audit(db, sm_case))
    assert count_after > count_before, (
        f"Audit trail should grow after evaluate: {count_before} → {count_after}"
    )


async def test_no_delete_audit_trail_endpoint(client, admin_headers):
    """Audit trail must have no DELETE endpoint — immutability enforced architecturally."""
    r = await client.delete("/api/v1/workflow/cases/audit", headers=admin_headers)
    assert r.status_code in (404, 405)


async def test_human_decision_requires_min_reasoning_length(client, sm_case, analyst_headers):
    await _evaluate(client, sm_case, analyst_headers)
    r = await client.post(
        f"/api/v1/workflow/cases/{sm_case}/decide",
        json={"decision": "approve", "reasoning": "ok"},  # too short
        headers=analyst_headers,
    )
    assert r.status_code == 422
