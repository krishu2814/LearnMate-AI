from typing import Annotated
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.course import LessonDetailResponse
from app.schemas.progress import LessonProgressResponse, LessonProgressUpdate
from app.services.learning_service import LearningService

router = APIRouter(prefix="/lessons", tags=["Lessons"])


@router.get(
    "/{lesson_id}",
    response_model=LessonDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get lesson content and details",
)
async def get_lesson(
    lesson_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LessonDetailResponse:
    """Retrieve full lesson metadata, learning content, and estimated duration."""
    service = LearningService(db)
    return await service.get_lesson(lesson_id)


@router.put(
    "/{lesson_id}/progress",
    response_model=LessonProgressResponse,
    status_code=status.HTTP_200_OK,
    summary="Update or mark lesson progress",
)
async def update_lesson_progress(
    lesson_id: str,
    payload: LessonProgressUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LessonProgressResponse:
    """
    Record progress for a lesson (not_started, in_progress, completed).
    When completed, automatically synchronizes learning path completion state.
    """
    service = LearningService(db)
    return await service.update_lesson_progress(
        user_id=current_user.id,
        lesson_id=lesson_id,
        payload=payload,
    )
