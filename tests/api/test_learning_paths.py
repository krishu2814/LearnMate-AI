import uuid
import pytest
from httpx import AsyncClient


def random_email() -> str:
    return f"student_{uuid.uuid4().hex[:8]}@example.com"


async def get_auth_headers(client: AsyncClient, email: str, password: str = "Password123!") -> dict:
    """Helper to register, login, and obtain authorization headers."""
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Test Learner",
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
async def test_list_courses(client: AsyncClient):
    """Test retrieving published course list."""
    response = await client.get("/api/v1/courses")
    assert response.status_code == 200
    courses = response.json()
    assert isinstance(courses, list)
    assert len(courses) >= 2
    for course in courses:
        assert "id" in course
        assert "title" in course
        assert "difficulty" in course
        assert "subject_tag" in course
        assert course["is_published"] is True


@pytest.mark.asyncio
async def test_get_course_detail(client: AsyncClient):
    """Test retrieving course details with nested modules and lessons."""
    # First get list of courses
    courses_resp = await client.get("/api/v1/courses")
    course_id = courses_resp.json()[0]["id"]

    response = await client.get(f"/api/v1/courses/{course_id}")
    assert response.status_code == 200
    detail = response.json()
    assert detail["id"] == course_id
    assert "modules" in detail
    assert len(detail["modules"]) >= 1

    first_module = detail["modules"][0]
    assert "lessons" in first_module
    assert len(first_module["lessons"]) >= 1
    assert "estimated_minutes" in first_module["lessons"][0]


