from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.quiz import QuizQuestion
from app.models.srs import ReviewItem


class SRSRepository:
    """Repository handling Spaced Repetition items and SM-2 scheduling parameters."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_item(self, user_id: str, question_id: str) -> ReviewItem | None:
        stmt = (
            select(ReviewItem)
            .where(
                ReviewItem.user_id == user_id,
                ReviewItem.question_id == question_id,
            )
            .options(selectinload(ReviewItem.question))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_item_by_id(self, item_id: str, user_id: str) -> ReviewItem | None:
        """
        Enforce row-level ownership: return ReviewItem strictly if it belongs to user_id.
        """
        stmt = (
            select(ReviewItem)
            .where(
                ReviewItem.id == item_id,
                ReviewItem.user_id == user_id,
            )
            .options(selectinload(ReviewItem.question))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_quiz_mistake(
        self,
        user_id: str,
        question_id: str,
        topic_tag: str | None = None,
    ) -> ReviewItem:
        """
        Record a mistake from a quiz attempt.
        Resets SM-2 repetition counter and schedules for immediate review.
        """
        item = await self.get_item(user_id=user_id, question_id=question_id)
        now = datetime.now(UTC)

        if item:
            item.repetitions = 0
            item.interval_days = 1
            item.consecutive_correct = 0
            item.next_review_at = now
            if topic_tag and not item.topic_tag:
                item.topic_tag = topic_tag
        else:
            item = ReviewItem(
                user_id=user_id,
                question_id=question_id,
                topic_tag=topic_tag,
                interval_days=1,
                repetitions=0,
                ease_factor=2.5,
                next_review_at=now,
            )
            self.db.add(item)

        await self.db.flush()
        return item

    async def record_review_result(self, item: ReviewItem, is_correct: bool) -> ReviewItem:
        """
        Apply SuperMemo SM-2 interval calculation algorithm based on student recall.
        """
        now = datetime.now(UTC)
        item.last_reviewed_at = now
        item.total_reviews += 1

        if is_correct:
            item.correct_reviews += 1
            item.consecutive_correct += 1
            item.repetitions += 1

            if item.repetitions == 1:
                item.interval_days = 1
            elif item.repetitions == 2:
                item.interval_days = 3
            else:
                item.interval_days = max(1, round(item.interval_days * item.ease_factor))

            # Reward consistent recall with slight ease factor increase
            item.ease_factor = min(3.0, item.ease_factor + 0.1)
        else:
            item.consecutive_correct = 0
            item.repetitions = 0
            item.interval_days = 1
            # Penalize missed recall with ease factor decrease
            item.ease_factor = max(1.3, item.ease_factor - 0.2)

        item.next_review_at = now + timedelta(days=item.interval_days)
        await self.db.flush()
        return item

    async def get_due_items(self, user_id: str, limit: int = 50) -> Sequence[ReviewItem]:
        """Fetch review items that have reached or passed their scheduled review time."""
        now = datetime.now(UTC) + timedelta(seconds=5)
        stmt = (
            select(ReviewItem)
            .where(
                ReviewItem.user_id == user_id,
                ReviewItem.next_review_at <= now,
            )
            .options(selectinload(ReviewItem.question))
            .order_by(ReviewItem.next_review_at.asc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def count_due_items(self, user_id: str) -> int:
        now = datetime.now(UTC) + timedelta(seconds=5)
        stmt = select(func.count(ReviewItem.id)).where(
            ReviewItem.user_id == user_id,
            ReviewItem.next_review_at <= now,
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def count_total_items(self, user_id: str) -> int:
        stmt = select(func.count(ReviewItem.id)).where(ReviewItem.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def get_user_weak_topics(self, user_id: str, limit: int = 5) -> list[dict]:
        """Group review items with 0 consecutive correct answers by topic_tag."""
        stmt = (
            select(
                ReviewItem.topic_tag,
                func.count(ReviewItem.id).label("missed_count"),
            )
            .where(
                ReviewItem.user_id == user_id,
                ReviewItem.topic_tag.isnot(None),
                ReviewItem.consecutive_correct == 0,
            )
            .group_by(ReviewItem.topic_tag)
            .order_by(func.count(ReviewItem.id).desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return [{"topic": row[0], "missed_count": row[1]} for row in result.all()]

    async def get_recent_missed_questions(
        self, user_id: str, limit: int = 10
    ) -> Sequence[QuizQuestion]:
        """Retrieve actual question texts for questions the user recently struggled with."""
        stmt = (
            select(QuizQuestion)
            .join(ReviewItem, ReviewItem.question_id == QuizQuestion.id)
            .where(
                ReviewItem.user_id == user_id,
                ReviewItem.consecutive_correct == 0,
            )
            .order_by(ReviewItem.updated_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
