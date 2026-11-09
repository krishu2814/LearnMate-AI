from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.prompts.remediation_prompts import build_remediation_quiz_prompt
from app.ai.providers.gemini import GeminiProvider
from app.core.exceptions import NotFoundException
from app.core.logging import logger
from app.models.quiz import Quiz, QuizQuestion
from app.repositories.quiz_repo import QuizRepository
from app.repositories.srs_repo import SRSRepository
from app.schemas.quiz import QuizDetailResponse, QuizQuestionResponse
from app.schemas.srs import (
    RemediationQuizRequest,
    ReviewItemResponse,
    ReviewQuestionResponse,
    ReviewQueueResponse,
    ReviewResultResponse,
    SubmitReviewRequest,
    WeakTopicSummary,
)


class SRSService:
    """Service orchestrating Spaced Repetition reviews and AI-driven weakness remediation."""

    def __init__(self, db: AsyncSession, ai_provider: GeminiProvider | None = None):
        self.db = db
        self.srs_repo = SRSRepository(db)
        self.quiz_repo = QuizRepository(db)
        self.ai_provider = ai_provider or GeminiProvider()

    async def get_review_queue(self, user_id: str) -> ReviewQueueResponse:
        """Fetch questions currently due for spaced repetition review for the authenticated student."""
        due_items = await self.srs_repo.get_due_items(user_id=user_id)
        due_count = await self.srs_repo.count_due_items(user_id=user_id)
        total_count = await self.srs_repo.count_total_items(user_id=user_id)
        weak_topics_data = await self.srs_repo.get_user_weak_topics(user_id=user_id)

        weak_topics = [
            WeakTopicSummary(topic=wt["topic"], missed_count=wt["missed_count"])
            for wt in weak_topics_data
        ]

        item_responses: list[ReviewItemResponse] = []
        for it in due_items:
            q_resp = ReviewQuestionResponse(
                id=it.question.id,
                question=it.question.question,
                question_type=it.question.question_type,
                options=it.question.options,
                topic_tag=it.question.topic_tag or it.topic_tag,
            )
            item_responses.append(
                ReviewItemResponse(
                    id=it.id,
                    question_id=it.question_id,
                    topic_tag=it.topic_tag,
                    interval_days=it.interval_days,
                    repetitions=it.repetitions,
                    ease_factor=it.ease_factor,
                    next_review_at=it.next_review_at,
                    last_reviewed_at=it.last_reviewed_at,
                    consecutive_correct=it.consecutive_correct,
                    question=q_resp,
                )
            )

        return ReviewQueueResponse(
            due_count=due_count,
            total_tracked_count=total_count,
            weak_topics=weak_topics,
            items=item_responses,
        )

    async def submit_review(
        self,
        user_id: str,
        item_id: str,
        payload: SubmitReviewRequest,
    ) -> ReviewResultResponse:
        """
        Evaluate student recall for a spaced repetition item and update SM-2 parameters.
        Enforces strict row-level ownership.
        """
        item = await self.srs_repo.get_item_by_id(item_id=item_id, user_id=user_id)
        if not item:
            raise NotFoundException(f"Review item '{item_id}' not found")

        is_correct = (
            payload.user_answer.strip().lower() == item.question.correct_answer.strip().lower()
        )

        await self.srs_repo.record_review_result(item=item, is_correct=is_correct)
        await self.db.commit()

        logger.info(
            "srs_review_recorded",
            user_id=user_id,
            item_id=item.id,
            is_correct=is_correct,
            new_interval=item.interval_days,
            repetitions=item.repetitions,
        )

        return ReviewResultResponse(
            item_id=item.id,
            is_correct=is_correct,
            correct_answer=item.question.correct_answer,
            explanation=item.question.explanation,
            new_interval_days=item.interval_days,
            new_repetitions=item.repetitions,
            next_review_at=item.next_review_at,
        )

    async def generate_remediation_quiz(
        self,
        user_id: str,
        payload: RemediationQuizRequest,
    ) -> QuizDetailResponse:
        """
        Synthesize student weakness history into an AI-generated targeted assessment.
        """
        weak_topics_data = await self.srs_repo.get_user_weak_topics(user_id=user_id)
        missed_questions = await self.srs_repo.get_recent_missed_questions(user_id=user_id)

        weak_topics = [wt["topic"] for wt in weak_topics_data if wt["topic"]]
        fallback_topic = weak_topics[0] if weak_topics else "General Knowledge & Engineering"

        missed_context = [
            {
                "topic_tag": q.topic_tag or fallback_topic,
                "question": q.question,
                "correct_answer": q.correct_answer,
                "explanation": q.explanation or "",
            }
            for q in missed_questions
        ]

        prompt = build_remediation_quiz_prompt(
            weak_topics=weak_topics,
            missed_questions=missed_context,
            num_questions=payload.num_questions,
            difficulty=payload.difficulty,
        )

        generated = await self.ai_provider.generate_quiz(
            prompt=prompt,
            fallback_topic=fallback_topic,
            fallback_difficulty=payload.difficulty,
            fallback_count=payload.num_questions,
        )

        quiz = Quiz(
            title=f"Remediation: {generated.title}",
            topic=generated.topic,
            difficulty=generated.difficulty,
            user_id=user_id,
            question_count=len(generated.questions),
            prompt_version="remediation-gemini-v1",
        )

        for idx, q_data in enumerate(generated.questions):
            q_entity = QuizQuestion(
                quiz_id=quiz.id,
                question=q_data.question,
                question_type=q_data.question_type,
                options=q_data.options,
                correct_answer=q_data.correct_answer,
                explanation=q_data.explanation,
                topic_tag=q_data.topic_tag or generated.topic,
                position=idx + 1,
            )
            quiz.questions.append(q_entity)

        self.db.add(quiz)
        await self.db.commit()
        await self.db.refresh(quiz)

        logger.info(
            "remediation_quiz_generated",
            user_id=user_id,
            quiz_id=quiz.id,
            question_count=len(quiz.questions),
        )

        return QuizDetailResponse(
            id=quiz.id,
            title=quiz.title,
            topic=quiz.topic,
            difficulty=quiz.difficulty,
            user_id=quiz.user_id,
            lesson_id=quiz.lesson_id,
            question_count=quiz.question_count,
            created_at=quiz.created_at,
            questions=[
                QuizQuestionResponse(
                    id=q.id,
                    quiz_id=q.quiz_id,
                    question=q.question,
                    question_type=q.question_type,
                    options=q.options,
                    position=q.position,
                    topic_tag=q.topic_tag,
                )
                for q in quiz.questions
            ],
        )
