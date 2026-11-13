from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.code_submission import CodeSubmission


class CodeRepository:
    """Repository handling code playground submissions and review records."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_submission(self, submission: CodeSubmission) -> CodeSubmission:
        self.db.add(submission)
        await self.db.flush()
        await self.db.refresh(submission)
        return submission

    async def get_submission_by_id(self, submission_id: str, user_id: str) -> CodeSubmission | None:
        """
        Row-level security: only retrieve submission if it belongs to user_id.
        """
        stmt = (
            select(CodeSubmission)
            .where(
                CodeSubmission.id == submission_id,
                CodeSubmission.user_id == user_id,
            )
            .options(selectinload(CodeSubmission.lesson))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_submissions(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
    ) -> Sequence[CodeSubmission]:
        """List user submissions ordered newest first."""
        stmt = (
            select(CodeSubmission)
            .where(CodeSubmission.user_id == user_id)
            .options(selectinload(CodeSubmission.lesson))
            .order_by(CodeSubmission.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def count_submissions(self, user_id: str) -> int:
        stmt = select(func.count(CodeSubmission.id)).where(CodeSubmission.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar() or 0
