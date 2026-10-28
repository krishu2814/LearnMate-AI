import uuid
import pytest
from httpx import AsyncClient


def random_email() -> str:
    return f"student_{uuid.uuid4().hex[:8]}@example.com"


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    email = random_email()
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPassword123!",
            "full_name": "LearnMate Student",
            "skill_level": "beginner",
            "daily_study_minutes": 45,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == email
    assert data["full_name"] == "LearnMate Student"
    assert data["skill_level"] == "beginner"
    assert data["daily_study_minutes"] == 45
    assert "password" not in data
    assert "id" in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    email = random_email()
    payload = {
        "email": email,
        "password": "StrongPassword123!",
    }
    first_resp = await client.post("/api/v1/auth/register", json=payload)
    assert first_resp.status_code == 201

    second_resp = await client.post("/api/v1/auth/register", json=payload)
    assert second_resp.status_code == 409
    error = second_resp.json()["error"]
    assert error["code"] == "ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_register_weak_password_validation(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": random_email(),
            "password": "short",  # < 8 characters
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    email = random_email()
    password = "MySecurePassword123!"

    # Register first
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert reg_resp.status_code == 201

    # Login
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_resp.status_code == 200
    data = login_resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    email = random_email()
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "CorrectPassword123!"},
    )

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "WrongPassword123!"},
    )
    assert login_resp.status_code == 401
    assert login_resp.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent_ghost@example.com", "password": "Password123!"},
    )
    assert login_resp.status_code == 401
    assert login_resp.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_refresh_token_rotation(client: AsyncClient):
    email = random_email()
    password = "RotatePassword123!"

    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    initial_tokens = login_resp.json()
    token_1 = initial_tokens["refresh_token"]

    # Rotate refresh token
    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": token_1},
    )
    assert refresh_resp.status_code == 200
    rotated_tokens = refresh_resp.json()
    token_2 = rotated_tokens["refresh_token"]

    assert token_2 != token_1
    assert "access_token" in rotated_tokens


@pytest.mark.asyncio
async def test_token_reuse_detection(client: AsyncClient):
    """
    Simulate token theft: an old rotated token is presented again.
    The system must detect token reuse and revoke all sessions for that user.
    """
    email = random_email()
    password = "ReuseTestPassword123!"

    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    initial_token = login_resp.json()["refresh_token"]

    # Legitimate user rotates token -> gets token_2
    rotate_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": initial_token},
    )
    assert rotate_resp.status_code == 200
    token_2 = rotate_resp.json()["refresh_token"]

    # Attacker tries to use the already-revoked initial_token!
    attacker_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": initial_token},
    )
    assert attacker_resp.status_code == 401
    assert "reuse detected" in attacker_resp.json()["error"]["message"].lower()

    # Legitimate token_2 should now ALSO be revoked as a security precaution
    legitimate_retry = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": token_2},
    )
    assert legitimate_retry.status_code == 401


@pytest.mark.asyncio
async def test_logout_revocation(client: AsyncClient):
    email = random_email()
    password = "LogoutPassword123!"

    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    refresh_token = login_resp.json()["refresh_token"]

    # Logout
    logout_resp = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert logout_resp.status_code == 204

    # Using the logged-out token to refresh must now fail
    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_resp.status_code == 401
