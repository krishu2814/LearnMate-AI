from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.course import DifficultyLevel
from app.models.user import User
from app.schemas.quiz import (
    PaginatedQuizAttemptsResponse,
    QuizAttemptCreate,
    QuizAttemptResponse,
    QuizDetailResponse,
    QuizResponse,
)
from app.services.quiz_service import QuizService

router = APIRouter(prefix="/quizzes", tags=["Quizzes"])


@router.get(
    "",
    response_model=List[QuizResponse],
    status_code=status.HTTP_200_OK,
    summary="List quizzes",
)
async def list_quizzes(
    db: Annotated[AsyncSession, Depends(get_db)],
    topic: Optional[str] = Query(None, description="Filter by topic"),
    difficulty: Optional[DifficultyLevel] = Query(None, description="Filter by difficulty level"),
    lesson_id: Optional[str] = Query(None, description="Filter by lesson ID"),
    skip: int = Query(0, ge=0, description="Pagination skip"),
    limit: int = Query(50, ge=1, le=100, description="Pagination limit"),
) -> List[QuizResponse]:
    """Retrieve catalog of available quizzes with optional filters."""
    service = QuizService(db)
    return await service.list_quizzes(
        topic=topic,
        difficulty=difficulty,
        lesson_id=lesson_id,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{quiz_id}",
    response_model=QuizDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get quiz questions and details",
)
async def get_quiz(
    quiz_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> QuizDetailResponse:
    """Retrieve quiz metadata and question set (correct answers excluded for test takers)."""
    service = QuizService(db)
    return await service.get_quiz(quiz_id)


@router.post(
    "/{quiz_id}/attempts",
    response_model=QuizAttemptResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit and score quiz attempt",
)
async def submit_quiz_attempt(
    quiz_id: str,
    payload: QuizAttemptCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> QuizAttemptResponse:
    """
    Submit answers for a quiz attempt.
    Scores each question immediately, records attempt history, and returns full score breakdown with explanations.
    """
    service = QuizService(db)
    return await service.submit_quiz_attempt(
        quiz_id=quiz_id,
        user_id=current_user.id,
        payload=payload,
    )


@router.get(
    "/{quiz_id}/attempts",
    response_model=PaginatedQuizAttemptsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get quiz attempt history for current user",
)
async def get_quiz_attempts_history(
    quiz_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
) -> PaginatedQuizAttemptsResponse:
    """Retrieve paginated attempt history for the authenticated user for a specific quiz."""
    service = QuizService(db)
    return await service.get_quiz_attempts_history(
        quiz_id=quiz_id,
        user_id=current_user.id,
        page=page,
        per_page=per_page,
    )
