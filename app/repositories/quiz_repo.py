from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.course import DifficultyLevel
from app.models.quiz import Quiz, QuizAnswer, QuizAttempt, QuizQuestion


class QuizRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_quiz_by_id(self, quiz_id: str) -> Quiz | None:
        stmt = (
            select(Quiz)
            .where(Quiz.id == quiz_id)
            .options(selectinload(Quiz.questions))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_question_by_id(self, question_id: str) -> QuizQuestion | None:
        stmt = select(QuizQuestion).where(QuizQuestion.id == question_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_quizzes(
        self,
        topic: str | None = None,
        difficulty: DifficultyLevel | None = None,
        lesson_id: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Sequence[Quiz]:
        stmt = select(Quiz)
        if topic:
            stmt = stmt.where(Quiz.topic.ilike(f"%{topic}%"))
        if difficulty:
            stmt = stmt.where(Quiz.difficulty == difficulty)
        if lesson_id:
            stmt = stmt.where(Quiz.lesson_id == lesson_id)

        stmt = stmt.order_by(Quiz.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def create_quiz(self, quiz: Quiz) -> Quiz:
        self.db.add(quiz)
        await self.db.flush()
        return quiz

    async def create_attempt(self, attempt: QuizAttempt) -> QuizAttempt:
        self.db.add(attempt)
        await self.db.flush()
        return attempt

    async def get_attempt_by_id(self, attempt_id: str, user_id: str) -> QuizAttempt | None:
        stmt = (
            select(QuizAttempt)
            .where(QuizAttempt.id == attempt_id, QuizAttempt.user_id == user_id)
            .options(
                selectinload(QuizAttempt.answers).selectinload(QuizAnswer.question),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_attempts_for_quiz(
        self,
        quiz_id: str,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[QuizAttempt], int]:
        count_stmt = (
            select(func.count(QuizAttempt.id))
            .where(QuizAttempt.quiz_id == quiz_id, QuizAttempt.user_id == user_id)
        )
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(QuizAttempt)
            .where(QuizAttempt.quiz_id == quiz_id, QuizAttempt.user_id == user_id)
            .order_by(QuizAttempt.submitted_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all(), total

    async def list_user_attempts(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[QuizAttempt], int]:
        count_stmt = (
            select(func.count(QuizAttempt.id))
            .where(QuizAttempt.user_id == user_id)
        )
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(QuizAttempt)
            .where(QuizAttempt.user_id == user_id)
            .order_by(QuizAttempt.submitted_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all(), total
