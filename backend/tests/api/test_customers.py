"""
Tests for /api/v1/customers.

Covers: auth required, RBAC role restrictions, response envelope shape.
Customer table is empty in test DB — we test structure, not seed data.
"""
import uuid

# ── Unauthenticated ────────────────────────────────────────────────────────────

async def test_list_customers_no_auth(client):
    r = await client.get("/api/v1/customers")
    assert r.status_code == 401


async def test_get_customer_no_auth(client):
    r = await client.get(f"/api/v1/customers/{uuid.uuid4()}")
    assert r.status_code == 401


# ── RBAC — list endpoint (admin + risk_analyst only) ──────────────────────────

async def test_list_customers_admin(client, admin_headers):
    r = await client.get("/api/v1/customers", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "success"
    assert isinstance(body["data"], list)


async def test_list_customers_analyst(client, analyst_headers):
    r = await client.get("/api/v1/customers", headers=analyst_headers)
    assert r.status_code == 200


async def test_list_customers_investigator_allowed(client, investigator_headers):
    """Phase 5 RBAC fix: all roles can list customers."""
    r = await client.get("/api/v1/customers", headers=investigator_headers)
    assert r.status_code == 200


# ── RBAC — sub-endpoints (all roles allowed) ────────────────────────────────

async def test_get_customer_not_found(client, analyst_headers):
    r = await client.get(f"/api/v1/customers/{uuid.uuid4()}", headers=analyst_headers)
    assert r.status_code == 404


async def test_get_accounts_allowed(client, investigator_headers):
    r = await client.get(f"/api/v1/customers/{uuid.uuid4()}/accounts", headers=investigator_headers)
    assert r.status_code in (200, 404)


async def test_get_holdings_allowed(client, analyst_headers):
    r = await client.get(f"/api/v1/customers/{uuid.uuid4()}/holdings", headers=analyst_headers)
    assert r.status_code in (200, 404)


async def test_get_transactions_allowed(client, analyst_headers):
    r = await client.get(f"/api/v1/customers/{uuid.uuid4()}/transactions", headers=analyst_headers)
    assert r.status_code in (200, 404)


# ── RBAC — risk-incidents ─────────────────────────────────────────────────────

async def test_get_risk_incidents_analyst_allowed(client, analyst_headers):
    r = await client.get(f"/api/v1/customers/{uuid.uuid4()}/risk-incidents", headers=analyst_headers)
    assert r.status_code in (200, 404)


# ── Pagination params ─────────────────────────────────────────────────────────

async def test_list_customers_pagination(client, admin_headers):
    r = await client.get("/api/v1/customers?page=1&size=10", headers=admin_headers)
    assert r.status_code == 200
    meta = r.json()["meta"]
    assert meta["page"] == 1
    assert meta["size"] == 10


async def test_list_customers_size_exceeds_max(client, admin_headers):
    r = await client.get("/api/v1/customers?size=999", headers=admin_headers)
    assert r.status_code == 422
