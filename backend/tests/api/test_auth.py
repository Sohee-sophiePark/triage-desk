from tests.conftest import TEST_PASSWORD, WRONG_PASSWORD


async def test_login_success(client, admin_user):
    r = await client.post(
        "/api/v1/auth/login",
        data={"username": admin_user.email, "password": TEST_PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


async def test_login_wrong_password(client, admin_user):
    r = await client.post(
        "/api/v1/auth/login",
        data={"username": admin_user.email, "password": WRONG_PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 400


async def test_login_unknown_user(client):
    r = await client.post(
        "/api/v1/auth/login",
        data={"username": "nobody@test.com", "password": WRONG_PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 400


async def test_test_token_valid(client, admin_headers):
    r = await client.post("/api/v1/auth/test-token", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["email"] is not None


async def test_test_token_no_auth(client):
    r = await client.post("/api/v1/auth/test-token")
    assert r.status_code == 401


async def test_test_token_bad_token(client):
    r = await client.post(
        "/api/v1/auth/test-token",
        headers={"Authorization": "Bearer notavalidtoken"},
    )
    assert r.status_code == 401
