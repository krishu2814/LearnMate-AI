import datetime
import math

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.gamification import GamificationProfile
from app.repositories.gamification_repo import GamificationRepository
from app.schemas.gamification import (
    BadgeResponse,
    GamificationProfileResponse,
    LeaderboardEntry,
    LeaderboardResponse,
    SyncGamificationResponse,
)


class GamificationService:
    """Service governing learner experience points, level progression, streaks, and badges."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = GamificationRepository(db)

    # =========================================================================
    # Level & XP Mechanics
    # =========================================================================

    @staticmethod
    def calculate_level(total_xp: int) -> int:
        """
        Calculate RPG level from cumulative XP.
        Formula: XP_base(L) = 50 * L * (L - 1)
        Level = floor((1 + sqrt(1 + 4 * (XP / 50))) / 2)
        """
        if total_xp <= 0:
            return 1
        return max(1, math.floor((1 + math.sqrt(1 + 4 * (total_xp / 50))) / 2))

    @staticmethod
    def get_level_threshold(level: int) -> int:
        """Calculate minimum cumulative XP required to reach a specific level."""
        if level <= 1:
            return 0
        return 50 * level * (level - 1)

    # =========================================================================
    # Gamification Profile & Badges
    # =========================================================================

    async def get_profile(self, user_id: str) -> GamificationProfileResponse:
        """Fetch the full gamification profile for a user with calculated level metrics."""
        profile = await self.repo.get_or_create_profile(user_id)
        user_badges = await self.repo.get_user_badges(user_id)
        all_badges = await self.repo.list_all_badges()

        return self._format_profile_response(
            profile=profile,
            user_badges_count=len(user_badges),
            total_badges_count=len(all_badges),
            recent_user_badges=list(user_badges[:5]),
        )

    async def list_badges(self, user_id: str) -> list[BadgeResponse]:
        """List all system badges annotated with the learner's unlock status and timestamp."""
        all_badges = await self.repo.list_all_badges()
        user_badges = await self.repo.get_user_badges(user_id)
        unlock_map = {ub.badge_id: ub.unlocked_at for ub in user_badges}

        badges_response: list[BadgeResponse] = []
        for badge in all_badges:
            is_unlocked = badge.id in unlock_map
            badges_response.append(
                BadgeResponse(
                    id=badge.id,
                    name=badge.name,
                    description=badge.description,
                    icon=badge.icon,
                    xp_reward=badge.xp_reward,
                    criteria_type=badge.criteria_type,
                    criteria_threshold=badge.criteria_threshold,
                    is_unlocked=is_unlocked,
                    unlocked_at=unlock_map.get(badge.id),
                )
            )
        return badges_response

    async def get_leaderboard(
        self,
        current_user_id: str,
        limit: int = 20,
    ) -> LeaderboardResponse:
        """Fetch ranked leaderboard entries and authenticated user rank."""
        leaderboard_rows = await self.repo.get_leaderboard(limit=limit)
        user_rank = await self.repo.get_user_rank(current_user_id)

        entries: list[LeaderboardEntry] = []
        user_entry: LeaderboardEntry | None = None

        for rank_idx, (prof, user, badge_cnt) in enumerate(leaderboard_rows, start=1):
            entry = LeaderboardEntry(
                rank=rank_idx,
                user_id=user.id,
                full_name=user.full_name or "Anonymous Scholar",
                total_xp=prof.total_xp,
                current_level=prof.current_level,
                current_streak=prof.current_streak,
                badges_count=badge_cnt,
            )
            entries.append(entry)
            if user.id == current_user_id:
                user_entry = entry

        # If current user is not in top limit, fetch their specific entry
        if user_entry is None and user_rank is not None:
            user_prof = await self.repo.get_profile_by_user_id(current_user_id)
            if user_prof and user_prof.user:
                user_badges = await self.repo.get_user_badges(current_user_id)
                user_entry = LeaderboardEntry(
                    rank=user_rank,
                    user_id=current_user_id,
                    full_name=user_prof.user.full_name or "Anonymous Scholar",
                    total_xp=user_prof.total_xp,
                    current_level=user_prof.current_level,
                    current_streak=user_prof.current_streak,
                    badges_count=len(user_badges),
                )

        return LeaderboardResponse(
            entries=entries,
            user_rank=user_rank,
            user_entry=user_entry,
        )

    # =========================================================================
    # Synchronization & Progression Updates
    # =========================================================================

    async def record_activity_and_sync(self, user_id: str) -> SyncGamificationResponse:
        """
        Synchronize learner achievements, evaluate all badge criteria,
        update daily streaks, and commit awards.
        """
        profile = await self.repo.get_or_create_profile(user_id)
        today = datetime.datetime.now(datetime.UTC).date()

        # 1. Update daily study streak
        self._update_streak(profile, today)

        # 2. Collect current platform activity metrics
        lessons_completed = await self.repo.count_completed_lessons(user_id)
        quizzes_perfect = await self.repo.count_perfect_quizzes(user_id)
        quizzes_passed = await self.repo.count_passed_quizzes(user_id)
        srs_reviewed = await self.repo.count_srs_reviews(user_id)
        code_passed = await self.repo.count_passed_code_submissions(user_id)

        metrics: dict[str, int] = {
            "lesson_completed": lessons_completed,
            "quiz_perfect": quizzes_perfect,
            "quiz_passed": quizzes_passed,
            "srs_reviewed": srs_reviewed,
            "code_passed": code_passed,
            "streak_days": max(profile.current_streak, profile.longest_streak),
        }

        # 3. Evaluate criteria against all registered badges
        all_badges = await self.repo.list_all_badges()
        already_unlocked = await self.repo.get_user_badge_ids(user_id)

        newly_unlocked: list[BadgeResponse] = []
        total_xp_awarded = 0

        for badge in all_badges:
            if badge.id in already_unlocked:
                continue

            current_metric_val = metrics.get(badge.criteria_type, 0)
            if current_metric_val >= badge.criteria_threshold:
                awarded = await self.repo.award_badge(user_id, badge.id)
                if awarded:
                    total_xp_awarded += badge.xp_reward
                    newly_unlocked.append(
                        BadgeResponse(
                            id=badge.id,
                            name=badge.name,
                            description=badge.description,
                            icon=badge.icon,
                            xp_reward=badge.xp_reward,
                            criteria_type=badge.criteria_type,
                            criteria_threshold=badge.criteria_threshold,
                            is_unlocked=True,
                            unlocked_at=awarded.unlocked_at,
                        )
                    )

        # 4. Apply newly awarded XP & recalculate level
        if total_xp_awarded > 0:
            profile.total_xp += total_xp_awarded
            profile.current_level = self.calculate_level(profile.total_xp)

        await self.db.commit()

        logger.info(
            "gamification_synced",
            user_id=user_id,
            xp_awarded=total_xp_awarded,
            newly_unlocked_badges_count=len(newly_unlocked),
            current_level=profile.current_level,
            current_streak=profile.current_streak,
        )

        # 5. Build full response
        user_badges = await self.repo.get_user_badges(user_id)
        profile_response = self._format_profile_response(
            profile=profile,
            user_badges_count=len(user_badges),
            total_badges_count=len(all_badges),
            recent_user_badges=list(user_badges[:5]),
        )

        message = (
            f"Progress synced. Unlocked {len(newly_unlocked)} new badges and earned +{total_xp_awarded} XP!"
            if newly_unlocked
            else "Progress up to date."
        )

        return SyncGamificationResponse(
            xp_awarded=total_xp_awarded,
            newly_unlocked_badges=newly_unlocked,
            profile=profile_response,
            message=message,
        )

    async def award_xp(self, user_id: str, amount: int) -> int:
        """Directly award XP to a learner and adjust streak."""
        profile = await self.repo.get_or_create_profile(user_id)
        today = datetime.datetime.now(datetime.UTC).date()
        self._update_streak(profile, today)

        profile.total_xp += amount
        profile.current_level = self.calculate_level(profile.total_xp)
        await self.db.commit()
        return profile.total_xp

    def _update_streak(self, profile: GamificationProfile, today: datetime.date) -> bool:
        """Update consecutive day streak in-place."""
        if profile.last_active_date == today:
            return False

        yesterday = today - datetime.timedelta(days=1)
        if profile.last_active_date == yesterday:
            profile.current_streak += 1
        else:
            profile.current_streak = 1

        profile.longest_streak = max(profile.longest_streak, profile.current_streak)
        profile.last_active_date = today
        return True

    def _format_profile_response(
        self,
        profile: GamificationProfile,
        user_badges_count: int,
        total_badges_count: int,
        recent_user_badges: list,
    ) -> GamificationProfileResponse:
        """Format database profile record into detailed response with calculated level bounds."""
        current_lvl = self.calculate_level(profile.total_xp)
        current_level_base = self.get_level_threshold(current_lvl)
        next_level_target = self.get_level_threshold(current_lvl + 1)
        xp_in_level = profile.total_xp - current_level_base
        xp_span = max(1, next_level_target - current_level_base)
        progress_pct = round(min(100.0, max(0.0, (xp_in_level / xp_span) * 100.0)), 1)
        xp_remaining = max(0, next_level_target - profile.total_xp)

        formatted_recent = [
            BadgeResponse(
                id=ub.badge.id,
                name=ub.badge.name,
                description=ub.badge.description,
                icon=ub.badge.icon,
                xp_reward=ub.badge.xp_reward,
                criteria_type=ub.badge.criteria_type,
                criteria_threshold=ub.badge.criteria_threshold,
                is_unlocked=True,
                unlocked_at=ub.unlocked_at,
            )
            for ub in recent_user_badges
            if ub.badge
        ]

        return GamificationProfileResponse(
            user_id=profile.user_id,
            total_xp=profile.total_xp,
            current_level=current_lvl,
            current_level_base_xp=current_level_base,
            next_level_xp=next_level_target,
            xp_for_next_level=xp_remaining,
            level_progress_percentage=progress_pct,
            current_streak=profile.current_streak,
            longest_streak=profile.longest_streak,
            last_active_date=profile.last_active_date,
            unlocked_badges_count=user_badges_count,
            total_badges_count=total_badges_count,
            recent_badges=formatted_recent,
        )
