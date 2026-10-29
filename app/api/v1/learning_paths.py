from typing import Annotated, List
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.learning_path import (
    LearningPathCreate,
    LearningPathDetailResponse,
    LearningPathResponse,
    LearningPathUpdate,
)
from app.services.learning_service import LearningService

router = APIRouter(prefix="/learning-paths", tags=["Learning Paths"])


@router.post(
    "",
    response_model=LearningPathDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a personalized learning path",
)
async def create_learning_path(
    payload: LearningPathCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LearningPathDetailResponse:
    """Create a new learning path with optional lessons for the current user."""
    service = LearningService(db)
    return await service.create_learning_path(user_id=current_user.id, payload=payload)


@router.get(
    "",
    response_model=List[LearningPathResponse],
    status_code=status.HTTP_200_OK,
    summary="List learning paths for current user",
)
async def list_learning_paths(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> List[LearningPathResponse]:
    """Retrieve all learning paths owned by the authenticated user."""
    service = LearningService(db)
    return await service.list_learning_paths(user_id=current_user.id, skip=skip, limit=limit)


@router.get(
    "/{path_id}",
    response_model=LearningPathDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get learning path detail by ID",
)
async def get_learning_path(
    path_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LearningPathDetailResponse:
    """
    Retrieve full details of a learning path including items and lesson metadata.
    Enforces row-level ownership: returns 404 if path belongs to another user.
    """
    service = LearningService(db)
    return await service.get_learning_path(path_id=path_id, user_id=current_user.id)


@router.patch(
    "/{path_id}",
    response_model=LearningPathResponse,
    status_code=status.HTTP_200_OK,
    summary="Update learning path metadata",
)
async def update_learning_path(
    path_id: str,
    payload: LearningPathUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LearningPathResponse:
    """
    Update learning path title, goal, status, total_days, or daily_minutes.
    Enforces row-level ownership: returns 404 if path belongs to another user.
    """
    service = LearningService(db)
    return await service.update_learning_path(path_id=path_id, user_id=current_user.id, payload=payload)


@router.delete(
    "/{path_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a learning path",
)
async def delete_learning_path(
    path_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """
    Delete a learning path.
    Enforces row-level ownership: returns 404 if path belongs to another user.
    """
    service = LearningService(db)
    await service.delete_learning_path(path_id=path_id, user_id=current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
