"""
Tests for admin-only user management API.
Covers: list, create, update; RBAC enforcement; 409 on duplicate email;
password policy enforcement (SC-01).
"""
import uuid

import pytest

from tests.conftest import TEST_PASSWORD

# ── List users ────────────────────────────────────────────────────────────────

async def test_list_users_admin(client, admin_headers):
    r = await client.get("/api/v1/users", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) > 0
    # Each item has the expected fields
    item = data[0]
    assert "id" in item
    assert "email" in item
    assert "role" in item
    assert "is_active" in item


async def test_list_users_forbidden_for_analyst(client, analyst_headers):
    r = await client.get("/api/v1/users", headers=analyst_headers)
    assert r.status_code == 403


async def test_list_users_forbidden_for_investigator(client, investigator_headers):
    r = await client.get("/api/v1/users", headers=investigator_headers)
    assert r.status_code == 403


async def test_list_users_requires_auth(client):
    r = await client.get("/api/v1/users")
    assert r.status_code == 401


# ── Create user ───────────────────────────────────────────────────────────────

async def test_create_user_admin(client, admin_headers):
    unique = uuid.uuid4().hex[:8]
    payload = {
        "email": f"newuser-{unique}@example.com",
        "password": TEST_PASSWORD,
        "full_name": "New Test User",
        "role": "risk_analyst",
    }
    r = await client.post("/api/v1/users", json=payload, headers=admin_headers)
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == payload["email"]
    assert body["role"] == "risk_analyst"
    assert body["is_active"] is True
    assert "id" in body
    # Password must NOT be in the response
    assert "password" not in body
    assert "hashed_password" not in body


async def test_create_user_duplicate_email(client, admin_headers):
    unique = uuid.uuid4().hex[:8]
    payload = {
        "email": f"dup-{unique}@example.com",
        "password": TEST_PASSWORD,
        "full_name": "First",
        "role": "admin",
    }
    r1 = await client.post("/api/v1/users", json=payload, headers=admin_headers)
    assert r1.status_code == 201

    r2 = await client.post("/api/v1/users", json=payload, headers=admin_headers)
    assert r2.status_code == 409


async def test_create_user_forbidden_for_analyst(client, analyst_headers):
    payload = {
        "email": "nobody@example.com",
        "password": TEST_PASSWORD,
        "full_name": "Nobody",
        "role": "admin",
    }
    r = await client.post("/api/v1/users", json=payload, headers=analyst_headers)
    assert r.status_code == 403


async def test_create_user_missing_fields(client, admin_headers):
    r = await client.post("/api/v1/users", json={"email": "incomplete@example.com"}, headers=admin_headers)
    assert r.status_code == 422


# ── Update user ───────────────────────────────────────────────────────────────

@pytest.fixture
async def created_user_id(client, admin_headers):
    unique = uuid.uuid4().hex[:8]
    payload = {
        "email": f"patch-target-{unique}@example.com",
        "password": TEST_PASSWORD,
        "full_name": "Patch Target",
        "role": "risk_analyst",
    }
    r = await client.post("/api/v1/users", json=payload, headers=admin_headers)
    assert r.status_code == 201
    return r.json()["id"]


async def test_update_user_role(client, admin_headers, created_user_id):
    r = await client.patch(
        f"/api/v1/users/{created_user_id}",
        json={"role": "compliance_officer"},
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["role"] == "compliance_officer"


async def test_update_user_deactivate(client, admin_headers, created_user_id):
    r = await client.patch(
        f"/api/v1/users/{created_user_id}",
        json={"is_active": False},
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["is_active"] is False


async def test_update_user_not_found(client, admin_headers):
    r = await client.patch(
        f"/api/v1/users/{uuid.uuid4()}",
        json={"full_name": "Ghost"},
        headers=admin_headers,
    )
    assert r.status_code == 404


async def test_update_user_forbidden_for_analyst(client, analyst_headers, created_user_id):
    r = await client.patch(
        f"/api/v1/users/{created_user_id}",
        json={"full_name": "Hacker"},
        headers=analyst_headers,
    )
    assert r.status_code == 403


# ── Password policy (SC-01) ───────────────────────────────────────────────────

async def test_create_user_short_password_rejected(client, admin_headers):
    """Passwords shorter than 12 characters must be rejected with 422."""
    r = await client.post(
        "/api/v1/users",
        json={
            "email": "short-pw@example.com",
            "password": "Short1!",
            "full_name": "Bad",
            "role": "risk_analyst",
        },
        headers=admin_headers,
    )
    assert r.status_code == 422


async def test_create_user_no_uppercase_rejected(client, admin_headers):
    r = await client.post(
        "/api/v1/users",
        json={
            "email": "noup@example.com",
            "password": "alllowercase1!",
            "full_name": "Bad",
            "role": "risk_analyst",
        },
        headers=admin_headers,
    )
    assert r.status_code == 422


async def test_create_user_no_digit_rejected(client, admin_headers):
    r = await client.post(
        "/api/v1/users",
        json={
            "email": "nodigit@example.com",
            "password": "NoDigitHere!!X",
            "full_name": "Bad",
            "role": "risk_analyst",
        },
        headers=admin_headers,
    )
    assert r.status_code == 422


async def test_create_user_no_special_char_rejected(client, admin_headers):
    r = await client.post(
        "/api/v1/users",
        json={
            "email": "nospecial@example.com",
            "password": "NoSpecialChar1A",
            "full_name": "Bad",
            "role": "risk_analyst",
        },
        headers=admin_headers,
    )
    assert r.status_code == 422


async def test_create_user_valid_complex_password(client, admin_headers):
    unique = uuid.uuid4().hex[:8]
    r = await client.post(
        "/api/v1/users",
        json={
            "email": f"goodpw-{unique}@example.com",
            "password": TEST_PASSWORD,
            "full_name": "Good",
            "role": "risk_analyst",
        },
        headers=admin_headers,
    )
    assert r.status_code == 201


async def test_update_user_weak_password_rejected(client, admin_headers, created_user_id):
    r = await client.patch(
        f"/api/v1/users/{created_user_id}",
        json={"password": "weakpass"},
        headers=admin_headers,
    )
    assert r.status_code == 422