@pytest.mark.asyncio
async def test_get_course_detail_not_found(client: AsyncClient):
    """Test requesting a non-existent course returns 404."""
    response = await client.get(f"/api/v1/courses/{uuid.uuid4()}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_create_and_get_learning_path(client: AsyncClient):
    """Test creating a personalized learning path with lessons and retrieving details."""
    headers = await get_auth_headers(client, random_email())

    # Get course lessons to populate the path
    courses_resp = await client.get("/api/v1/courses")
    course_id = courses_resp.json()[0]["id"]
    course_detail = (await client.get(f"/api/v1/courses/{course_id}")).json()
    lesson_ids = [l["id"] for m in course_detail["modules"] for l in m["lessons"]][:3]

    create_payload = {
        "title": "My Python Mastery Path",
        "goal": "Master backend systems in 30 days",
        "total_days": 30,
        "daily_minutes": 60,
        "lesson_ids": lesson_ids,
    }

    create_resp = await client.post("/api/v1/learning-paths", json=create_payload, headers=headers)
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["title"] == "My Python Mastery Path"
    assert created["goal"] == "Master backend systems in 30 days"
    assert created["total_items"] == len(lesson_ids)
    assert created["completed_items"] == 0
    assert created["completion_pct"] == 0.0
    assert len(created["items"]) == len(lesson_ids)
    assert created["items"][0]["lesson_title"] != ""
    assert created["items"][0]["position"] == 1

    # Fetch created learning path by ID
    path_id = created["id"]
    get_resp = await client.get(f"/api/v1/learning-paths/{path_id}", headers=headers)
    assert get_resp.status_code == 200
    fetched = get_resp.json()
    assert fetched["id"] == path_id
    assert fetched["title"] == "My Python Mastery Path"


@pytest.mark.asyncio
async def test_create_learning_path_with_invalid_lesson(client: AsyncClient):
    """Test that creating a path with non-existent lesson IDs raises 404."""
    headers = await get_auth_headers(client, random_email())

    create_payload = {
        "title": "Invalid Path",
        "goal": "Test non-existent lesson",
        "total_days": 15,
        "daily_minutes": 45,
        "lesson_ids": [str(uuid.uuid4())],
    }

    response = await client.post("/api/v1/learning-paths", json=create_payload, headers=headers)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_row_level_ownership_isolation(client: AsyncClient):
    """
    CRITICAL SECURITY & MULTI-TENANCY TEST:
    Verify that User B cannot view, modify, or delete User A's learning path.
    Accessing another user's path must return 404 NOT_FOUND.
    """
    user_a_headers = await get_auth_headers(client, random_email())
    user_b_headers = await get_auth_headers(client, random_email())

    # User A creates a path
    create_payload = {
        "title": "User A Private Learning Path",
        "goal": "Private goal for User A",
        "total_days": 20,
        "daily_minutes": 45,
        "lesson_ids": [],
    }
    user_a_resp = await client.post("/api/v1/learning-paths", json=create_payload, headers=user_a_headers)
    assert user_a_resp.status_code == 201
    user_a_path_id = user_a_resp.json()["id"]

    # 1. User B tries to GET User A's path -> 404 NOT FOUND
    resp = await client.get(f"/api/v1/learning-paths/{user_a_path_id}", headers=user_b_headers)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"

    # 2. User B tries to PATCH User A's path -> 404 NOT FOUND
    resp = await client.patch(
        f"/api/v1/learning-paths/{user_a_path_id}",
        json={"title": "Hacked Path Title"},
        headers=user_b_headers,
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"

    # 3. User B tries to DELETE User A's path -> 404 NOT FOUND
    resp = await client.delete(f"/api/v1/learning-paths/{user_a_path_id}", headers=user_b_headers)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"

    # 4. User B lists learning paths -> User A's path is NOT present
    list_resp = await client.get("/api/v1/learning-paths", headers=user_b_headers)
    assert list_resp.status_code == 200
    b_path_ids = [p["id"] for p in list_resp.json()]
    assert user_a_path_id not in b_path_ids

    # 5. User A verifies their path was not modified or deleted
    user_a_verify = await client.get(f"/api/v1/learning-paths/{user_a_path_id}", headers=user_a_headers)
    assert user_a_verify.status_code == 200
    assert user_a_verify.json()["title"] == "User A Private Learning Path"


@pytest.mark.asyncio
async def test_update_learning_path(client: AsyncClient):
    """Test updating learning path properties."""
    headers = await get_auth_headers(client, random_email())

    create_resp = await client.post(
        "/api/v1/learning-paths",
        json={"title": "Initial Title", "goal": "Initial Goal", "total_days": 30, "daily_minutes": 60},
        headers=headers,
    )
    path_id = create_resp.json()["id"]

    patch_resp = await client.patch(
        f"/api/v1/learning-paths/{path_id}",
        json={
            "title": "Updated Title",
            "goal": "Updated Goal",
            "total_days": 45,
            "daily_minutes": 90,
            "status": "completed",
        },
        headers=headers,
    )
    assert patch_resp.status_code == 200
    updated = patch_resp.json()
    assert updated["title"] == "Updated Title"
    assert updated["goal"] == "Updated Goal"
    assert updated["total_days"] == 45
    assert updated["daily_minutes"] == 90
    assert updated["status"] == "completed"


@pytest.mark.asyncio
async def test_delete_learning_path(client: AsyncClient):
    """Test deleting a learning path."""
    headers = await get_auth_headers(client, random_email())

    create_resp = await client.post(
        "/api/v1/learning-paths",
        json={"title": "Path To Delete", "goal": "Testing deletion", "total_days": 10, "daily_minutes": 30},
        headers=headers,
    )
    path_id = create_resp.json()["id"]

    # Delete
    del_resp = await client.delete(f"/api/v1/learning-paths/{path_id}", headers=headers)
    assert del_resp.status_code == 204

    # Verify 404 after deletion
    get_resp = await client.get(f"/api/v1/learning-paths/{path_id}", headers=headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_unauthenticated_access(client: AsyncClient):
    """Test that unauthorized requests are rejected."""
    resp = await client.get("/api/v1/learning-paths")
    assert resp.status_code == 401

    resp = await client.post("/api/v1/learning-paths", json={"title": "x", "goal": "y"})
    assert resp.status_code == 401
