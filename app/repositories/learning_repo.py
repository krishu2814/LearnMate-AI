from typing import List, Optional, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.course import Course, DifficultyLevel, Lesson, Module
from app.models.learning_path import ItemType, LearningPath, LearningPathItem, PathStatus


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
