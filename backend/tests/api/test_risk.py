async def test_risk_incidents_no_auth(client):
    r = await client.get("/api/v1/risk/incidents")
    assert r.status_code == 401


async def test_risk_incidents_admin(client, admin_headers):
    r = await client.get("/api/v1/risk/incidents", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "success"
    assert isinstance(body["data"], list)


async def test_risk_incidents_analyst(client, analyst_headers):
    r = await client.get("/api/v1/risk/incidents", headers=analyst_headers)
    assert r.status_code == 200


async def test_risk_incidents_investigator_forbidden(client, investigator_headers):
    """Risk incidents list is gated to admin + risk_analyst only."""
    r = await client.get("/api/v1/risk/incidents", headers=investigator_headers)
    assert r.status_code == 403
