from typing import Annotated
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.progress import DashboardProgressResponse
from app.services.learning_service import LearningService

router = APIRouter(prefix="/progress", tags=["Progress Dashboard"])


@router.get(
    "",
    response_model=DashboardProgressResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user learning progress dashboard summary",
)
async def get_my_dashboard_progress(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DashboardProgressResponse:
    """
    Retrieve comprehensive progress dashboard metrics:
    - Total lessons, completed count, completion percentages
    - Total study duration (seconds & minutes)
    - Per-course progress breakdown
    - Active learning path progression status
    """
    service = LearningService(db)
    return await service.get_dashboard_progress(user_id=current_user.id)
