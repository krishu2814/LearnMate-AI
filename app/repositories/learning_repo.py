from datetime import datetime, timezone
from typing import List, Optional, Sequence
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.course import Course, DifficultyLevel, Lesson, Module
from app.models.learning_path import ItemType, LearningPath, LearningPathItem, PathStatus
from app.models.progress import LessonProgress, ProgressStatus


class LearningRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_courses(
        self,
        difficulty: Optional[DifficultyLevel] = None,
        subject_tag: Optional[str] = None,
    ) -> Sequence[Course]:
        stmt = select(Course).where(Course.is_published.is_(True))
        if difficulty:
            stmt = stmt.where(Course.difficulty == difficulty)
        if subject_tag:
            stmt = stmt.where(Course.subject_tag == subject_tag)

        stmt = stmt.order_by(Course.created_at.desc())
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_course_by_id(self, course_id: str) -> Optional[Course]:
        stmt = (
            select(Course)
            .where(Course.id == course_id, Course.is_published.is_(True))
            .options(
                selectinload(Course.modules).selectinload(Module.lessons),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_lesson_by_id(self, lesson_id: str) -> Optional[Lesson]:
        stmt = select(Lesson).where(Lesson.id == lesson_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_lessons_by_ids(self, lesson_ids: List[str]) -> Sequence[Lesson]:
        if not lesson_ids:
            return []
        stmt = select(Lesson).where(Lesson.id.in_(lesson_ids))
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def create_learning_path(
        self,
        user_id: str,
        title: str,
        goal: str,
        total_days: int = 30,
        daily_minutes: int = 60,
    ) -> LearningPath:
        path = LearningPath(
            user_id=user_id,
            title=title,
            goal=goal,
            total_days=total_days,
            daily_minutes=daily_minutes,
            status=PathStatus.ACTIVE,
        )
        self.db.add(path)
        await self.db.flush()
        await self.db.refresh(path)
        return path

    async def add_item_to_path(
        self,
        learning_path_id: str,
        lesson_id: str,
        position: int,
        item_type: ItemType = ItemType.LESSON,
        is_optional: bool = False,
    ) -> LearningPathItem:
        item = LearningPathItem(
            learning_path_id=learning_path_id,
            lesson_id=lesson_id,
            position=position,
            item_type=item_type,
            is_optional=is_optional,
        )
        self.db.add(item)
        await self.db.flush()
        return item

    async def get_learning_path(
        self,
        path_id: str,
        user_id: str,
    ) -> Optional[LearningPath]:
        """
        CRITICAL OWNERSHIP PATTERN:
        Query ALWAYS enforces LearningPath.user_id == user_id.
        Never query by path_id alone without ownership verification!
        """
        stmt = (
            select(LearningPath)
            .where(
                LearningPath.id == path_id,
                LearningPath.user_id == user_id,
            )
            .options(
                selectinload(LearningPath.items).selectinload(LearningPathItem.lesson),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_learning_paths(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
    ) -> Sequence[LearningPath]:
        """List learning paths owned strictly by the authenticated user."""
        stmt = (
            select(LearningPath)
            .where(LearningPath.user_id == user_id)
            .options(
                selectinload(LearningPath.items).selectinload(LearningPathItem.lesson),
            )
            .order_by(LearningPath.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def update_learning_path(
        self,
        path: LearningPath,
        **kwargs,
    ) -> LearningPath:
        for key, value in kwargs.items():
            if hasattr(path, key) and value is not None:
                setattr(path, key, value)
        await self.db.flush()
        await self.db.refresh(path)
        return path

    async def delete_learning_path(self, path: LearningPath) -> None:
        await self.db.delete(path)
        await self.db.flush()

    async def get_lesson_progress(
        self,
        user_id: str,
        lesson_id: str,
    ) -> Optional[LessonProgress]:
        stmt = select(LessonProgress).where(
            LessonProgress.user_id == user_id,
            LessonProgress.lesson_id == lesson_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_lesson_progress(
        self,
        user_id: str,
        lesson_id: str,
        status: ProgressStatus = ProgressStatus.COMPLETED,
        time_spent_seconds: Optional[int] = None,
        additional_seconds: int = 0,
    ) -> LessonProgress:
        progress = await self.get_lesson_progress(user_id=user_id, lesson_id=lesson_id)
        now = datetime.now(timezone.utc)

        if progress:
            progress.status = status
            if time_spent_seconds is not None:
                progress.time_spent_seconds = time_spent_seconds
            elif additional_seconds > 0:
                progress.time_spent_seconds += additional_seconds

            if status in (ProgressStatus.IN_PROGRESS, ProgressStatus.COMPLETED) and not progress.started_at:
                progress.started_at = now
            if status == ProgressStatus.COMPLETED and not progress.completed_at:
                progress.completed_at = now
        else:
            initial_time = time_spent_seconds if time_spent_seconds is not None else additional_seconds
            started_at = now if status in (ProgressStatus.IN_PROGRESS, ProgressStatus.COMPLETED) else None
            completed_at = now if status == ProgressStatus.COMPLETED else None

            progress = LessonProgress(
                user_id=user_id,
                lesson_id=lesson_id,
                status=status,
                time_spent_seconds=initial_time,
                started_at=started_at,
                completed_at=completed_at,
            )
            self.db.add(progress)

        await self.db.flush()
        await self.db.refresh(progress)
        return progress

    async def sync_learning_path_items_completed(
        self,
        user_id: str,
        lesson_id: str,
    ) -> None:
        """Mark corresponding items across all the user's learning paths as completed."""
        user_path_subquery = select(LearningPath.id).where(LearningPath.user_id == user_id)
        stmt = (
            update(LearningPathItem)
            .where(
                LearningPathItem.lesson_id == lesson_id,
                LearningPathItem.learning_path_id.in_(user_path_subquery),
            )
            .values(is_completed=True)
        )
        await self.db.execute(stmt)
        await self.db.flush()

    async def get_user_all_progress(
        self,
        user_id: str,
    ) -> Sequence[LessonProgress]:
        stmt = select(LessonProgress).where(LessonProgress.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_all_lessons_count(self) -> int:
        stmt = select(func.count(Lesson.id))
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def get_all_courses_with_lessons(self) -> Sequence[Course]:
        stmt = (
            select(Course)
            .where(Course.is_published.is_(True))
            .options(
                selectinload(Course.modules).selectinload(Module.lessons),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
