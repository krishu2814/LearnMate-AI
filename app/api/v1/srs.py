from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.quiz import QuizDetailResponse
from app.schemas.srs import (
    RemediationQuizRequest,
    ReviewQueueResponse,
    ReviewResultResponse,
    SubmitReviewRequest,
)
from app.services.srs_service import SRSService

router = APIRouter(prefix="/srs", tags=["Spaced Repetition & Weakness Remediation"])


@router.get(
    "/queue",
    response_model=ReviewQueueResponse,
    status_code=status.HTTP_200_OK,
    summary="Get questions due for spaced repetition review",
)
async def get_review_queue(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReviewQueueResponse:
    """
    Retrieve questions currently scheduled for spaced repetition review according
    to the SM-2 algorithm. Includes weak topic analysis and question details.
    """
    service = SRSService(db)
    return await service.get_review_queue(user_id=current_user.id)


@router.post(
    "/items/{item_id}/review",
    response_model=ReviewResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit review answer for an SRS item",
)
async def submit_review(
    item_id: str,
    payload: SubmitReviewRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReviewResultResponse:
    """
    Submit a review answer for a spaced repetition item.
    Updates the SM-2 ease factor, interval, and schedules the next review date.
    Enforces row-level ownership.
    """
    service = SRSService(db)
    return await service.submit_review(
        user_id=current_user.id,
        item_id=item_id,
        payload=payload,
    )


@router.post(
    "/remediation/generate-quiz",
    response_model=QuizDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate an AI quiz targeting learner weaknesses",
)
async def generate_remediation_quiz(
    payload: RemediationQuizRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> QuizDetailResponse:
    """
    Synthesize past missed questions and weak conceptual topics into a tailored
    remediation quiz powered by Gemini AI.
    """
    service = SRSService(db)
    return await service.generate_remediation_quiz(
        user_id=current_user.id,
        payload=payload,
    )

