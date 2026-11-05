from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.ai import (
    AIEvaluateAnswerRequest,
    AIEvaluateAnswerResponse,
    AILearningPathGenerateRequest,
    AILearningPathGenerateResponse,
    AILessonExplainRequest,
    AILessonExplainResponse,
    AIQuizGenerateRequest,
    AITutorChatRequest,
    AITutorChatResponse,
)
from app.schemas.quiz import QuizDetailResponse
from app.services.ai_learning_path_service import AILearningPathService
from app.services.ai_quiz_service import AIQuizService
from app.services.ai_tutor_service import AITutorService

router = APIRouter(prefix="/ai", tags=["AI Assessment & Learning"])


@router.post(
    "/quizzes/generate",
    response_model=QuizDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate an adaptive assessment quiz using Gemini AI",
)
async def generate_quiz(
    payload: AIQuizGenerateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> QuizDetailResponse:
    """
    Generate an AI-powered quiz with structured schema output.
    Optionally grounds questions in specific lesson content or generates from broad topic.
    Persists the created quiz and question set, returning the full assessment for test-takers.
    """
    service = AIQuizService(db)
    return await service.generate_quiz(user_id=current_user.id, payload=payload)


@router.post(
    "/quizzes/evaluate-answer",
    response_model=AIEvaluateAnswerResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate student response with AI semantic confidence and pedagogical feedback",
)
async def evaluate_answer(
    payload: AIEvaluateAnswerRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AIEvaluateAnswerResponse:
    """
    Evaluate student's answer using Gemini AI semantic reasoning.
    Returns correctness boolean, confidence score (0.0-1.0), and constructive feedback.
    """
    service = AIQuizService(db)
    return await service.evaluate_single_answer(payload=payload)


@router.post(
    "/learning-paths/generate",
    response_model=AILearningPathGenerateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a personalized curriculum and learning roadmap",
)
async def generate_learning_path(
    payload: AILearningPathGenerateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AILearningPathGenerateResponse:
    """
    Synthesize learner goals, current skill level, and schedule constraints into
    an optimal learning path grounded in the catalog of published courses and lessons.
    Persists the LearningPath and ordered LearningPathItems for the user.
    """
    service = AILearningPathService(db)
    return await service.generate_learning_path(user_id=current_user.id, payload=payload)


@router.post(
    "/lessons/{lesson_id}/explain",
    response_model=AILessonExplainResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate multi-style pedagogical explanation of a lesson",
)
async def explain_lesson(
    lesson_id: str,
    payload: AILessonExplainRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AILessonExplainResponse:
    """
    Generate an in-depth pedagogical explanation of lesson concepts tailored to
    different learning styles (beginner/ELI5, deep_dive, analogy, or practical).
    """
    payload.lesson_id = lesson_id
    service = AITutorService(db)
    return await service.explain_lesson(payload=payload)


@router.post(
    "/tutor/chat",
    response_model=AITutorChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Interactive Socratic tutor chat session",
)
async def tutor_chat(
    payload: AITutorChatRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AITutorChatResponse:
    """
    Interactive Socratic engineering mentor.
    Answers technical questions, checks student understanding, and suggests next topics.
    """
    service = AITutorService(db)
    return await service.tutor_chat(payload=payload)
