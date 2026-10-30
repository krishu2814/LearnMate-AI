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
            "full_name": "Quiz Tester",
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
async def test_list_quizzes(client: AsyncClient):
    resp = await client.get("/api/v1/quizzes")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1

    first_quiz = data[0]
    assert "id" in first_quiz
    assert "title" in first_quiz
    assert "topic" in first_quiz
    assert "difficulty" in first_quiz
    assert "question_count" in first_quiz


@pytest.mark.asyncio
async def test_list_quizzes_filtering(client: AsyncClient):
    # Filter by topic
    resp = await client.get("/api/v1/quizzes?topic=Backend")
    assert resp.status_code == 200
    for q in resp.json():
        assert "Backend" in q["topic"]

    # Filter by difficulty
    resp_diff = await client.get("/api/v1/quizzes?difficulty=intermediate")
    assert resp_diff.status_code == 200
    for q in resp_diff.json():
        assert q["difficulty"] == "intermediate"


@pytest.mark.asyncio
async def test_get_quiz_detail_masks_correct_answers(client: AsyncClient):
    list_resp = await client.get("/api/v1/quizzes")
    quiz_id = list_resp.json()[0]["id"]

    resp = await client.get(f"/api/v1/quizzes/{quiz_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == quiz_id
    assert "questions" in data
    assert len(data["questions"]) >= 1

    for question in data["questions"]:
        assert "id" in question
        assert "question" in question
        assert "question_type" in question
        assert "options" in question
        # Crucial security assertion: answers must not be leaked to the client taking the quiz
        assert "correct_answer" not in question
        assert "explanation" not in question


@pytest.mark.asyncio
async def test_get_quiz_detail_not_found(client: AsyncClient):
    resp = await client.get(f"/api/v1/quizzes/{uuid.uuid4()}")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_submit_quiz_attempt_scoring(client: AsyncClient):
    email = random_email()
    headers = await get_auth_headers(client, email)

    list_resp = await client.get("/api/v1/quizzes")
    quiz_id = list_resp.json()[0]["id"]
    quiz_detail = (await client.get(f"/api/v1/quizzes/{quiz_id}")).json()
    questions = quiz_detail["questions"]
    assert len(questions) == 3

    # Submit 3 answers: 2 correct, 1 wrong
    # Question 1: "async def" (correct)
    # Question 2: "False" (correct)
    # Question 3: "Query" (wrong, correct is "Depends")
    payload = {
        "answers": [
            {"question_id": questions[0]["id"], "user_answer": "async def"},
            {"question_id": questions[1]["id"], "user_answer": "False"},
            {"question_id": questions[2]["id"], "user_answer": "Query"},
        ],
        "time_seconds": 45,
        "is_exam_mode": False,
    }

    submit_resp = await client.post(
        f"/api/v1/quizzes/{quiz_id}/attempts",
        json=payload,
        headers=headers,
    )
    assert submit_resp.status_code == 201
    result = submit_resp.json()
    assert result["quiz_id"] == quiz_id
    assert result["total_questions"] == 3
    assert result["correct_count"] == 2
    assert result["score"] == 66.67
    assert result["time_seconds"] == 45
    assert len(result["answers"]) == 3

    # Now verify answers include explanations and correct answer keys after submission
    ans_q1 = next(a for a in result["answers"] if a["question_id"] == questions[0]["id"])
    assert ans_q1["is_correct"] is True
    assert ans_q1["correct_answer"] == "async def"
    assert "explanation" in ans_q1

    ans_q3 = next(a for a in result["answers"] if a["question_id"] == questions[2]["id"])
    assert ans_q3["is_correct"] is False
    assert ans_q3["correct_answer"] == "Depends"


@pytest.mark.asyncio
async def test_submit_quiz_attempt_perfect_score(client: AsyncClient):
    email = random_email()
    headers = await get_auth_headers(client, email)

    list_resp = await client.get("/api/v1/quizzes")
    quiz_id = list_resp.json()[0]["id"]
    quiz_detail = (await client.get(f"/api/v1/quizzes/{quiz_id}")).json()
    questions = quiz_detail["questions"]

    payload = {
        "answers": [
            {"question_id": questions[0]["id"], "user_answer": "async def"},
            {"question_id": questions[1]["id"], "user_answer": "false"},  # case-insensitive check
            {"question_id": questions[2]["id"], "user_answer": "Depends"},
        ],
        "time_seconds": 60,
    }

    submit_resp = await client.post(
        f"/api/v1/quizzes/{quiz_id}/attempts",
        json=payload,
        headers=headers,
    )
    assert submit_resp.status_code == 201
    result = submit_resp.json()
    assert result["correct_count"] == 3
    assert result["score"] == 100.0


@pytest.mark.asyncio
async def test_submit_quiz_attempt_duplicate_question_validation(client: AsyncClient):
    email = random_email()
    headers = await get_auth_headers(client, email)

    list_resp = await client.get("/api/v1/quizzes")
    quiz_id = list_resp.json()[0]["id"]
    quiz_detail = (await client.get(f"/api/v1/quizzes/{quiz_id}")).json()
    q_id = quiz_detail["questions"][0]["id"]

    payload = {
        "answers": [
            {"question_id": q_id, "user_answer": "async def"},
            {"question_id": q_id, "user_answer": "def"},
        ]
    }
    resp = await client.post(
        f"/api/v1/quizzes/{quiz_id}/attempts",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "BAD_REQUEST"


@pytest.mark.asyncio
async def test_submit_quiz_attempt_invalid_question_id(client: AsyncClient):
    email = random_email()
    headers = await get_auth_headers(client, email)

    list_resp = await client.get("/api/v1/quizzes")
    quiz_id = list_resp.json()[0]["id"]

    payload = {
        "answers": [
            {"question_id": str(uuid.uuid4()), "user_answer": "option"}
        ]
    }
    resp = await client.post(
        f"/api/v1/quizzes/{quiz_id}/attempts",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "BAD_REQUEST"


@pytest.mark.asyncio
async def test_quiz_attempt_history_and_user_isolation(client: AsyncClient):
    user_a_email = random_email()
    headers_a = await get_auth_headers(client, user_a_email)

    user_b_email = random_email()
    headers_b = await get_auth_headers(client, user_b_email)

    list_resp = await client.get("/api/v1/quizzes")
    quiz_id = list_resp.json()[0]["id"]
    quiz_detail = (await client.get(f"/api/v1/quizzes/{quiz_id}")).json()
    questions = quiz_detail["questions"]

    # User A submits 2 attempts
    for score_ans in ["async def", "wrong_answer"]:
        await client.post(
            f"/api/v1/quizzes/{quiz_id}/attempts",
            json={
                "answers": [
                    {"question_id": questions[0]["id"], "user_answer": score_ans},
                    {"question_id": questions[1]["id"], "user_answer": "False"},
                    {"question_id": questions[2]["id"], "user_answer": "Depends"},
                ]
            },
            headers=headers_a,
        )

    # User A retrieves history
    history_a = await client.get(f"/api/v1/quizzes/{quiz_id}/attempts", headers=headers_a)
    assert history_a.status_code == 200
    data_a = history_a.json()
    assert data_a["total"] == 2
    assert len(data_a["items"]) == 2
    assert data_a["page"] == 1

    # User B retrieves history -> must be 0 attempts (Row-Level Security / Ownership Isolation)
    history_b = await client.get(f"/api/v1/quizzes/{quiz_id}/attempts", headers=headers_b)
    assert history_b.status_code == 200
    data_b = history_b.json()
    assert data_b["total"] == 0
    assert len(data_b["items"]) == 0


@pytest.mark.asyncio
async def test_unauthenticated_quiz_attempt_rejected(client: AsyncClient):
    list_resp = await client.get("/api/v1/quizzes")
    quiz_id = list_resp.json()[0]["id"]

    submit_resp = await client.post(
        f"/api/v1/quizzes/{quiz_id}/attempts",
        json={"answers": [{"question_id": "dummy", "user_answer": "ans"}]},
    )
    assert submit_resp.status_code == 401

    history_resp = await client.get(f"/api/v1/quizzes/{quiz_id}/attempts")
    assert history_resp.status_code == 401
