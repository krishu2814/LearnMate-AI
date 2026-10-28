import uuid
import pytest
from httpx import AsyncClient


def random_email() -> str:
    return f"student_{uuid.uuid4().hex[:8]}@example.com"


async def create_authenticated_client(client: AsyncClient, email: str, password: str = "Password123!") -> dict:
    """Helper to register, login and return auth headers."""
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Initial Name",
            "skill_level": "beginner",
            "daily_study_minutes": 60,
        },
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_get_my_profile_authenticated(client: AsyncClient):
    email = random_email()
    headers = await create_authenticated_client(client, email)

    response = await client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == email
    assert data["full_name"] == "Initial Name"
    assert data["skill_level"] == "beginner"
    assert data["daily_study_minutes"] == 60


@pytest.mark.asyncio
async def test_get_my_profile_unauthenticated(client: AsyncClient):
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_my_profile_invalid_token(client: AsyncClient):
    response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer invalid.tampered.token"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_my_profile(client: AsyncClient):
    email = random_email()
    headers = await create_authenticated_client(client, email)

    patch_resp = await client.patch(
        "/api/v1/users/me",
        headers=headers,
        json={
            "full_name": "Senior Backend Dev",
            "skill_level": "advanced",
            "daily_study_minutes": 120,
            "timezone": "America/New_York",
        },
    )
    assert patch_resp.status_code == 200
    updated_data = patch_resp.json()
    assert updated_data["full_name"] == "Senior Backend Dev"
    assert updated_data["skill_level"] == "advanced"
    assert updated_data["daily_study_minutes"] == 120
    assert updated_data["timezone"] == "America/New_York"

    # Verify persistence via GET /me
    get_resp = await client.get("/api/v1/users/me", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["full_name"] == "Senior Backend Dev"
