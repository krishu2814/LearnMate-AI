import uuid

import pytest
from httpx import AsyncClient


def random_email() -> str:
    return f"ai_student_{uuid.uuid4().hex[:8]}@example.com"


async def get_auth_headers(client: AsyncClient, email: str, password: str = "Password123!") -> dict:
    """Helper to register, login, and obtain authorization headers."""
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "AI Test Learner",
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
async def test_generate_quiz_from_topic(client: AsyncClient):
    headers = await get_auth_headers(client, random_email())

    response = await client.post(
        "/api/v1/ai/quizzes/generate",
        headers=headers,
        json={
            "topic": "Python Asyncio & Concurrency",
            "difficulty": "intermediate",
            "num_questions": 3,
            "custom_instructions": "Focus on event loop mechanics",
        },
    )
    assert response.status_code == 201
    data = response.json()

    assert "id" in data
    assert data["topic"] == "Python Asyncio & Concurrency"
    assert data["difficulty"] == "intermediate"
    assert data["question_count"] == 3
    assert len(data["questions"]) == 3

    for q in data["questions"]:
        assert "id" in q
        assert "question" in q
        assert q["question_type"] in ["mcq", "true_false"]
        assert len(q["options"]) >= 2
        assert q["position"] >= 1


@pytest.mark.asyncio
async def test_generate_quiz_grounded_in_lesson(client: AsyncClient):
    headers = await get_auth_headers(client, random_email())

    # Fetch existing courses to obtain a valid lesson ID
    courses_resp = await client.get("/api/v1/courses")
    assert courses_resp.status_code == 200
    course_id = courses_resp.json()[0]["id"]

    course_detail_resp = await client.get(f"/api/v1/courses/{course_id}")
    lesson_id = course_detail_resp.json()["modules"][0]["lessons"][0]["id"]

    response = await client.post(
        "/api/v1/ai/quizzes/generate",
        headers=headers,
        json={
            "topic": "FastAPI Validation",
            "difficulty": "beginner",
            "num_questions": 2,
            "lesson_id": lesson_id,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["lesson_id"] == lesson_id
    assert len(data["questions"]) == 2


@pytest.mark.asyncio
async def test_generate_quiz_invalid_lesson_id(client: AsyncClient):
    headers = await get_auth_headers(client, random_email())

    response = await client.post(
        "/api/v1/ai/quizzes/generate",
        headers=headers,
        json={
            "topic": "Distributed Systems",
            "lesson_id": "nonexistent-lesson-uuid-99999",
            "num_questions": 3,
        },
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_generate_quiz_unauthenticated(client: AsyncClient):
    response = await client.post(
        "/api/v1/ai/quizzes/generate",
        json={"topic": "Docker Containers", "num_questions": 2},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_evaluate_answer_flow(client: AsyncClient):
    headers = await get_auth_headers(client, random_email())

    # First generate a quiz to obtain valid question IDs
    quiz_resp = await client.post(
        "/api/v1/ai/quizzes/generate",
        headers=headers,
        json={
            "topic": "Relational Databases",
            "difficulty": "beginner",
            "num_questions": 2,
        },
    )
    assert quiz_resp.status_code == 201
    question = quiz_resp.json()["questions"][0]

    # Evaluate an answer
    eval_resp = await client.post(
        "/api/v1/ai/quizzes/evaluate-answer",
        headers=headers,
        json={
            "question_id": question["id"],
            "user_answer": question["options"][0],
        },
    )
    assert eval_resp.status_code == 200
    eval_data = eval_resp.json()

    assert eval_data["question_id"] == question["id"]
    assert isinstance(eval_data["is_correct"], bool)
    assert 0.0 <= eval_data["ai_confidence"] <= 1.0
    assert len(eval_data["ai_feedback"]) > 0


@pytest.mark.asyncio
async def test_evaluate_answer_nonexistent_question(client: AsyncClient):
    headers = await get_auth_headers(client, random_email())

    eval_resp = await client.post(
        "/api/v1/ai/quizzes/evaluate-answer",
        headers=headers,
        json={
            "question_id": "nonexistent-question-uuid",
            "user_answer": "My answer",
        },
    )
    assert eval_resp.status_code == 404
    assert eval_resp.json()["error"]["code"] == "NOT_FOUND"
