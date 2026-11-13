from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.prompts.path_prompts import build_curriculum_prompt
from app.ai.providers.gemini import GeminiProvider
from app.core.logging import logger
from app.models.learning_path import LearningPath, LearningPathItem
from app.models.progress import ProgressStatus
from app.repositories.learning_repo import LearningRepository
from app.schemas.ai import (
    AILearningPathGenerateRequest,
    AILearningPathGenerateResponse,
)
from app.schemas.learning_path import LearningPathDetailResponse


class AILearningPathService:
    """Service orchestrating AI-driven personalized curriculum generation and persistence."""

    def __init__(self, db: AsyncSession, ai_provider: GeminiProvider | None = None):
        self.db = db
        self.learning_repo = LearningRepository(db)
        self.ai_provider = ai_provider or GeminiProvider()

    async def generate_learning_path(
        self,
        user_id: str,
        payload: AILearningPathGenerateRequest,
    ) -> AILearningPathGenerateResponse:
        """
        Generate a personalized curriculum using Gemini structured outputs,
        grounded in the platform's active catalog of courses and lessons.
        Persists the resulting LearningPath and LearningPathItems.
        """
        # 1. Fetch available course catalog
        courses = await self.learning_repo.get_all_courses_with_lessons()

        catalog_summary: list[dict] = []
        available_lesson_ids: list[str] = []
        for course in courses:
            for module in course.modules:
                for lesson in module.lessons:
                    available_lesson_ids.append(lesson.id)
                    catalog_summary.append(
                        {
                            "course_title": course.title,
                            "module_title": module.title,
                            "lesson_id": lesson.id,
                            "lesson_title": lesson.title,
                            "estimated_minutes": lesson.estimated_minutes,
                        }
                    )

        # 2. Build prompt and query AI
        prompt = build_curriculum_prompt(
            goal=payload.goal,
            difficulty=payload.difficulty,
            total_days=payload.total_days,
            daily_minutes=payload.daily_minutes,
            catalog_summary=catalog_summary,
            custom_focus=payload.custom_focus,
        )

        generated = await self.ai_provider.generate_curriculum(
            prompt=prompt,
            goal=payload.goal,
            available_lesson_ids=available_lesson_ids,
            total_days=payload.total_days,
            daily_minutes=payload.daily_minutes,
        )

        # 3. Filter valid lesson IDs to ensure grounding in actual DB entities
        valid_ids = [lid for lid in generated.selected_lesson_ids if lid in available_lesson_ids]
        if not valid_ids and available_lesson_ids:
            # Fallback to catalog defaults if AI selected nonexistent IDs
            valid_ids = available_lesson_ids[:5]

        # 4. Create the LearningPath entity
        path = LearningPath(
            user_id=user_id,
            title=generated.title,
            goal=payload.goal,
            total_days=payload.total_days,
            daily_minutes=payload.daily_minutes,
        )

        # 5. Check if user has already completed any of these lessons
        user_progress = await self.learning_repo.get_user_all_progress(user_id=user_id)
        completed_ids = {p.lesson_id for p in user_progress if p.status == ProgressStatus.COMPLETED}

        lessons = await self.learning_repo.get_lessons_by_ids(valid_ids)
        lesson_map = {lesson.id: lesson for lesson in lessons}

        for idx, lid in enumerate(valid_ids):
            if lid not in lesson_map:
                continue
            item = LearningPathItem(
                learning_path_id=path.id,
                lesson_id=lid,
                position=idx + 1,
                is_completed=(lid in completed_ids),
            )
            item.lesson = lesson_map[lid]
            path.items.append(item)

        self.db.add(path)
        await self.db.commit()

        logger.info(
            "ai_learning_path_generated",
            path_id=path.id,
            user_id=user_id,
            lessons_count=len(path.items),
        )

        detail_response = LearningPathDetailResponse.model_validate(path)
        return AILearningPathGenerateResponse(
            learning_path=detail_response,
            ai_overview=generated.overview,
            weekly_milestones=generated.weekly_milestones,
            study_tips=generated.study_tips,
        )
