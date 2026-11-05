from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.prompts.tutor_prompts import (
    build_lesson_explanation_prompt,
    build_socratic_tutor_prompt,
)
from app.ai.providers.gemini import GeminiProvider
from app.core.exceptions import BadRequestException, NotFoundException
from app.repositories.learning_repo import LearningRepository
from app.schemas.ai import (
    AILessonExplainRequest,
    AILessonExplainResponse,
    AITutorChatRequest,
    AITutorChatResponse,
)


class AITutorService:
    """Service providing intelligent Socratic tutoring and lesson conceptual explanations."""

    def __init__(self, db: AsyncSession, ai_provider: GeminiProvider | None = None):
        self.db = db
        self.learning_repo = LearningRepository(db)
        self.ai_provider = ai_provider or GeminiProvider()

    async def explain_lesson(
        self,
        payload: AILessonExplainRequest,
    ) -> AILessonExplainResponse:
        """Generate a structured, style-tailored explanation of a lesson."""
        if not payload.lesson_id:
            raise BadRequestException("lesson_id is required to explain a lesson")

        lesson = await self.learning_repo.get_lesson_by_id(payload.lesson_id)
        if not lesson:
            raise NotFoundException(f"Lesson '{payload.lesson_id}' not found")

        prompt = build_lesson_explanation_prompt(
            lesson_title=lesson.title,
            lesson_content=lesson.content,
            style=payload.style.value,
            focus_question=payload.focus_question,
        )

        result = await self.ai_provider.explain_lesson(
            prompt=prompt,
            lesson_title=lesson.title,
            style=payload.style,
        )

        return AILessonExplainResponse(
            lesson_id=lesson.id,
            lesson_title=lesson.title,
            style=payload.style,
            explanation=result.explanation,
            key_takeaways=result.key_takeaways,
            code_example=result.code_example,
            suggested_followups=result.suggested_followups,
        )

    async def tutor_chat(
        self,
        payload: AITutorChatRequest,
    ) -> AITutorChatResponse:
        """Engage in interactive Socratic tutoring, optionally grounded in lesson content."""
        lesson_title = None
        lesson_content = None

        if payload.lesson_id:
            lesson = await self.learning_repo.get_lesson_by_id(payload.lesson_id)
            if lesson:
                lesson_title = lesson.title
                lesson_content = lesson.content

        history_dicts = [msg.model_dump() for msg in payload.history]

        prompt = build_socratic_tutor_prompt(
            message=payload.message,
            lesson_title=lesson_title,
            lesson_content=lesson_content,
            history=history_dicts,
        )

        result = await self.ai_provider.tutor_chat(
            prompt=prompt,
            user_message=payload.message,
        )

        return AITutorChatResponse(
            reply=result.reply,
            socratic_question=result.socratic_question,
            suggested_topics=result.suggested_topics,
        )
