async def test_products_no_auth(client):
    r = await client.get("/api/v1/products")
    assert r.status_code == 401


async def test_products_authenticated(client, analyst_headers):
    r = await client.get("/api/v1/products", headers=analyst_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "success"
    assert isinstance(body["data"], list)


async def test_products_admin(client, admin_headers):
    r = await client.get("/api/v1/products", headers=admin_headers)
    assert r.status_code == 200


async def test_products_investigator(client, investigator_headers):
    r = await client.get("/api/v1/products", headers=investigator_headers)
    assert r.status_code == 200
