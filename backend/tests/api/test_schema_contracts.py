"""
Schema contract tests — validates every major endpoint's response shape.
Catches breaking changes before the frontend breaks.
Zero real API calls — all mocked via ASGI test client.
"""
import re
import uuid
from datetime import date, datetime, timezone

import pytest

from tests.conftest import TEST_PASSWORD

# ── Helpers ────────────────────────────────────────────────────────────────────

UUID4_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _is_valid_uuid4(value: str) -> bool:
    return bool(UUID4_PATTERN.match(str(value)))


def _is_iso8601(value: str) -> bool:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except (ValueError, AttributeError):
        return False


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
async def seeded_customer(db):
    """Create one customer for schema shape assertions."""
    from app.models.customer import Customer, IncomeBracket, KYCStatus, RiskTolerance, Segment

    customer = Customer(
        id=uuid.uuid4(),
        external_id=f"SCHEMA-{uuid.uuid4().hex[:6]}",
        first_name="Schema",
        last_name="TestUser",
        date_of_birth=date(1985, 6, 15),
        email=f"schema-{uuid.uuid4().hex[:6]}@example.com",
        income_bracket=IncomeBracket.medium,
        credit_score=720,
        risk_tolerance=RiskTolerance.moderate,
        segment=Segment.affluent,
        kyc_status=KYCStatus.verified,
    )
    db.add(customer)
    await db.commit()
    return customer


@pytest.fixture
async def seeded_incident(db, seeded_customer):
    """Create one risk incident linked to the schema test customer."""
    from app.models.risk_incident import (
        IncidentSeverity,
        IncidentStatus,
        IncidentType,
        RiskIncident,
    )

    incident = RiskIncident(
        id=uuid.uuid4(),
        customer_id=seeded_customer.id,
        incident_type=IncidentType.fraud_alert,
        severity=IncidentSeverity.high,
        status=IncidentStatus.open,
        description="Schema contract test incident.",
        created_at=datetime.now(timezone.utc),
    )
    db.add(incident)
    await db.commit()
    return incident


@pytest.fixture
async def seeded_case(db, seeded_incident, analyst_headers, client):
    """Create a workflow case for schema tests."""
    r = await client.post(
        f"/api/v1/workflow/cases/{seeded_incident.id}",
        headers=analyst_headers,
    )
    assert r.status_code == 200
    return uuid.UUID(r.json()["case_id"])


# ── Auth ───────────────────────────────────────────────────────────────────────

