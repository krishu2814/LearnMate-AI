from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.code import (
    CodeReviewRequest,
    CodeSubmissionResponse,
    CodingExerciseResponse,
    GenerateExerciseRequest,
)
from app.services.code_service import CodeService

router = APIRouter(prefix="/code", tags=["AI Code Playground & Exercise Evaluator"])


@router.post(
    "/review",
    response_model=CodeSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit code for AI architectural review and complexity analysis",
)
async def review_code(
    payload: CodeReviewRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CodeSubmissionResponse:
    """
    Evaluate user-submitted source code for algorithmic time/space complexity,
    architectural code quality, security/anti-patterns, and provide refactored suggestions.
    Saves the submission to the student's portfolio.
    """
    service = CodeService(db)
    return await service.review_code(user_id=current_user.id, payload=payload)


@router.get(
    "/submissions",
    response_model=list[CodeSubmissionResponse],
    status_code=status.HTTP_200_OK,
    summary="List past code submissions and evaluations",
)
async def list_submissions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(default=0, ge=0, description="Offset"),
    limit: int = Query(default=20, ge=1, le=100, description="Limit"),
) -> list[CodeSubmissionResponse]:
    """
    Retrieve historical code reviews and complexity evaluations for the authenticated learner.
    """
    service = CodeService(db)
    return await service.list_submissions(user_id=current_user.id, skip=skip, limit=limit)


@router.get(
    "/submissions/{submission_id}",
    response_model=CodeSubmissionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single code submission evaluation by ID",
)
async def get_submission(
    submission_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CodeSubmissionResponse:
    """
    Retrieve full details and AI review report of a specific code submission.
    Enforces strict row-level ownership.
    """
    service = CodeService(db)
    return await service.get_submission(user_id=current_user.id, submission_id=submission_id)


@router.post(
    "/exercises/generate",
    response_model=CodingExerciseResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate tailored hands-on coding challenge with test cases",
)
async def generate_exercise(
    payload: GenerateExerciseRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CodingExerciseResponse:
    """
    Dynamically craft an algorithmic or system-design coding challenge with
    starter boilerplate, test specifications, and progressive pedagogical hints.
    """
    service = CodeService(db)
    return await service.generate_exercise(payload=payload)
