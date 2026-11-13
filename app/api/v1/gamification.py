from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.gamification import (
    BadgeResponse,
    GamificationProfileResponse,
    LeaderboardResponse,
    SyncGamificationResponse,
)
from app.services.gamification_service import GamificationService

router = APIRouter(prefix="/gamification", tags=["Gamification, Streaks & Badges"])


@router.get(
    "/profile",
    response_model=GamificationProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get learner gamification profile, XP, level, and active streak",
)
async def get_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GamificationProfileResponse:
    """
    Retrieve current student's XP, computed RPG level, level completion percentage,
    consecutive study day streak, and recent achievement badges.
    """
    service = GamificationService(db)
    return await service.get_profile(user_id=current_user.id)


@router.get(
    "/badges",
    response_model=list[BadgeResponse],
    status_code=status.HTTP_200_OK,
    summary="List all achievement badges with student unlock status",
)
async def list_badges(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[BadgeResponse]:
    """
    Browse the complete catalog of achievement badges, displaying unlocked status
    and completion dates for earned awards.
    """
    service = GamificationService(db)
    return await service.list_badges(user_id=current_user.id)


@router.get(
    "/leaderboard",
    response_model=LeaderboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Get global student leaderboard ranked by total XP",
)
async def get_leaderboard(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=20, ge=1, le=100, description="Top rank limit"),
) -> LeaderboardResponse:
    """
    Fetch the competitive leaderboard of learners ranked by XP, including
    the authenticated user's specific rank standing.
    """
    service = GamificationService(db)
    return await service.get_leaderboard(current_user_id=current_user.id, limit=limit)


@router.post(
    "/sync",
    response_model=SyncGamificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Synchronize achievements, evaluate badge criteria, and update streaks",
)
async def sync_gamification(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SyncGamificationResponse:
    """
    Audit learner activity (completed lessons, quiz attempts, SRS reviews, code submissions),
    increment daily streak if active today, award newly eligible badges, and recalculate level.
    """
    service = GamificationService(db)
    return await service.record_activity_and_sync(user_id=current_user.id)