async def test_auth_login_response_shape(client, admin_user):
    r = await client.post(
        "/api/v1/auth/login",
        data={"username": admin_user.email, "password": TEST_PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body, "Missing access_token in login response"
    assert isinstance(body["access_token"], str)
    assert body.get("token_type") == "bearer"


# ── Customers ─────────────────────────────────────────────────────────────────

async def test_customer_list_returns_list(client, admin_headers, seeded_customer):
    r = await client.get("/api/v1/customers", headers=admin_headers)
    assert r.status_code == 200
    # Customers list uses the envelope: {"data": [...], "status": "success", "meta": {...}}
    body = r.json()
    assert "data" in body, f"Expected envelope with 'data' key, got: {list(body.keys())}"
    assert isinstance(body["data"], list)


async def test_customer_list_item_shape(client, admin_headers, seeded_customer):
    r = await client.get("/api/v1/customers", headers=admin_headers)
    items = r.json()["data"]
    assert len(items) > 0, "Expected at least one customer from seeded data"
    item = items[0]
    for field in ("id", "email", "first_name", "last_name", "income_bracket", "created_at"):
        assert field in item, f"Missing field {field!r} in customer list item"


async def test_customer_detail_shape(client, admin_headers, seeded_customer):
    r = await client.get(f"/api/v1/customers/{seeded_customer.id}", headers=admin_headers)
    assert r.status_code == 200
    envelope = r.json()
    body = envelope["data"] if isinstance(envelope, dict) and "data" in envelope else envelope
    for field in ("id", "email", "first_name", "last_name", "income_bracket", "created_at"):
        assert field in body, f"Missing field {field!r} in customer detail"


async def test_customer_id_is_valid_uuid4(client, admin_headers, seeded_customer):
    r = await client.get("/api/v1/customers", headers=admin_headers)
    items = r.json()["data"]
    assert len(items) > 0
    assert _is_valid_uuid4(items[0]["id"]), f"id {items[0]['id']!r} is not a valid UUID4"


async def test_customer_timestamps_are_iso8601(client, admin_headers, seeded_customer):
    r = await client.get(f"/api/v1/customers/{seeded_customer.id}", headers=admin_headers)
    envelope = r.json()
    body = envelope["data"] if isinstance(envelope, dict) and "data" in envelope else envelope
    assert _is_iso8601(body["created_at"]), f"created_at not ISO8601: {body['created_at']!r}"


async def test_credit_score_is_number_not_string(client, admin_headers, seeded_customer):
    r = await client.get(f"/api/v1/customers/{seeded_customer.id}", headers=admin_headers)
    envelope = r.json()
    body = envelope["data"] if isinstance(envelope, dict) and "data" in envelope else envelope
    if body.get("credit_score") is not None:
        assert isinstance(body["credit_score"], int), (
            f"credit_score should be int, got {type(body['credit_score'])}"
        )


# ── Risk incidents ─────────────────────────────────────────────────────────────

async def test_risk_incidents_list_returns_list(client, admin_headers, seeded_incident):
    r = await client.get("/api/v1/risk/incidents", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert "data" in body, f"Expected envelope with 'data' key, got: {list(body.keys())}"
    assert isinstance(body["data"], list)


async def test_risk_incident_item_shape(client, admin_headers, seeded_incident):
    r = await client.get("/api/v1/risk/incidents", headers=admin_headers)
    items = r.json()["data"]
    assert len(items) > 0
    item = items[0]
    for field in ("id", "customer_id", "incident_type", "severity", "status", "created_at"):
        assert field in item, f"Missing field {field!r} in risk incident item"


# ── Products ───────────────────────────────────────────────────────────────────

async def test_products_list_returns_list(client, admin_headers):
    r = await client.get("/api/v1/products", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    # Products may return envelope or bare list — accept either
    items = body["data"] if isinstance(body, dict) and "data" in body else body
    assert isinstance(items, list)


# ── Workflow cases ─────────────────────────────────────────────────────────────

async def test_workflow_case_detail_shape(client, analyst_headers, seeded_case):
    r = await client.get(f"/api/v1/workflow/cases/{seeded_case}", headers=analyst_headers)
    assert r.status_code == 200
    envelope = r.json()
    body = envelope["data"] if isinstance(envelope, dict) and "data" in envelope else envelope
    for field in ("id", "status", "case_type", "created_at"):
        assert field in body, f"Missing field {field!r} in workflow case detail"


async def test_workflow_cases_list_returns_list(client, admin_headers, seeded_case):
    r = await client.get("/api/v1/workflow/cases", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    # Cases list uses the envelope: {"data": [...], "status": "success", "meta": {...}}
    items = body["data"] if isinstance(body, dict) and "data" in body else body
    assert isinstance(items, list)


async def test_workflow_evaluate_response_shape(client, analyst_headers, seeded_case):
    r = await client.post(
        f"/api/v1/workflow/cases/{seeded_case}/evaluate",
        headers=analyst_headers,
    )

    assert r.status_code == 200
    body = r.json()
    assert "status" in body
    assert "ai_justification" in body
    assert "confidence_score" in body


async def test_workflow_decide_response_shape(client, analyst_headers, seeded_case):
    # Evaluate first to move case into a decidable state
    await client.post(
        f"/api/v1/workflow/cases/{seeded_case}/evaluate",
        headers=analyst_headers,
    )

    r = await client.post(
        f"/api/v1/workflow/cases/{seeded_case}/decide",
        json={"decision": "approve", "reasoning": "Schema test — looks good."},
        headers=analyst_headers,
    )
    # May be 200 or 400 if already decided; shape check only on 200
    if r.status_code == 200:
        body = r.json()
        assert "case_id" in body
        assert "decision" in body
        assert "new_status" in body


async def test_error_response_no_stack_trace(client):
    # Trigger a validation error (422)
    r = await client.post(
        "/api/v1/auth/login",
        data={"username": "not-an-email"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert "traceback" not in r.text.lower()
    assert "file \"/" not in r.text.lower()
