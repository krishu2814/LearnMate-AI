from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.ai import (
    AIEvaluateAnswerRequest,
    AIEvaluateAnswerResponse,
    AIQuizGenerateRequest,
)
from app.schemas.quiz import QuizDetailResponse
from app.services.ai_quiz_service import AIQuizService

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
