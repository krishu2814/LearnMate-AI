from collections.abc import Sequence

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.code_submission import CodeSubmission
from app.models.gamification import Badge, GamificationProfile, UserBadge
from app.models.progress import LessonProgress, ProgressStatus
from app.models.quiz import QuizAttempt
from app.models.srs import ReviewItem
from app.models.user import User


class GamificationRepository:
    """Repository handling database operations for gamification profiles, badges, and leaderboards."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_profile(self, user_id: str) -> GamificationProfile:
        """Retrieve existing profile or create a default one for the student."""
        result = await self.db.execute(
            select(GamificationProfile).where(GamificationProfile.user_id == user_id)
        )
        profile = result.scalars().first()
        if not profile:
            profile = GamificationProfile(
                user_id=user_id,
                total_xp=0,
                current_level=1,
                current_streak=0,
                longest_streak=0,
                last_active_date=None,
            )
            self.db.add(profile)
            await self.db.flush()
        return profile

    async def get_profile_by_user_id(self, user_id: str) -> GamificationProfile | None:
        """Fetch profile for a user."""
        result = await self.db.execute(
            select(GamificationProfile).where(GamificationProfile.user_id == user_id)
        )
        return result.scalars().first()

    async def list_all_badges(self) -> Sequence[Badge]:
        """Fetch all registered achievement badges."""
        result = await self.db.execute(
            select(Badge).order_by(Badge.criteria_threshold.asc(), Badge.xp_reward.asc())
        )
        return result.scalars().all()

    async def get_user_badges(self, user_id: str) -> Sequence[UserBadge]:
        """Fetch all badges earned by a specific user with eager-loaded badge metadata."""
        result = await self.db.execute(
            select(UserBadge)
            .options(selectinload(UserBadge.badge))
            .where(UserBadge.user_id == user_id)
            .order_by(UserBadge.unlocked_at.desc())
        )
        return result.scalars().all()

    async def get_user_badge_ids(self, user_id: str) -> set[str]:
        """Fetch set of badge IDs already unlocked by a user."""
        result = await self.db.execute(
            select(UserBadge.badge_id).where(UserBadge.user_id == user_id)
        )
        return set(result.scalars().all())

    async def award_badge(self, user_id: str, badge_id: str) -> UserBadge | None:
        """Award a badge to a user if not already unlocked."""
        existing = await self.db.execute(
            select(UserBadge).where(
                UserBadge.user_id == user_id,
                UserBadge.badge_id == badge_id,
            )
        )
        if existing.scalars().first():
            return None

        user_badge = UserBadge(user_id=user_id, badge_id=badge_id)
        self.db.add(user_badge)
        await self.db.flush()
        return user_badge

    async def get_leaderboard(
        self,
        limit: int = 20,
    ) -> list[tuple[GamificationProfile, User, int]]:
        """
        Fetch top students by total XP, joining User entity and counting badges.
        Returns tuples of (GamificationProfile, User, badge_count).
        """
        # Subquery to count badges per user
        badge_count_subq = (
            select(
                UserBadge.user_id,
                func.count(UserBadge.id).label("badge_count"),
            )
            .group_by(UserBadge.user_id)
            .subquery()
        )

        query = (
            select(
                GamificationProfile,
                User,
                func.coalesce(badge_count_subq.c.badge_count, 0).label("badge_count"),
            )
            .join(User, GamificationProfile.user_id == User.id)
            .outerjoin(badge_count_subq, GamificationProfile.user_id == badge_count_subq.c.user_id)
            .order_by(desc(GamificationProfile.total_xp), desc(GamificationProfile.current_streak))
            .limit(limit)
        )

        result = await self.db.execute(query)
        return [(row[0], row[1], int(row[2])) for row in result.all()]

    async def get_user_rank(self, user_id: str) -> int | None:
        """Compute the rank placement of a user on the global leaderboard."""
        profile = await self.get_profile_by_user_id(user_id)
        if not profile:
            return None

        # Rank is number of learners with strictly greater XP + 1
        count_res = await self.db.execute(
            select(func.count(GamificationProfile.id)).where(
                GamificationProfile.total_xp > profile.total_xp
            )
        )
        greater_count = count_res.scalar() or 0
        return greater_count + 1

    # =========================================================================
    # Activity Aggregators for Automatic Criteria Evaluation
    # =========================================================================

    async def count_completed_lessons(self, user_id: str) -> int:
        """Count unique lessons completed by student."""
        res = await self.db.execute(
            select(func.count(LessonProgress.id)).where(
                LessonProgress.user_id == user_id,
                LessonProgress.status == ProgressStatus.COMPLETED,
            )
        )
        return res.scalar() or 0

    async def count_perfect_quizzes(self, user_id: str) -> int:
        """Count quiz attempts where user scored 100%."""
        res = await self.db.execute(
            select(func.count(QuizAttempt.id)).where(
                QuizAttempt.user_id == user_id,
                QuizAttempt.score == 100.0,
            )
        )
        return res.scalar() or 0

    async def count_passed_quizzes(self, user_id: str) -> int:
        """Count quiz attempts where user scored >= 70%."""
        res = await self.db.execute(
            select(func.count(func.distinct(QuizAttempt.quiz_id))).where(
                QuizAttempt.user_id == user_id,
                QuizAttempt.score >= 70.0,
            )
        )
        return res.scalar() or 0

    async def count_srs_reviews(self, user_id: str) -> int:
        """Count total SRS reviews executed by the student."""
        res = await self.db.execute(
            select(func.sum(ReviewItem.total_reviews)).where(
                ReviewItem.user_id == user_id,
            )
        )
        return int(res.scalar() or 0)

    async def count_passed_code_submissions(self, user_id: str) -> int:
        """Count passing code submissions in the playground."""
        res = await self.db.execute(
            select(func.count(CodeSubmission.id)).where(
                CodeSubmission.user_id == user_id,
                CodeSubmission.is_passed.is_(True),
            )
        )
        return res.scalar() or 0
