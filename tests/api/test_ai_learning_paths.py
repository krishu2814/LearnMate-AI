import uuid

import pytest
from httpx import AsyncClient


def random_email() -> str:
    return f"ai_path_user_{uuid.uuid4().hex[:8]}@example.com"


async def get_auth_headers(client: AsyncClient, email: str, password: str = "Password123!") -> dict:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "AI Path Learner",
            "skill_level": "intermediate",
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
async def test_generate_ai_learning_path(client: AsyncClient):
    headers = await get_auth_headers(client, random_email())

    payload = {
        "goal": "Master Backend Async Engineering & High Throughput APIs",
        "difficulty": "intermediate",
        "total_days": 30,
        "daily_minutes": 60,
        "custom_focus": "FastAPI, async database pooling & security",
    }

    response = await client.post(
        "/api/v1/ai/learning-paths/generate",
        headers=headers,
        json=payload,
    )
    assert response.status_code == 201
    data = response.json()

    assert "learning_path" in data
    assert "ai_overview" in data
    assert "weekly_milestones" in data
    assert "study_tips" in data

    path_data = data["learning_path"]
    assert "id" in path_data
    assert path_data["goal"] == payload["goal"]
    assert path_data["total_days"] == 30
    assert path_data["daily_minutes"] == 60
    assert path_data["status"] == "active"
    assert len(path_data["items"]) >= 1

    # Verify each item has linked lesson metadata
    for item in path_data["items"]:
        assert "id" in item
        assert "lesson_id" in item
        assert len(item["lesson_title"]) > 0
        assert item["position"] >= 1

    # Verify the user can retrieve the created path directly via /api/v1/learning-paths/{id}
    fetch_resp = await client.get(
        f"/api/v1/learning-paths/{path_data['id']}",
        headers=headers,
    )
    assert fetch_resp.status_code == 200
    assert fetch_resp.json()["id"] == path_data["id"]


@pytest.mark.asyncio
async def test_generate_learning_path_with_existing_progress_credit(client: AsyncClient):
    headers = await get_auth_headers(client, random_email())

    # Find the first course and first lesson
    courses_resp = await client.get("/api/v1/courses")
    first_course_id = courses_resp.json()[0]["id"]
    course_detail = (await client.get(f"/api/v1/courses/{first_course_id}")).json()
    first_lesson_id = course_detail["modules"][0]["lessons"][0]["id"]

    # Mark the first lesson as completed by the student beforehand
    prog_resp = await client.put(
        f"/api/v1/lessons/{first_lesson_id}/progress",
        headers=headers,
        json={"status": "completed", "time_spent_seconds": 1200},
    )
    assert prog_resp.status_code == 200

    # Generate an AI learning path
    payload = {
        "goal": "Python Mastery",
        "difficulty": "intermediate",
        "total_days": 14,
        "daily_minutes": 45,
    }
    gen_resp = await client.post(
        "/api/v1/ai/learning-paths/generate",
        headers=headers,
        json=payload,
    )
    assert gen_resp.status_code == 201
    items = gen_resp.json()["learning_path"]["items"]

    # If the first lesson is included in the path, it should be marked as completed
    for it in items:
        if it["lesson_id"] == first_lesson_id:
            assert it["is_completed"] is True


@pytest.mark.asyncio
async def test_generate_ai_learning_path_validation_errors(client: AsyncClient):
    headers = await get_auth_headers(client, random_email())

    # Goal too short
    resp_short = await client.post(
        "/api/v1/ai/learning-paths/generate",
        headers=headers,
        json={"goal": "ab", "daily_minutes": 60},
    )
    assert resp_short.status_code == 422

    # Daily minutes out of bounds (< 15)
    resp_low_time = await client.post(
        "/api/v1/ai/learning-paths/generate",
        headers=headers,
        json={"goal": "Valid Goal Here", "daily_minutes": 10},
    )
    assert resp_low_time.status_code == 422


@pytest.mark.asyncio
async def test_generate_ai_learning_path_unauthorized(client: AsyncClient):
    resp = await client.post(
        "/api/v1/ai/learning-paths/generate",
        json={"goal": "Unauthorized Goal Attempt"},
    )
    assert resp.status_code == 401
