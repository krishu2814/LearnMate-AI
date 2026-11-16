from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.flashcard import (
    AIGenerateDeckRequest,
    FlashcardDeckCreate,
    FlashcardDeckDetailResponse,
    FlashcardDeckResponse,
    FlashcardDeckUpdate,
    StudySessionResponse,
    StudySessionSubmission,
)
from app.services.flashcard_service import FlashcardService

router = APIRouter(prefix="/flashcards", tags=["Active Recall Flashcard Decks Studio"])


@router.post(
    "/generate",
    response_model=FlashcardDeckDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate an active recall flashcard deck with Gemini",
)
async def generate_ai_deck(
    payload: AIGenerateDeckRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FlashcardDeckDetailResponse:
    """
    Synthesize high-yield, atomic flashcards grounded in lesson content or custom technical topics.
    Returns the newly created deck and all generated cards.
    """
    service = FlashcardService(db)
    return await service.generate_ai_deck(user_id=current_user.id, payload=payload)


@router.post(
    "/decks",
    response_model=FlashcardDeckDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Manually create a new flashcard deck with cards",
)
async def create_deck(
    payload: FlashcardDeckCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FlashcardDeckDetailResponse:
    """
    Create a custom active recall flashcard deck. Optionally attaches to a curriculum lesson.
    """
    service = FlashcardService(db)
    return await service.create_deck(user_id=current_user.id, payload=payload)


@router.get(
    "/decks",
    response_model=list[FlashcardDeckResponse],
    status_code=status.HTTP_200_OK,
    summary="List learner flashcard decks with Leitner mastery stats",
)
async def list_decks(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(default=0, ge=0, description="Offset"),
    limit: int = Query(default=20, ge=1, le=100, description="Limit"),
    topic: str | None = Query(default=None, description="Filter by topic keyword"),
    lesson_id: str | None = Query(default=None, description="Filter by lesson ID"),
) -> list[FlashcardDeckResponse]:
    """
    Browse student's flashcard decks with distribution metrics across Leitner mastery stages
    (mastered, learning, new).
    """
    service = FlashcardService(db)
    return await service.list_decks(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        topic=topic,
        lesson_id=lesson_id,
    )


@router.get(
    "/decks/{deck_id}",
    response_model=FlashcardDeckDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get full flashcard deck with all contained cards",
)
async def get_deck(
    deck_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FlashcardDeckDetailResponse:
    """
    Retrieve deck metadata, Leitner mastery breakdown, and complete card list.
    Enforces row-level ownership.
    """
    service = FlashcardService(db)
    return await service.get_deck_detail(user_id=current_user.id, deck_id=deck_id)


@router.patch(
    "/decks/{deck_id}",
    response_model=FlashcardDeckDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Update deck metadata",
)
async def update_deck(
    deck_id: str,
    payload: FlashcardDeckUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FlashcardDeckDetailResponse:
    """
    Modify deck title, topic, description, or visibility status.
    """
    service = FlashcardService(db)
    return await service.update_deck(user_id=current_user.id, deck_id=deck_id, payload=payload)


@router.delete(
    "/decks/{deck_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a flashcard deck and its cards",
)
async def delete_deck(
    deck_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    Permanently delete a flashcard deck and all its contained cards.
    """
    service = FlashcardService(db)
    await service.delete_deck(user_id=current_user.id, deck_id=deck_id)


@router.post(
    "/decks/{deck_id}/study",
    response_model=StudySessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit card self-assessment ratings for Leitner box transitions",
)
async def submit_study_session(
    deck_id: str,
    payload: StudySessionSubmission,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StudySessionResponse:
    """
    Submit active recall study session ratings (1=Again, 2=Hard, 3=Good, 4=Easy).
    Calculates Leitner box promotions/demotions, updates mastery status, awards gamification XP,
    and increments daily study streak.
    """
    service = FlashcardService(db)
    return await service.study_deck_session(
        user_id=current_user.id,
        deck_id=deck_id,
        payload=payload,
    )
