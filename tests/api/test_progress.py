import uuid
import pytest
from httpx import AsyncClient


def random_email() -> str:
    return f"student_{uuid.uuid4().hex[:8]}@example.com"


async def get_auth_headers(client: AsyncClient, email: str, password: str = "Password123!") -> dict:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Progress Tester",
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


async def get_seed_lesson_ids(client: AsyncClient) -> list[str]:
    courses_resp = await client.get("/api/v1/courses")
    first_course_id = courses_resp.json()[0]["id"]
    detail_resp = await client.get(f"/api/v1/courses/{first_course_id}")
    modules = detail_resp.json()["modules"]
    return [l["id"] for m in modules for l in m["lessons"]]


@pytest.mark.asyncio
async def test_get_lesson_detail(client: AsyncClient):
    lesson_ids = await get_seed_lesson_ids(client)
    assert len(lesson_ids) > 0
    lesson_id = lesson_ids[0]

    resp = await client.get(f"/api/v1/lessons/{lesson_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == lesson_id
    assert "title" in data
    assert "content" in data
    assert len(data["content"]) > 0
    assert "estimated_minutes" in data
    assert data["estimated_minutes"] > 0
    assert "module_id" in data


@pytest.mark.asyncio
async def test_get_lesson_detail_not_found(client: AsyncClient):
    resp = await client.get(f"/api/v1/lessons/{uuid.uuid4()}")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_update_lesson_progress_lifecycle(client: AsyncClient):
    headers = await get_auth_headers(client, random_email())
    lesson_ids = await get_seed_lesson_ids(client)
    lesson_id = lesson_ids[0]

    # 1. Start lesson (in_progress)
    resp = await client.put(
        f"/api/v1/lessons/{lesson_id}/progress",
        json={"status": "in_progress", "time_spent_seconds": 300},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "in_progress"
    assert data["time_spent_seconds"] == 300
    assert data["started_at"] is not None
    assert data["completed_at"] is None

    # 2. Add time and mark completed
    resp = await client.put(
        f"/api/v1/lessons/{lesson_id}/progress",
        json={"status": "completed", "additional_seconds": 120},
        headers=headers,
    )
    assert resp.status_code == 200
    completed_data = resp.json()
    assert completed_data["status"] == "completed"
    assert completed_data["time_spent_seconds"] == 420
    assert completed_data["completed_at"] is not None


@pytest.mark.asyncio
async def test_lesson_completion_syncs_learning_path_items(client: AsyncClient):
    """
    Test that completing a lesson automatically synchronizes the is_completed
    flag on any active learning paths containing that lesson.
    """
    headers = await get_auth_headers(client, random_email())
    lesson_ids = await get_seed_lesson_ids(client)
    target_lesson = lesson_ids[0]
    other_lesson = lesson_ids[1]

    # Create learning path with 2 lessons
    path_resp = await client.post(
        "/api/v1/learning-paths",
        json={
            "title": "Sync Test Path",
            "goal": "Verify progress synchronization",
            "total_days": 10,
            "daily_minutes": 30,
            "lesson_ids": [target_lesson, other_lesson],
        },
        headers=headers,
    )
    assert path_resp.status_code == 201
    path_id = path_resp.json()["id"]
    assert path_resp.json()["completed_items"] == 0
    assert path_resp.json()["completion_pct"] == 0.0

    # Complete target_lesson
    progress_resp = await client.put(
        f"/api/v1/lessons/{target_lesson}/progress",
        json={"status": "completed", "time_spent_seconds": 600},
        headers=headers,
    )
    assert progress_resp.status_code == 200

    # Fetch learning path and verify sync
    updated_path_resp = await client.get(f"/api/v1/learning-paths/{path_id}", headers=headers)
    assert updated_path_resp.status_code == 200
    updated_path = updated_path_resp.json()
    assert updated_path["completed_items"] == 1
    assert updated_path["completion_pct"] == 50.0

    items_by_lesson = {i["lesson_id"]: i["is_completed"] for i in updated_path["items"]}
    assert items_by_lesson[target_lesson] is True
    assert items_by_lesson[other_lesson] is False


@pytest.mark.asyncio
async def test_dashboard_progress(client: AsyncClient):
    headers = await get_auth_headers(client, random_email())
    lesson_ids = await get_seed_lesson_ids(client)

    # Complete 2 lessons
    await client.put(
        f"/api/v1/lessons/{lesson_ids[0]}/progress",
        json={"status": "completed", "time_spent_seconds": 600},
        headers=headers,
    )
    await client.put(
        f"/api/v1/lessons/{lesson_ids[1]}/progress",
        json={"status": "completed", "time_spent_seconds": 900},
        headers=headers,
    )

    # Get progress dashboard
    resp = await client.get("/api/v1/progress", headers=headers)
    assert resp.status_code == 200
    dashboard = resp.json()

    assert dashboard["total_lessons_available"] >= 11
    assert dashboard["completed_lessons"] >= 2
    assert dashboard["total_time_spent_seconds"] >= 1500
    assert dashboard["total_time_spent_minutes"] >= 25
    assert dashboard["overall_completion_pct"] > 0.0

    assert len(dashboard["courses_progress"]) >= 2
    course_summary = dashboard["courses_progress"][0]
    assert course_summary["total_lessons"] > 0
    assert "completion_pct" in course_summary


@pytest.mark.asyncio
async def test_progress_user_isolation(client: AsyncClient):
    """Verify that User B does not see User A's progress."""
    user_a_headers = await get_auth_headers(client, random_email())
    user_b_headers = await get_auth_headers(client, random_email())
    lesson_ids = await get_seed_lesson_ids(client)

    # User A completes a lesson
    await client.put(
        f"/api/v1/lessons/{lesson_ids[0]}/progress",
        json={"status": "completed", "time_spent_seconds": 1200},
        headers=user_a_headers,
    )

    # User B checks progress -> 0 completed
    resp = await client.get("/api/v1/progress", headers=user_b_headers)
    assert resp.status_code == 200
    user_b_dashboard = resp.json()
    assert user_b_dashboard["completed_lessons"] == 0
    assert user_b_dashboard["total_time_spent_seconds"] == 0
    assert user_b_dashboard["overall_completion_pct"] == 0.0


@pytest.mark.asyncio
async def test_unauthenticated_progress_access(client: AsyncClient):
    lesson_ids = await get_seed_lesson_ids(client)

    resp = await client.put(
        f"/api/v1/lessons/{lesson_ids[0]}/progress",
        json={"status": "completed"},
    )
    assert resp.status_code == 401

    resp = await client.get("/api/v1/progress")
    assert resp.status_code == 401
