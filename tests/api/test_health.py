import json
from unittest.mock import MagicMock

import pytest
from fastapi import Request
from httpx import AsyncClient

from app.core.exceptions import unhandled_exception_handler


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


@pytest.mark.asyncio
async def test_unhandled_exception_handler():
    mock_request = MagicMock(spec=Request)
    mock_request.headers.get.return_value = "req-test-uuid"
    mock_request.url = "http://testserver/api/v1/unexpected"

    exc = RuntimeError("Unexpected crash")
    response = await unhandled_exception_handler(mock_request, exc)

    assert response.status_code == 500
    body = json.loads(response.body.decode("utf-8"))
    assert body["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert body["error"]["request_id"] == "req-test-uuid"
    assert body["error"]["message"] == "An unexpected server error occurred."
