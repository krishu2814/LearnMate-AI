import datetime
import uuid

from app.models.gamification import Badge, GamificationProfile, UserBadge
from app.services.gamification_service import GamificationService


def test_level_calculation_curve():
    calc = GamificationService.calculate_level

    # Level 1 (0 to 99 XP)
    assert calc(0) == 1
    assert calc(50) == 1
    assert calc(99) == 1

    # Level 2 (100 to 299 XP)
    assert calc(100) == 2
    assert calc(200) == 2
    assert calc(299) == 2

    # Level 3 (300 to 599 XP)
    assert calc(300) == 3
    assert calc(450) == 3
    assert calc(599) == 3

    # Level 4 (600 to 999 XP)
    assert calc(600) == 4
    assert calc(800) == 4
    assert calc(999) == 4

    # Level 5 (1000+ XP)
    assert calc(1000) == 5
    assert calc(1500) == 6


def test_level_thresholds():
    thresh = GamificationService.get_level_threshold
    assert thresh(1) == 0
    assert thresh(2) == 100
    assert thresh(3) == 300
    assert thresh(4) == 600
    assert thresh(5) == 1000


def test_streak_progression_logic():
    service = GamificationService(None)  # type: ignore[arg-type]
    profile = GamificationProfile(user_id=str(uuid.uuid4()))

    day1 = datetime.date(2026, 11, 1)
    day2 = datetime.date(2026, 11, 2)
    day3 = datetime.date(2026, 11, 3)
    day5 = datetime.date(2026, 11, 5)  # Gap day (missed Nov 4)

    # 1. Day 1: first activity
    updated = service._update_streak(profile, day1)
    assert updated is True
    assert profile.current_streak == 1
    assert profile.longest_streak == 1
    assert profile.last_active_date == day1

    # 2. Day 1 again: duplicate activity on same day
    updated_again = service._update_streak(profile, day1)
    assert updated_again is False
    assert profile.current_streak == 1
    assert profile.longest_streak == 1

    # 3. Day 2: consecutive day
    updated_d2 = service._update_streak(profile, day2)
    assert updated_d2 is True
    assert profile.current_streak == 2
    assert profile.longest_streak == 2
    assert profile.last_active_date == day2

    # 4. Day 3: consecutive day
    updated_d3 = service._update_streak(profile, day3)
    assert updated_d3 is True
    assert profile.current_streak == 3
    assert profile.longest_streak == 3

    # 5. Day 5: gap day, broken streak
    updated_d5 = service._update_streak(profile, day5)
    assert updated_d5 is True
    assert profile.current_streak == 1  # Reset to 1
    assert profile.longest_streak == 3  # Longest streak preserved!
    assert profile.last_active_date == day5


def test_gamification_model_reprs():
    uid = str(uuid.uuid4())
    prof = GamificationProfile(user_id=uid, total_xp=450, current_level=3, current_streak=4)
    assert "user=" in repr(prof)
    assert "xp=450" in repr(prof)
    assert "level=3" in repr(prof)

    badge = Badge(
        id="streak_master",
        name="Streak Master",
        description="Study 7 days",
        icon="🔥",
        xp_reward=150,
    )
    assert "streak_master" in repr(badge)
    assert "xp=150" in repr(badge)

    ub = UserBadge(user_id=uid, badge_id="streak_master")
    assert f"user={uid}" in repr(ub)
    assert "badge=streak_master" in repr(ub)
