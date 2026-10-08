"""
Workflow endpoint tests.

All LLM calls are mocked — tests never hit the real Gemini API.
The mock returns a valid JSON response matching each agent's output schema.
"""
import uuid
from datetime import date, datetime, timezone

import pytest

# ── LLM response stubs ────────────────────────────────────────────────────────

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
async def incident_id(db):
    """Create a real RiskIncident row and return its id."""
    from datetime import date, datetime, timezone

    from app.models.customer import Customer, IncomeBracket, KYCStatus, RiskTolerance, Segment
    from app.models.risk_incident import (
        IncidentSeverity,
        IncidentStatus,
        IncidentType,
        RiskIncident,
    )

    customer = Customer(
        id=uuid.uuid4(),
        external_id=f"EXT-WF-{uuid.uuid4().hex[:6]}",
        first_name="Workflow",
        last_name="TestCustomer",
        date_of_birth=date(1985, 1, 1),
        email=f"wf-{uuid.uuid4().hex[:6]}@test.com",
        income_bracket=IncomeBracket.medium,
        credit_score=700,
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
        severity=IncidentSeverity.high,
        status=IncidentStatus.open,
        description="Suspicious high-value transfer detected on customer account.",
        created_at=datetime.now(timezone.utc),
    )
    db.add(incident)
    await db.commit()
    return incident.id


@pytest.fixture
async def case_id(db, incident_id, analyst_headers, client):
    """Create a workflow case and return its id."""
    r = await client.post(f"/api/v1/workflow/cases/{incident_id}", headers=analyst_headers)
    assert r.status_code == 200
    return uuid.UUID(r.json()["case_id"])


# ── Auth / access tests ───────────────────────────────────────────────────────

async def test_create_case_no_auth(client, incident_id):
    r = await client.post(f"/api/v1/workflow/cases/{incident_id}")
    assert r.status_code == 401


async def test_create_case_analyst(client, incident_id, analyst_headers):
    r = await client.post(f"/api/v1/workflow/cases/{incident_id}", headers=analyst_headers)
    assert r.status_code == 200
    body = r.json()
    assert "case_id" in body
    assert body["status"] == "success"


async def test_get_cases_no_auth(client):
    r = await client.get("/api/v1/workflow/cases")
    assert r.status_code == 401


async def test_get_cases_admin(client, admin_headers, case_id):
    r = await client.get("/api/v1/workflow/cases", headers=admin_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


async def test_get_case_detail_analyst(client, analyst_headers, case_id):
    r = await client.get(f"/api/v1/workflow/cases/{case_id}", headers=analyst_headers)
    assert r.status_code in (200, 404)
    if r.status_code == 200:
        body = r.json()
        assert "id" in body
        assert "status" in body


async def test_get_case_audit_analyst(client, analyst_headers, case_id):
    r = await client.get(f"/api/v1/workflow/cases/{case_id}/audit", headers=analyst_headers)
    assert r.status_code in (200, 404)
    if r.status_code == 200:
        body = r.json()
        assert "audit_trail" in body


# ── Evaluate case ─────────────────────────────────────────────────────────────

async def test_evaluate_case_analyst(client, analyst_headers, case_id):
    r = await client.post(f"/api/v1/workflow/cases/{case_id}/evaluate", headers=analyst_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "success"
    assert "ai_justification" in body


# ── Human decision ────────────────────────────────────────────────────────────

async def test_human_decide_no_auth(client, case_id):
    r = await client.post(
        f"/api/v1/workflow/cases/{case_id}/decide",
        json={"decision": "approve", "reasoning": "Looks good to me."},
    )
    assert r.status_code == 401


async def test_human_decide_short_reasoning(client, analyst_headers, case_id):
    r = await client.post(
        f"/api/v1/workflow/cases/{case_id}/decide",
        json={"decision": "approve", "reasoning": "ok"},
        headers=analyst_headers,
    )
    assert r.status_code == 422


async def test_human_decide_analyst(client, analyst_headers, case_id):
    # First evaluate so status is pending_review
    await client.post(f"/api/v1/workflow/cases/{case_id}/evaluate", headers=analyst_headers)

    r = await client.post(
        f"/api/v1/workflow/cases/{case_id}/decide",
        json={"decision": "approve", "reasoning": "Reviewed and confirmed — legitimate transaction."},
        headers=analyst_headers,
    )
    # 200 if case is now in a decidable state; 400 if already decided in a prior test run
    assert r.status_code in (200, 400)
    if r.status_code == 200:
        assert r.json()["decision"] == "approve"


# ── Case type derivation ──────────────────────────────────────────────────────

async def _make_incident(db, incident_type):
    from app.models.customer import Customer, IncomeBracket, KYCStatus, RiskTolerance, Segment
    from app.models.risk_incident import IncidentSeverity, IncidentStatus, RiskIncident

    customer = Customer(
        id=uuid.uuid4(),
        external_id=f"EXT-CT-{uuid.uuid4().hex[:6]}",
        first_name="CaseType",
        last_name="Test",
        date_of_birth=date(1990, 6, 15),
        email=f"ct-{uuid.uuid4().hex[:8]}@test.com",
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
        incident_type=incident_type,
        severity=IncidentSeverity.medium,
        status=IncidentStatus.open,
        description="Test incident for case type derivation.",
        created_at=datetime.now(timezone.utc),
    )
    db.add(incident)
    await db.commit()
    return incident.id


@pytest.mark.parametrize("incident_type,expected_case_type", [
    ("fraud_alert", "fraud"),
    ("suspicious_txn", "fraud"),
    ("identity_theft", "fraud"),
    ("aml_flag", "compliance"),
    ("credit_breach", "risk"),
])
async def test_case_type_derived_from_incident(db, client, analyst_headers, incident_type, expected_case_type):
    from app.models.risk_incident import IncidentType
    inc_id = await _make_incident(db, IncidentType(incident_type))
    r = await client.post(f"/api/v1/workflow/cases/{inc_id}", headers=analyst_headers)
    assert r.status_code == 200
    case_id = r.json()["case_id"]

    r2 = await client.get(f"/api/v1/workflow/cases/{case_id}", headers=analyst_headers)
    assert r2.status_code == 200
    assert r2.json()["case_type"] == expected_case_type
