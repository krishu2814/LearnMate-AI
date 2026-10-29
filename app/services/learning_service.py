from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.models.course import DifficultyLevel
from app.models.learning_path import LearningPath, LearningPathItem
from app.repositories.learning_repo import LearningRepository
from app.schemas.course import CourseDetailResponse, CourseResponse
from app.schemas.learning_path import (
    LearningPathCreate,
    LearningPathDetailResponse,
    LearningPathResponse,
    LearningPathUpdate,
)


class LearningService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = LearningRepository(db)

    async def get_courses(
        self,
        difficulty: Optional[DifficultyLevel] = None,
        subject_tag: Optional[str] = None,
    ) -> List[CourseResponse]:
        courses = await self.repo.get_courses(difficulty=difficulty, subject_tag=subject_tag)
        return [CourseResponse.model_validate(c) for c in courses]

    async def get_course(self, course_id: str) -> CourseDetailResponse:
        course = await self.repo.get_course_by_id(course_id)
        if not course:
            raise NotFoundException(f"Course '{course_id}' not found")
        return CourseDetailResponse.model_validate(course)

    async def create_learning_path(
        self,
        user_id: str,
        payload: LearningPathCreate,
    ) -> LearningPathDetailResponse:
        lesson_map = {}
        if payload.lesson_ids:
            lessons = await self.repo.get_lessons_by_ids(payload.lesson_ids)
            lesson_map = {lesson.id: lesson for lesson in lessons}
            for lesson_id in payload.lesson_ids:
                if lesson_id not in lesson_map:
                    raise NotFoundException(f"Lesson '{lesson_id}' not found")

        path = LearningPath(
            user_id=user_id,
            title=payload.title,
            goal=payload.goal,
            total_days=payload.total_days,
            daily_minutes=payload.daily_minutes,
        )

        for idx, lesson_id in enumerate(payload.lesson_ids):
            item = LearningPathItem(
                learning_path_id=path.id,
                lesson_id=lesson_id,
                position=idx + 1,
            )
            item.lesson = lesson_map[lesson_id]
            path.items.append(item)

        self.db.add(path)
        await self.db.commit()
        await self.db.refresh(path)

        return LearningPathDetailResponse.model_validate(path)

    async def get_learning_path(
        self,
        path_id: str,
        user_id: str,
    ) -> LearningPathDetailResponse:
        path = await self.repo.get_learning_path(path_id, user_id)
        if not path:
            raise NotFoundException(f"Learning path '{path_id}' not found")
        return LearningPathDetailResponse.model_validate(path)

    async def list_learning_paths(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
    ) -> List[LearningPathResponse]:
        paths = await self.repo.list_learning_paths(user_id=user_id, skip=skip, limit=limit)
        return [LearningPathResponse.model_validate(p) for p in paths]

    async def update_learning_path(
        self,
        path_id: str,
        user_id: str,
        payload: LearningPathUpdate,
    ) -> LearningPathResponse:
        path = await self.repo.get_learning_path(path_id, user_id)
        if not path:
            raise NotFoundException(f"Learning path '{path_id}' not found")

        updated_path = await self.repo.update_learning_path(
            path,
            **payload.model_dump(exclude_unset=True),
        )
        await self.db.commit()
        return LearningPathResponse.model_validate(updated_path)

    async def delete_learning_path(
        self,
        path_id: str,
        user_id: str,
    ) -> None:
        path = await self.repo.get_learning_path(path_id, user_id)
        if not path:
            raise NotFoundException(f"Learning path '{path_id}' not found")

        await self.repo.delete_learning_path(path)
        await self.db.commit()
