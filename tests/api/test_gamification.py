import uuid

import pytest
from httpx import AsyncClient


def random_email() -> str:
    return f"gamer_student_{uuid.uuid4().hex[:8]}@example.com"


async def get_auth_headers(client: AsyncClient, email: str, password: str = "Password123!") -> dict:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Gamification Tester",
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
async def test_get_gamification_profile_initial(client: AsyncClient):
    headers = await get_auth_headers(client, random_email())

    resp = await client.get("/api/v1/gamification/profile", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_xp"] == 0
    assert data["current_level"] == 1
    assert data["current_streak"] == 0
    assert data["longest_streak"] == 0
    assert data["unlocked_badges_count"] == 0
    assert data["total_badges_count"] >= 8
    assert data["level_progress_percentage"] == 0.0
    assert data["xp_for_next_level"] == 100


@pytest.mark.asyncio
async def test_list_all_badges(client: AsyncClient):
    headers = await get_auth_headers(client, random_email())

    resp = await client.get("/api/v1/gamification/badges", headers=headers)
    assert resp.status_code == 200
    badges = resp.json()
    assert len(badges) >= 8

    badge_ids = [b["id"] for b in badges]
    assert "first_lesson" in badge_ids
    assert "perfect_quiz" in badge_ids
    assert "code_ninja" in badge_ids
    assert "streak_3" in badge_ids

    # For brand new user, all badges should be locked
    assert all(b["is_unlocked"] is False for b in badges)


@pytest.mark.asyncio
async def test_gamification_sync_awards_first_lesson_badge(client: AsyncClient):
    headers = await get_auth_headers(client, random_email())

    # Get a real lesson ID from courses
    courses = (await client.get("/api/v1/courses")).json()
    course_id = courses[0]["id"]
    course_detail = (await client.get(f"/api/v1/courses/{course_id}")).json()
    lesson_id = course_detail["modules"][0]["lessons"][0]["id"]

    # 1. Complete lesson
    prog_resp = await client.put(
        f"/api/v1/lessons/{lesson_id}/progress",
        headers=headers,
        json={"status": "completed", "time_spent_seconds": 300},
    )
    assert prog_resp.status_code == 200

    # 2. Sync gamification progress
    sync_resp = await client.post("/api/v1/gamification/sync", headers=headers)
    assert sync_resp.status_code == 200
    sync_data = sync_resp.json()

    # Should unlock "first_lesson" badge
    unlocked_ids = [b["id"] for b in sync_data["newly_unlocked_badges"]]
    assert "first_lesson" in unlocked_ids
    assert sync_data["xp_awarded"] >= 50

    # Verify profile reflects XP and streak
    profile = sync_data["profile"]
    assert profile["total_xp"] >= 75  # 25 XP from completion hook + 50 from badge
    assert profile["current_streak"] == 1
    assert profile["unlocked_badges_count"] >= 1
    assert any(b["id"] == "first_lesson" for b in profile["recent_badges"])


@pytest.mark.asyncio
async def test_gamification_sync_code_ninja_badge(client: AsyncClient):
    headers = await get_auth_headers(client, random_email())

    # Submit clean code in playground
    code_resp = await client.post(
        "/api/v1/code/review",
        headers=headers,
        json={
            "title": "Clean Math Function",
            "language": "python",
            "source_code": "def multiply(x: int, y: int) -> int:\n    return x * y\n",
        },
    )
    assert code_resp.status_code == 201

    # Sync
    sync_resp = await client.post("/api/v1/gamification/sync", headers=headers)
    assert sync_resp.status_code == 200
    sync_data = sync_resp.json()

    unlocked_ids = [b["id"] for b in sync_data["newly_unlocked_badges"]]
    assert "code_ninja" in unlocked_ids

    # Check badges endpoint reflects unlock
    badges_resp = await client.get("/api/v1/gamification/badges", headers=headers)
    badges = badges_resp.json()
    code_badge = next(b for b in badges if b["id"] == "code_ninja")
    assert code_badge["is_unlocked"] is True
    assert code_badge["unlocked_at"] is not None


@pytest.mark.asyncio
async def test_leaderboard_rankings(client: AsyncClient):
    email_a = random_email()
    email_b = random_email()

    headers_a = await get_auth_headers(client, email_a)
    headers_b = await get_auth_headers(client, email_b)

    # User A completes a lesson -> earns XP
    courses = (await client.get("/api/v1/courses")).json()
    course_id = courses[0]["id"]
    course_detail = (await client.get(f"/api/v1/courses/{course_id}")).json()
    lesson_id = course_detail["modules"][0]["lessons"][0]["id"]
    await client.put(
        f"/api/v1/lessons/{lesson_id}/progress",
        headers=headers_a,
        json={"status": "completed", "time_spent_seconds": 200},
    )
    await client.post("/api/v1/gamification/sync", headers=headers_a)

    # Fetch leaderboard from User A perspective
    leaderboard_resp = await client.get("/api/v1/gamification/leaderboard", headers=headers_a)
    assert leaderboard_resp.status_code == 200
    data = leaderboard_resp.json()

    assert len(data["entries"]) >= 1
    assert data["user_rank"] is not None
    assert data["user_rank"] >= 1
    assert data["user_entry"] is not None
    assert data["user_entry"]["total_xp"] >= 25

    # Fetch leaderboard from User B perspective
    lead_b = await client.get("/api/v1/gamification/leaderboard", headers=headers_b)
    assert lead_b.status_code == 200


@pytest.mark.asyncio
async def test_gamification_endpoints_require_auth(client: AsyncClient):
    res_prof = await client.get("/api/v1/gamification/profile")
    assert res_prof.status_code == 401

    res_badges = await client.get("/api/v1/gamification/badges")
    assert res_badges.status_code == 401

    res_lead = await client.get("/api/v1/gamification/leaderboard")
    assert res_lead.status_code == 401

    res_sync = await client.post("/api/v1/gamification/sync")
    assert res_sync.status_code == 401
