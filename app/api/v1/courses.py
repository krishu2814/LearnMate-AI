from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.course import DifficultyLevel
from app.schemas.course import CourseDetailResponse, CourseResponse
from app.services.learning_service import LearningService

router = APIRouter(prefix="/courses", tags=["Courses"])


@router.get(
    "",
    response_model=List[CourseResponse],
    status_code=status.HTTP_200_OK,
    summary="List all published courses",
)
async def list_courses(
    db: Annotated[AsyncSession, Depends(get_db)],
    difficulty: Optional[DifficultyLevel] = Query(None, description="Filter by difficulty level"),
    subject_tag: Optional[str] = Query(None, description="Filter by subject tag"),
) -> List[CourseResponse]:
    """Retrieve catalog of published courses with optional filtering."""
    service = LearningService(db)
    return await service.get_courses(difficulty=difficulty, subject_tag=subject_tag)


@router.get(
    "/{course_id}",
    response_model=CourseDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get course details with modules and lessons",
)
async def get_course_detail(
    course_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CourseDetailResponse:
    """Retrieve full details of a course including modules and lessons."""
    service = LearningService(db)
    return await service.get_course(course_id)
