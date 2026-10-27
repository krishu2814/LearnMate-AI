import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "LearnMate AI" in data["message"]
    assert data["health"] == "/health/live"
    assert "X-Request-ID" in response.headers
    assert "X-Process-Time" in response.headers


@pytest.mark.asyncio
async def test_liveness_endpoint(client: AsyncClient):
    response = await client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "LearnMate AI"
    assert data["environment"] == "development"


@pytest.mark.asyncio
async def test_readiness_endpoint_structure(client: AsyncClient):
    # Depending on whether MySQL & Redis are running, status will be 200 or 503
    response = await client.get("/health/ready")
    assert response.status_code in [200, 503]
    data = response.json()
    assert "status" in data
    assert "checks" in data
    assert "database" in data["checks"]
    assert "redis" in data["checks"]
