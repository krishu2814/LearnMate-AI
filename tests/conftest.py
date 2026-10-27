from typing import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Test client for FastAPI asynchronous API endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
