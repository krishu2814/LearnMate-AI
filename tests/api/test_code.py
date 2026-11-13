import uuid

import pytest
from httpx import AsyncClient


def random_email() -> str:
    return f"code_student_{uuid.uuid4().hex[:8]}@example.com"


async def get_auth_headers(client: AsyncClient, email: str, password: str = "Password123!") -> dict:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Code Tester",
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
async def test_review_code_clean_submission(client: AsyncClient):
    headers = await get_auth_headers(client, random_email())

    clean_code = (
        "def binary_search(arr: list[int], target: int) -> int:\n"
        "    left, right = 0, len(arr) - 1\n"
        "    while left <= right:\n"
        "        mid = (left + right) // 2\n"
        "        if arr[mid] == target:\n"
        "            return mid\n"
        "        elif arr[mid] < target:\n"
        "            left = mid + 1\n"
        "        else:\n"
        "            right = mid - 1\n"
        "    return -1\n"
    )

    resp = await client.post(
        "/api/v1/code/review",
        headers=headers,
        json={
            "title": "Binary Search Implementation",
            "language": "python",
            "source_code": clean_code,
            "problem_description": "Search for a target value in a sorted integer array in O(log n) time.",
        },
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Binary Search Implementation"
    assert data["language"] == "python"
    assert data["score"] >= 80
    assert data["is_passed"] is True
    assert data["time_complexity"] is not None
    assert data["space_complexity"] is not None
    assert len(data["strengths"]) >= 1
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_review_code_with_lesson_context(client: AsyncClient):
    headers = await get_auth_headers(client, random_email())

    courses = (await client.get("/api/v1/courses")).json()
    first_course_id = courses[0]["id"]
    course_detail = (await client.get(f"/api/v1/courses/{first_course_id}")).json()
    lesson_id = course_detail["modules"][0]["lessons"][0]["id"]

    resp = await client.post(
        "/api/v1/code/review",
        headers=headers,
        json={
            "title": "Async Task Runner",
            "language": "python",
            "source_code": "import asyncio\nasync def run(): await asyncio.sleep(0.01)\n",
            "lesson_id": lesson_id,
        },
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["lesson_id"] == lesson_id
    assert data["score"] > 0


@pytest.mark.asyncio
async def test_review_code_invalid_lesson_id(client: AsyncClient):
    headers = await get_auth_headers(client, random_email())

    resp = await client.post(
        "/api/v1/code/review",
        headers=headers,
        json={
            "title": "Invalid Lesson Test",
            "language": "python",
            "source_code": "print('hello')",
            "lesson_id": "non-existent-lesson-id-999",
        },
    )

    assert resp.status_code == 404
    assert "not found" in resp.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_code_submission_retrieval_and_isolation(client: AsyncClient):
    user_a_headers = await get_auth_headers(client, random_email())
    user_b_headers = await get_auth_headers(client, random_email())

    # User A submits code
    sub_resp = await client.post(
        "/api/v1/code/review",
        headers=user_a_headers,
        json={
            "title": "User A Algorithm",
            "language": "python",
            "source_code": "def solve(): return 42\n",
        },
    )
    assert sub_resp.status_code == 201
    submission_id = sub_resp.json()["id"]

    # User A retrieves their own submission -> 200 OK
    get_resp = await client.get(
        f"/api/v1/code/submissions/{submission_id}",
        headers=user_a_headers,
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == submission_id
    assert get_resp.json()["title"] == "User A Algorithm"

    # User B attempts to access User A's submission -> 404 Not Found (Row-level security)
    b_resp = await client.get(
        f"/api/v1/code/submissions/{submission_id}",
        headers=user_b_headers,
    )
    assert b_resp.status_code == 404


@pytest.mark.asyncio
async def test_list_code_submissions_pagination(client: AsyncClient):
    user_headers = await get_auth_headers(client, random_email())

    # Submit 3 code snippets
    for i in range(3):
        await client.post(
            "/api/v1/code/review",
            headers=user_headers,
            json={
                "title": f"Exercise {i}",
                "language": "python",
                "source_code": f"x_{i} = {i}\n",
            },
        )

    # List submissions
    list_resp = await client.get(
        "/api/v1/code/submissions?skip=0&limit=10",
        headers=user_headers,
    )
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert len(items) == 3

    # Check pagination limit
    limited_resp = await client.get(
        "/api/v1/code/submissions?skip=0&limit=2",
        headers=user_headers,
    )
    assert limited_resp.status_code == 200
    assert len(limited_resp.json()) == 2


@pytest.mark.asyncio
async def test_generate_coding_exercise(client: AsyncClient):
    headers = await get_auth_headers(client, random_email())

    resp = await client.post(
        "/api/v1/code/exercises/generate",
        headers=headers,
        json={
            "topic": "LRU Cache Design",
            "difficulty": "advanced",
            "custom_instructions": "Focus on O(1) get and put operations using doubly linked lists",
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert "LRU Cache Design" in data["title"] or "Challenge" in data["title"]
    assert len(data["description"]) > 0
    assert data["difficulty"] == "advanced"
    assert len(data["starter_code"]) > 0
    assert len(data["test_cases"]) >= 2
    assert len(data["hints"]) >= 2


@pytest.mark.asyncio
async def test_code_endpoints_require_authentication(client: AsyncClient):
    # Unauthenticated review
    res_review = await client.post(
        "/api/v1/code/review",
        json={"title": "Test", "language": "python", "source_code": "x=1"},
    )
    assert res_review.status_code == 401

    # Unauthenticated list
    res_list = await client.get("/api/v1/code/submissions")
    assert res_list.status_code == 401

    # Unauthenticated get
    res_get = await client.get("/api/v1/code/submissions/some-id")
    assert res_get.status_code == 401

    # Unauthenticated generate exercise
    res_gen = await client.post(
        "/api/v1/code/exercises/generate",
        json={"topic": "Recursion"},
    )
    assert res_gen.status_code == 401
