from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.models.course import DifficultyLevel
from app.models.learning_path import LearningPath, LearningPathItem
from app.models.progress import ProgressStatus
from app.repositories.learning_repo import LearningRepository
from app.schemas.course import CourseDetailResponse, CourseResponse, LessonDetailResponse
from app.schemas.learning_path import (
    LearningPathCreate,
    LearningPathDetailResponse,
    LearningPathResponse,
    LearningPathUpdate,
)
from app.schemas.progress import (
    CourseProgressSummary,
    DashboardProgressResponse,
    LessonProgressResponse,
    LessonProgressUpdate,
    PathProgressSummary,
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

    async def get_lesson(self, lesson_id: str) -> LessonDetailResponse:
        lesson = await self.repo.get_lesson_by_id(lesson_id)
        if not lesson:
            raise NotFoundException(f"Lesson '{lesson_id}' not found")
        return LessonDetailResponse.model_validate(lesson)

    async def update_lesson_progress(
        self,
        user_id: str,
        lesson_id: str,
        payload: LessonProgressUpdate,
    ) -> LessonProgressResponse:
        lesson = await self.repo.get_lesson_by_id(lesson_id)
        if not lesson:
            raise NotFoundException(f"Lesson '{lesson_id}' not found")

        progress = await self.repo.upsert_lesson_progress(
            user_id=user_id,
            lesson_id=lesson_id,
            status=payload.status,
            time_spent_seconds=payload.time_spent_seconds,
            additional_seconds=payload.additional_seconds or 0,
        )

        if payload.status == ProgressStatus.COMPLETED:
            await self.repo.sync_learning_path_items_completed(user_id=user_id, lesson_id=lesson_id)

        await self.db.commit()
        await self.db.refresh(progress)
        return LessonProgressResponse.model_validate(progress)

    async def get_dashboard_progress(self, user_id: str) -> DashboardProgressResponse:
        all_progress = await self.repo.get_user_all_progress(user_id)
        completed_lesson_ids = {p.lesson_id for p in all_progress if p.status == ProgressStatus.COMPLETED}
        in_progress_count = sum(1 for p in all_progress if p.status == ProgressStatus.IN_PROGRESS)
        total_time_spent = sum(p.time_spent_seconds for p in all_progress)

        courses = await self.repo.get_all_courses_with_lessons()
        total_lessons_available = 0
        courses_progress = []

        for course in courses:
            course_lesson_ids = [
                lesson.id
                for module in course.modules
                for lesson in module.lessons
            ]
            course_total = len(course_lesson_ids)
            total_lessons_available += course_total
            course_completed = sum(1 for lid in course_lesson_ids if lid in completed_lesson_ids)
            course_pct = round((course_completed / course_total) * 100, 1) if course_total > 0 else 0.0

            courses_progress.append(
                CourseProgressSummary(
                    course_id=course.id,
                    course_title=course.title,
                    total_lessons=course_total,
                    completed_lessons=course_completed,
                    completion_pct=course_pct,
                )
            )

        active_paths = await self.repo.list_learning_paths(user_id=user_id, limit=50)
        paths_progress = [
            PathProgressSummary(
                path_id=p.id,
                title=p.title,
                total_items=p.total_items,
                completed_items=p.completed_items,
                completion_pct=p.completion_pct,
            )
            for p in active_paths
        ]

        overall_pct = (
            round((len(completed_lesson_ids) / total_lessons_available) * 100, 1)
            if total_lessons_available > 0
            else 0.0
        )

        return DashboardProgressResponse(
            total_lessons_available=total_lessons_available,
            completed_lessons=len(completed_lesson_ids),
            in_progress_lessons=in_progress_count,
            overall_completion_pct=overall_pct,
            total_time_spent_seconds=total_time_spent,
            total_time_spent_minutes=total_time_spent // 60,
            courses_progress=courses_progress,
            active_paths_progress=paths_progress,
        )
