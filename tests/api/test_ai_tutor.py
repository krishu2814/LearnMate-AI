import uuid

import pytest
from httpx import AsyncClient


def random_email() -> str:
    return f"tutor_user_{uuid.uuid4().hex[:8]}@example.com"


async def get_auth_headers(client: AsyncClient, email: str, password: str = "Password123!") -> dict:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Tutor Student",
            "skill_level": "intermediate",
            "daily_study_minutes": 45,
        },
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_explain_lesson_multi_style(client: AsyncClient):
    headers = await get_auth_headers(client, random_email())

    # Get a real lesson ID from course catalog
    courses = (await client.get("/api/v1/courses")).json()
    first_course_id = courses[0]["id"]
    detail = (await client.get(f"/api/v1/courses/{first_course_id}")).json()
    lesson_id = detail["modules"][0]["lessons"][0]["id"]
    lesson_title = detail["modules"][0]["lessons"][0]["title"]

    # 1. Beginner style
    resp_beg = await client.post(
        f"/api/v1/ai/lessons/{lesson_id}/explain",
        headers=headers,
        json={"style": "beginner"},
    )
    assert resp_beg.status_code == 200
    data_beg = resp_beg.json()
    assert data_beg["lesson_id"] == lesson_id
    assert data_beg["lesson_title"] == lesson_title
    assert data_beg["style"] == "beginner"
    assert len(data_beg["explanation"]) > 0
    assert len(data_beg["key_takeaways"]) >= 2
    assert len(data_beg["suggested_followups"]) >= 1

    # 2. Deep Dive with specific focus question
    resp_dd = await client.post(
        f"/api/v1/ai/lessons/{lesson_id}/explain",
        headers=headers,
        json={
            "style": "deep_dive",
            "focus_question": "What are the common thread-safety failure modes?",
        },
    )
    assert resp_dd.status_code == 200
    data_dd = resp_dd.json()
    assert data_dd["style"] == "deep_dive"
    assert data_dd["code_example"] is not None


@pytest.mark.asyncio
async def test_explain_lesson_not_found(client: AsyncClient):
    headers = await get_auth_headers(client, random_email())
    fake_id = str(uuid.uuid4())

    resp = await client.post(
        f"/api/v1/ai/lessons/{fake_id}/explain",
        headers=headers,
        json={"style": "analogy"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_explain_lesson_unauthorized(client: AsyncClient):
    fake_id = str(uuid.uuid4())
    resp = await client.post(
        f"/api/v1/ai/lessons/{fake_id}/explain",
        json={"style": "practical"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_socratic_tutor_chat(client: AsyncClient):
    headers = await get_auth_headers(client, random_email())

    courses = (await client.get("/api/v1/courses")).json()
    lesson_id = courses[0]["id"]

    # 1. Standalone question
    resp = await client.post(
        "/api/v1/ai/tutor/chat",
        headers=headers,
        json={
            "message": "Why should I use asynchronous connection pooling?",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "reply" in data
    assert len(data["reply"]) > 0
    assert data["socratic_question"] is not None
    assert isinstance(data["suggested_topics"], list)

    # 2. Multi-turn dialogue with history & lesson context
    resp_history = await client.post(
        "/api/v1/ai/tutor/chat",
        headers=headers,
        json={
            "lesson_id": lesson_id,
            "message": "I think it allows multiple queries to be awaited without thread starvation, right?",
            "history": [
                {
                    "role": "user",
                    "content": "Why should I use connection pooling?",
                },
                {
                    "role": "assistant",
                    "content": "Think about what happens when 500 requests open a new TCP handshake simultaneously.",
                },
            ],
        },
    )
    assert resp_history.status_code == 200
    data_hist = resp_history.json()
    assert len(data_hist["reply"]) > 0
    assert data_hist["socratic_question"] is not None


@pytest.mark.asyncio
async def test_socratic_tutor_chat_unauthorized(client: AsyncClient):
    resp = await client.post(
        "/api/v1/ai/tutor/chat",
        json={"message": "Hello tutor!"},
    )
    assert resp.status_code == 401
