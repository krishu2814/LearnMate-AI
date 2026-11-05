from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.prompts.quiz_prompts import (
    build_answer_evaluation_prompt,
    build_quiz_generation_prompt,
)
from app.ai.providers.gemini import GeminiProvider
from app.core.exceptions import NotFoundException
from app.core.logging import logger
from app.models.quiz import Quiz, QuizQuestion
from app.repositories.learning_repo import LearningRepository
from app.repositories.quiz_repo import QuizRepository
from app.schemas.ai import (
    AIEvaluateAnswerRequest,
    AIEvaluateAnswerResponse,
    AIQuizGenerateRequest,
)
from app.schemas.quiz import QuizDetailResponse, QuizQuestionResponse


class AIQuizService:
    """Service for AI-powered adaptive quiz generation and intelligent answer assessment."""

    def __init__(self, db: AsyncSession, ai_provider: GeminiProvider | None = None):
        self.db = db
        self.quiz_repo = QuizRepository(db)
        self.learning_repo = LearningRepository(db)
        self.ai_provider = ai_provider or GeminiProvider()

    async def generate_quiz(
        self,
        user_id: str,
        payload: AIQuizGenerateRequest,
    ) -> QuizDetailResponse:
        """Generate a personalized assessment quiz from lesson content or broad topic."""
        lesson_title = None
        lesson_content = None

        if payload.lesson_id:
            lesson = await self.learning_repo.get_lesson_by_id(payload.lesson_id)
            if not lesson:
                raise NotFoundException(f"Lesson '{payload.lesson_id}' not found")
            lesson_title = lesson.title
            lesson_content = lesson.content

        prompt = build_quiz_generation_prompt(
            topic=payload.topic,
            difficulty=payload.difficulty,
            num_questions=payload.num_questions,
            lesson_title=lesson_title,
            lesson_content=lesson_content,
            allowed_types=payload.question_types,
            custom_instructions=payload.custom_instructions,
        )

        generated_payload = await self.ai_provider.generate_quiz(
            prompt=prompt,
            fallback_topic=payload.topic,
            fallback_difficulty=payload.difficulty,
            fallback_count=payload.num_questions,
        )

        # Persist generated quiz to database
        quiz = Quiz(
            title=generated_payload.title,
            topic=generated_payload.topic,
            difficulty=generated_payload.difficulty,
            user_id=user_id,
            lesson_id=payload.lesson_id,
            question_count=len(generated_payload.questions),
            prompt_version="gemini-2.5-flash-v1",
        )

        for idx, q_data in enumerate(generated_payload.questions):
            question_entity = QuizQuestion(
                quiz_id=quiz.id,
                question=q_data.question,
                question_type=q_data.question_type,
                options=q_data.options,
                correct_answer=q_data.correct_answer,
                explanation=q_data.explanation,
                topic_tag=q_data.topic_tag or generated_payload.topic,
                position=idx + 1,
            )
            quiz.questions.append(question_entity)

        self.db.add(quiz)
        await self.db.commit()
        await self.db.refresh(quiz)

        logger.info(
            "ai_quiz_generated_successfully",
            quiz_id=quiz.id,
            user_id=user_id,
            question_count=len(quiz.questions),
        )

        questions_response = [
            QuizQuestionResponse(
                id=q.id,
                question=q.question,
                question_type=q.question_type,
                options=q.options,
                position=q.position,
                topic_tag=q.topic_tag,
            )
            for q in sorted(quiz.questions, key=lambda x: x.position)
        ]

        return QuizDetailResponse(
            id=quiz.id,
            title=quiz.title,
            topic=quiz.topic,
            difficulty=quiz.difficulty,
            question_count=len(questions_response),
            lesson_id=quiz.lesson_id,
            created_at=quiz.created_at,
            questions=questions_response,
        )

    async def evaluate_single_answer(
        self,
        payload: AIEvaluateAnswerRequest,
    ) -> AIEvaluateAnswerResponse:
        """Perform semantic evaluation and AI pedagogical feedback on a student's answer."""
        question = await self.quiz_repo.get_question_by_id(payload.question_id)
        if not question:
            raise NotFoundException(f"Quiz question '{payload.question_id}' not found")

        prompt = build_answer_evaluation_prompt(
            question_text=question.question,
            question_type=question.question_type.value,
            correct_answer=question.correct_answer,
            user_answer=payload.user_answer,
            explanation=question.explanation,
        )

        eval_result = await self.ai_provider.evaluate_answer(
            prompt=prompt,
            expected_answer=question.correct_answer,
            user_answer=payload.user_answer,
        )

        return AIEvaluateAnswerResponse(
            question_id=question.id,
            user_answer=payload.user_answer,
            is_correct=eval_result.is_correct,
            ai_confidence=eval_result.confidence,
            ai_feedback=eval_result.feedback,
        )
