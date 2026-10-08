async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


async def test_docs_available(client):
    r = await client.get("/docs")
    assert r.status_code == 200
