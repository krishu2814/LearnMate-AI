import uuid

import pytest
from httpx import AsyncClient


def random_email() -> str:
    return f"flashcard_student_{uuid.uuid4().hex[:8]}@example.com"


async def get_auth_headers(client: AsyncClient, email: str, password: str = "Password123!") -> dict:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Flashcard Tester",
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
async def test_generate_ai_flashcard_deck(client: AsyncClient):
    headers = await get_auth_headers(client, random_email())

    resp = await client.post(
        "/api/v1/flashcards/generate",
        headers=headers,
        json={
            "topic": "Python Generators and Iterators",
            "num_cards": 4,
            "difficulty": "intermediate",
            "custom_instructions": "Focus on yield vs return and memory efficiency",
        },
    )

    assert resp.status_code == 201
    data = resp.json()
    assert "Python Generators" in data["title"]
    assert data["topic"] == "Python Generators and Iterators"
    assert data["card_count"] == 4
    assert len(data["cards"]) == 4
    assert data["new_count"] == 4
    assert data["mastered_count"] == 0


@pytest.mark.asyncio
async def test_generate_ai_flashcard_deck_grounded_in_lesson(client: AsyncClient):
    headers = await get_auth_headers(client, random_email())

    courses = (await client.get("/api/v1/courses")).json()
    course_id = courses[0]["id"]
    course_detail = (await client.get(f"/api/v1/courses/{course_id}")).json()
    lesson_id = course_detail["modules"][0]["lessons"][0]["id"]

    resp = await client.post(
        "/api/v1/flashcards/generate",
        headers=headers,
        json={
            "topic": "Curriculum Lesson Recall",
            "num_cards": 3,
            "lesson_id": lesson_id,
        },
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["lesson_id"] == lesson_id
    assert len(data["cards"]) == 3


@pytest.mark.asyncio
async def test_generate_ai_flashcard_deck_invalid_lesson(client: AsyncClient):
    headers = await get_auth_headers(client, random_email())

    resp = await client.post(
        "/api/v1/flashcards/generate",
        headers=headers,
        json={
            "topic": "Invalid Lesson Test",
            "lesson_id": "nonexistent-lesson-id-999",
        },
    )

    assert resp.status_code == 404
    assert "not found" in resp.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_create_and_get_manual_deck(client: AsyncClient):
    headers = await get_auth_headers(client, random_email())

    create_payload = {
        "title": "Data Structures Quick Review",
        "topic": "Computer Science",
        "description": "Essential arrays, trees, and hash tables review",
        "cards": [
            {
                "front": "What is the average lookup complexity of a hash map?",
                "back": "O(1) constant time on average.",
                "hint": "Consider array bucket hashing.",
                "key_concept": "Hash Map Complexity",
            },
            {
                "front": "What is the height of a balanced binary search tree with N nodes?",
                "back": "O(log N).",
                "hint": "Each split divides nodes in half.",
                "key_concept": "BST Height",
            },
        ],
    }

    create_resp = await client.post(
        "/api/v1/flashcards/decks",
        headers=headers,
        json=create_payload,
    )
    assert create_resp.status_code == 201
    created_data = create_resp.json()
    deck_id = created_data["id"]
    assert created_data["card_count"] == 2
    assert len(created_data["cards"]) == 2

    # Get deck detail
    get_resp = await client.get(
        f"/api/v1/flashcards/decks/{deck_id}",
        headers=headers,
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == deck_id
    assert get_resp.json()["title"] == "Data Structures Quick Review"


@pytest.mark.asyncio
async def test_study_deck_session_leitner_transitions_and_xp(client: AsyncClient):
    headers = await get_auth_headers(client, random_email())

    # Create deck with 2 cards
    create_resp = await client.post(
        "/api/v1/flashcards/decks",
        headers=headers,
        json={
            "title": "Leitner Test Deck",
            "topic": "Algorithms",
            "cards": [
                {"front": "Q1", "back": "A1"},
                {"front": "Q2", "back": "A2"},
            ],
        },
    )
    assert create_resp.status_code == 201
    deck_data = create_resp.json()
    deck_id = deck_data["id"]
    card1_id = deck_data["cards"][0]["id"]
    card2_id = deck_data["cards"][1]["id"]

    # Submit study session: Card 1 -> Good (3), Card 2 -> Easy (4)
    study_resp = await client.post(
        f"/api/v1/flashcards/decks/{deck_id}/study",
        headers=headers,
        json={
            "reviews": [
                {"card_id": card1_id, "rating": 3},
                {"card_id": card2_id, "rating": 4},
            ]
        },
    )
    assert study_resp.status_code == 200
    study_data = study_resp.json()
    assert study_data["total_reviewed"] == 2
    assert study_data["promoted_count"] == 2
    assert study_data["xp_awarded"] > 0

    # Verify updated boxes in deck
    detail_resp = await client.get(
        f"/api/v1/flashcards/decks/{deck_id}",
        headers=headers,
    )
    cards = detail_resp.json()["cards"]
    c1 = next(c for c in cards if c["id"] == card1_id)
    c2 = next(c for c in cards if c["id"] == card2_id)
    assert c1["box"] == 2  # 1 + 1 = 2
    assert c2["box"] == 3  # 1 + 2 = 3


@pytest.mark.asyncio
async def test_delete_flashcard_deck(client: AsyncClient):
    headers = await get_auth_headers(client, random_email())

    create_resp = await client.post(
        "/api/v1/flashcards/decks",
        headers=headers,
        json={"title": "To Delete Deck", "topic": "Testing", "cards": []},
    )
    deck_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/v1/flashcards/decks/{deck_id}", headers=headers)
    assert del_resp.status_code == 204

    # Subsequent GET returns 404
    get_resp = await client.get(f"/api/v1/flashcards/decks/{deck_id}", headers=headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_flashcard_row_level_isolation(client: AsyncClient):
    headers_a = await get_auth_headers(client, random_email())
    headers_b = await get_auth_headers(client, random_email())

    # User A creates a private deck
    create_resp = await client.post(
        "/api/v1/flashcards/decks",
        headers=headers_a,
        json={"title": "User A Private Deck", "topic": "Security", "is_public": False},
    )
    deck_id = create_resp.json()["id"]

    # User B cannot access User A's private deck -> 404
    get_b = await client.get(f"/api/v1/flashcards/decks/{deck_id}", headers=headers_b)
    assert get_b.status_code == 404

    # User B cannot delete User A's deck -> 404
    del_b = await client.delete(f"/api/v1/flashcards/decks/{deck_id}", headers=headers_b)
    assert del_b.status_code == 404


@pytest.mark.asyncio
async def test_unauthenticated_flashcard_endpoints(client: AsyncClient):
    fake_id = str(uuid.uuid4())

    res_gen = await client.post("/api/v1/flashcards/generate", json={"topic": "Test"})
    assert res_gen.status_code == 401

    res_create = await client.post("/api/v1/flashcards/decks", json={"title": "T", "topic": "T"})
    assert res_create.status_code == 401

    res_list = await client.get("/api/v1/flashcards/decks")
    assert res_list.status_code == 401

    res_get = await client.get(f"/api/v1/flashcards/decks/{fake_id}")
    assert res_get.status_code == 401

    res_del = await client.delete(f"/api/v1/flashcards/decks/{fake_id}")
    assert res_del.status_code == 401
