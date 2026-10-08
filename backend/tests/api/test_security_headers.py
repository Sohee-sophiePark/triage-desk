"""
Security header tests — verifies every required security header is present.
Zero real API calls — all requests hit the ASGI test client.
"""


async def test_x_frame_options_deny(client):
    r = await client.get("/health")
    assert r.headers.get("x-frame-options") == "DENY"


async def test_x_content_type_options_nosniff(client):
    r = await client.get("/health")
    assert r.headers.get("x-content-type-options") == "nosniff"


async def test_x_xss_protection(client):
    r = await client.get("/health")
    assert "1; mode=block" in r.headers.get("x-xss-protection", "")


async def test_referrer_policy(client):
    r = await client.get("/health")
    assert r.headers.get("referrer-policy") == "strict-origin-when-cross-origin"


async def test_server_header_not_framework_disclosed(client):
    r = await client.get("/health")
    server = r.headers.get("server", "").lower()
    assert server not in ("uvicorn", "fastapi", "python"), (
        f"Framework version disclosed in server header: {server!r}"
    )


async def test_cors_allows_dev_localhost_5173(client):
    r = await client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"


async def test_cors_allows_dev_127_5173(client):
    r = await client.get("/health", headers={"Origin": "http://127.0.0.1:5173"})
    assert "access-control-allow-origin" in r.headers


async def test_cors_rejects_untrusted_origin(client):
    r = await client.get("/health", headers={"Origin": "https://evil.com"})
    acao = r.headers.get("access-control-allow-origin", "")
    assert acao != "https://evil.com", "Untrusted origin must not be reflected in ACAO header"


async def test_cors_credentials_flag_for_dev_origin(client):
    r = await client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert r.headers.get("access-control-allow-credentials") == "true"


async def test_health_body_contains_only_status(client):
    r = await client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"status"}
    assert body["status"] == "ok"


async def test_unauthenticated_api_request_returns_401_not_403(client):
    r = await client.get("/api/v1/customers")
    assert r.status_code == 401, (
        "No-auth request should return 401, not 403/404 — "
        "403 leaks that the endpoint exists to unauthenticated callers"
    )


async def test_options_preflight_returns_200_for_allowed_origin(client):
    r = await client.options(
        "/api/v1/customers",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
        },
    )
    assert r.status_code == 200
