import uuid

import pytest
from httpx import AsyncClient


def random_email() -> str:
    return f"srs_learner_{uuid.uuid4().hex[:8]}@example.com"


async def get_auth_headers(client: AsyncClient, email: str, password: str = "Password123!") -> dict:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "SRS Test Student",
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


async def get_seeded_quiz(client: AsyncClient) -> dict:
    """Fetch the specific seeded quiz for consistent attempt testing."""
    list_resp = await client.get("/api/v1/quizzes")
    for q in list_resp.json():
        if q.get("title") == "Python Concurrency & Async Architecture Quiz":
            detail = await client.get(f"/api/v1/quizzes/{q['id']}")
            return detail.json()
    first_id = list_resp.json()[0]["id"]
    return (await client.get(f"/api/v1/quizzes/{first_id}")).json()


@pytest.mark.asyncio
async def test_quiz_mistake_automatically_populates_srs_queue(client: AsyncClient):
    headers = await get_auth_headers(client, random_email())

    # 1. Fetch seeded quiz and detail
    quiz_detail = await get_seeded_quiz(client)
    quiz_id = quiz_detail["id"]
    questions = quiz_detail["questions"]
    first_q_id = questions[0]["id"]

    # 2. Before submitting attempts, queue should be empty
    queue_before = (await client.get("/api/v1/srs/queue", headers=headers)).json()
    assert queue_before["due_count"] == 0

    # 3. Submit quiz attempt with answers for all questions
    attempt_payload = {
        "time_seconds": 45,
        "answers": [
            {
                "question_id": q["id"],
                "user_answer": "Definitely Incorrect Answer 123",
            }
            for q in questions
        ],
    }
    submit_resp = await client.post(
        f"/api/v1/quizzes/{quiz_id}/attempts",
        headers=headers,
        json=attempt_payload,
    )
    assert submit_resp.status_code == 201

    # 4. Spaced repetition queue must now have these questions scheduled
    queue_after = (await client.get("/api/v1/srs/queue", headers=headers)).json()
    assert queue_after["due_count"] >= 1
    assert queue_after["total_tracked_count"] >= 1
    assert len(queue_after["weak_topics"]) >= 1

    item = next(it for it in queue_after["items"] if it["question_id"] == first_q_id)
    assert item["interval_days"] == 1
    assert item["repetitions"] == 0
    assert item["consecutive_correct"] == 0
    assert item["question"]["id"] == first_q_id
    assert "question" in item["question"]


@pytest.mark.asyncio
async def test_srs_review_submission_lifecycle(client: AsyncClient):
    headers = await get_auth_headers(client, random_email())

    # Get seeded quiz and submit incorrect answers for all questions to populate queue
    quiz_detail = await get_seeded_quiz(client)
    quiz_id = quiz_detail["id"]
    questions = quiz_detail["questions"]

    attempt_resp = await client.post(
        f"/api/v1/quizzes/{quiz_id}/attempts",
        headers=headers,
        json={
            "time_seconds": 30,
            "answers": [
                {"question_id": q["id"], "user_answer": "deliberately wrong"} for q in questions
            ],
        },
    )
    assert attempt_resp.status_code == 201

    queue = (await client.get("/api/v1/srs/queue", headers=headers)).json()
    assert len(queue["items"]) > 0
    item_id = queue["items"][0]["id"]

    # 1. Review with INCORRECT answer
    review_wrong = await client.post(
        f"/api/v1/srs/items/{item_id}/review",
        headers=headers,
        json={"user_answer": "Still Wrong Answer"},
    )
    assert review_wrong.status_code == 200
    wrong_data = review_wrong.json()
    assert wrong_data["is_correct"] is False
    assert wrong_data["new_repetitions"] == 0
    assert wrong_data["new_interval_days"] == 1
    assert len(wrong_data["correct_answer"]) > 0

    # 2. Review with CORRECT answer
    correct_ans = wrong_data["correct_answer"]
    review_correct = await client.post(
        f"/api/v1/srs/items/{item_id}/review",
        headers=headers,
        json={"user_answer": correct_ans},
    )
    assert review_correct.status_code == 200
    correct_data = review_correct.json()
    assert correct_data["is_correct"] is True
    assert correct_data["new_repetitions"] == 1
    assert correct_data["new_interval_days"] == 1

    # 3. Second consecutive correct review advances interval
    review_correct_2 = await client.post(
        f"/api/v1/srs/items/{item_id}/review",
        headers=headers,
        json={"user_answer": correct_ans},
    )
    assert review_correct_2.status_code == 200
    assert review_correct_2.json()["new_repetitions"] == 2
    assert review_correct_2.json()["new_interval_days"] == 3


@pytest.mark.asyncio
async def test_generate_ai_remediation_quiz(client: AsyncClient):
    headers = await get_auth_headers(client, random_email())

    # Populate weak spots
    quiz_detail = await get_seeded_quiz(client)
    quiz_id = quiz_detail["id"]
    questions = quiz_detail["questions"]

    await client.post(
        f"/api/v1/quizzes/{quiz_id}/attempts",
        headers=headers,
        json={
            "time_seconds": 25,
            "answers": [{"question_id": q["id"], "user_answer": "wrong"} for q in questions],
        },
    )

    # Request AI Remediation Quiz
    resp = await client.post(
        "/api/v1/srs/remediation/generate-quiz",
        headers=headers,
        json={"num_questions": 3, "difficulty": "intermediate"},
    )
    assert resp.status_code == 201
    quiz_data = resp.json()

    assert "id" in quiz_data
    assert "Remediation" in quiz_data["title"]
    assert quiz_data["question_count"] == 3
    assert len(quiz_data["questions"]) == 3

    for q in quiz_data["questions"]:
        assert "id" in q
        assert len(q["question"]) > 0


@pytest.mark.asyncio
async def test_srs_row_level_ownership_isolation(client: AsyncClient):
    headers_a = await get_auth_headers(client, random_email())
    headers_b = await get_auth_headers(client, random_email())

    quiz_detail = await get_seeded_quiz(client)
    quiz_id = quiz_detail["id"]
    questions = quiz_detail["questions"]

    # User A incurs a mistake
    att_resp = await client.post(
        f"/api/v1/quizzes/{quiz_id}/attempts",
        headers=headers_a,
        json={
            "time_seconds": 20,
            "answers": [{"question_id": q["id"], "user_answer": "wrong"} for q in questions],
        },
    )
    assert att_resp.status_code == 201

    queue_a = (await client.get("/api/v1/srs/queue", headers=headers_a)).json()
    assert len(queue_a["items"]) > 0
    item_id_a = queue_a["items"][0]["id"]

    # User B tries to review User A's item -> 404
    resp_b = await client.post(
        f"/api/v1/srs/items/{item_id_a}/review",
        headers=headers_b,
        json={"user_answer": "some answer"},
    )
    assert resp_b.status_code == 404


@pytest.mark.asyncio
async def test_srs_unauthenticated_access(client: AsyncClient):
    resp_queue = await client.get("/api/v1/srs/queue")
    assert resp_queue.status_code == 401

    fake_id = str(uuid.uuid4())
    resp_review = await client.post(
        f"/api/v1/srs/items/{fake_id}/review",
        json={"user_answer": "test"},
    )
    assert resp_review.status_code == 401

    resp_remed = await client.post(
        "/api/v1/srs/remediation/generate-quiz",
        json={"num_questions": 3},
    )
    assert resp_remed.status_code == 401
