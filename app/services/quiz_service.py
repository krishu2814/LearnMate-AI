from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.models.course import DifficultyLevel
from app.models.quiz import QuizAnswer, QuizAttempt
from app.repositories.quiz_repo import QuizRepository
from app.schemas.quiz import (
    PaginatedQuizAttemptsResponse,
    QuizAnswerResultResponse,
    QuizAttemptCreate,
    QuizAttemptResponse,
    QuizAttemptSummaryResponse,
    QuizDetailResponse,
    QuizQuestionResponse,
    QuizResponse,
)


class QuizService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = QuizRepository(db)

    async def list_quizzes(
        self,
        topic: Optional[str] = None,
        difficulty: Optional[DifficultyLevel] = None,
        lesson_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[QuizResponse]:
        quizzes = await self.repo.list_quizzes(
            topic=topic,
            difficulty=difficulty,
            lesson_id=lesson_id,
            skip=skip,
            limit=limit,
        )
        return [QuizResponse.model_validate(q) for q in quizzes]

    async def get_quiz(self, quiz_id: str) -> QuizDetailResponse:
        quiz = await self.repo.get_quiz_by_id(quiz_id)
        if not quiz:
            raise NotFoundException(f"Quiz '{quiz_id}' not found")

        questions = [
            QuizQuestionResponse.model_validate(q)
            for q in sorted(quiz.questions, key=lambda x: x.position)
        ]
        return QuizDetailResponse(
            id=quiz.id,
            title=quiz.title,
            topic=quiz.topic,
            difficulty=quiz.difficulty,
            question_count=len(questions),
            lesson_id=quiz.lesson_id,
            created_at=quiz.created_at,
            questions=questions,
        )

    async def submit_quiz_attempt(
        self,
        quiz_id: str,
        user_id: str,
        payload: QuizAttemptCreate,
    ) -> QuizAttemptResponse:
        quiz = await self.repo.get_quiz_by_id(quiz_id)
        if not quiz:
            raise NotFoundException(f"Quiz '{quiz_id}' not found")

        if not quiz.questions:
            raise BadRequestException("Cannot submit attempt for a quiz with no questions")

        question_map = {q.id: q for q in quiz.questions}
        seen_question_ids = set()

        for ans in payload.answers:
            if ans.question_id not in question_map:
                raise BadRequestException(f"Question '{ans.question_id}' does not belong to quiz '{quiz_id}'")
            if ans.question_id in seen_question_ids:
                raise BadRequestException(f"Duplicate answer submitted for question '{ans.question_id}'")
            seen_question_ids.add(ans.question_id)

        # Grade submitted answers
        submitted_answers_map = {ans.question_id: ans.user_answer for ans in payload.answers}
        total_questions = len(quiz.questions)
        correct_count = 0
        answer_entities: List[QuizAnswer] = []
        answer_results: List[QuizAnswerResultResponse] = []

        for q in sorted(quiz.questions, key=lambda x: x.position):
            user_ans = submitted_answers_map.get(q.id, "")
            is_correct = (
                user_ans.strip().lower() == q.correct_answer.strip().lower()
                if user_ans
                else False
            )
            if is_correct:
                correct_count += 1

            ans_entity = QuizAnswer(
                attempt_id="",
                question_id=q.id,
                user_answer=user_ans,
                is_correct=is_correct,
            )
            ans_entity.question = q
            answer_entities.append(ans_entity)

            answer_results.append(
                QuizAnswerResultResponse(
                    question_id=q.id,
                    user_answer=user_ans,
                    is_correct=is_correct,
                    correct_answer=q.correct_answer,
                    explanation=q.explanation,
                )
            )

        score = round((correct_count / total_questions) * 100.0, 2) if total_questions > 0 else 0.0

        attempt = QuizAttempt(
            quiz_id=quiz.id,
            user_id=user_id,
            score=score,
            total_questions=total_questions,
            correct_count=correct_count,
            time_seconds=payload.time_seconds,
            is_exam_mode=payload.is_exam_mode,
        )

        for ans_entity in answer_entities:
            ans_entity.attempt_id = attempt.id
            attempt.answers.append(ans_entity)

        await self.repo.create_attempt(attempt)
        await self.db.commit()

        return QuizAttemptResponse(
            id=attempt.id,
            quiz_id=attempt.quiz_id,
            user_id=attempt.user_id,
            score=attempt.score,
            total_questions=attempt.total_questions,
            correct_count=attempt.correct_count,
            time_seconds=attempt.time_seconds,
            is_exam_mode=attempt.is_exam_mode,
            submitted_at=attempt.submitted_at,
            answers=answer_results,
        )

    async def get_quiz_attempts_history(
        self,
        quiz_id: str,
        user_id: str,
        page: int = 1,
        per_page: int = 20,
    ) -> PaginatedQuizAttemptsResponse:
        quiz = await self.repo.get_quiz_by_id(quiz_id)
        if not quiz:
            raise NotFoundException(f"Quiz '{quiz_id}' not found")

        skip = (page - 1) * per_page
        attempts, total = await self.repo.list_attempts_for_quiz(
            quiz_id=quiz_id,
            user_id=user_id,
            skip=skip,
            limit=per_page,
        )

        items = [QuizAttemptSummaryResponse.model_validate(a) for a in attempts]
        return PaginatedQuizAttemptsResponse(
            total=total,
            page=page,
            per_page=per_page,
            items=items,
        )
