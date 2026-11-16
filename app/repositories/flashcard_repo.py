from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.flashcard import Flashcard, FlashcardDeck, MasteryStatus


class FlashcardRepository:
    """Repository handling database operations for flashcard decks and individual cards."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_deck(self, deck: FlashcardDeck) -> FlashcardDeck:
        """Persist a new flashcard deck and its initial cards."""
        self.db.add(deck)
        await self.db.flush()
        return deck

    async def get_deck_by_id(
        self,
        deck_id: str,
        user_id: str | None = None,
    ) -> FlashcardDeck | None:
        """
        Fetch deck by ID with all cards eager-loaded.
        If user_id is provided, enforces that the deck belongs to the user or is public.
        """
        query = (
            select(FlashcardDeck)
            .options(selectinload(FlashcardDeck.cards))
            .where(FlashcardDeck.id == deck_id)
        )
        if user_id:
            query = query.where(
                or_(
                    FlashcardDeck.user_id == user_id,
                    FlashcardDeck.is_public.is_(True),
                )
            )

        result = await self.db.execute(query)
        return result.scalars().first()

    async def list_user_decks(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
        topic: str | None = None,
        lesson_id: str | None = None,
    ) -> list[FlashcardDeck]:
        """List decks created by the learner with optional filtering."""
        query = (
            select(FlashcardDeck)
            .options(selectinload(FlashcardDeck.cards))
            .where(FlashcardDeck.user_id == user_id)
        )

        if topic:
            query = query.where(FlashcardDeck.topic.ilike(f"%{topic}%"))
        if lesson_id:
            query = query.where(FlashcardDeck.lesson_id == lesson_id)

        query = query.order_by(FlashcardDeck.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_user_decks(
        self,
        user_id: str,
        topic: str | None = None,
        lesson_id: str | None = None,
    ) -> int:
        """Count total decks matching filter criteria for pagination."""
        query = select(func.count(FlashcardDeck.id)).where(FlashcardDeck.user_id == user_id)
        if topic:
            query = query.where(FlashcardDeck.topic.ilike(f"%{topic}%"))
        if lesson_id:
            query = query.where(FlashcardDeck.lesson_id == lesson_id)

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def delete_deck(self, deck_id: str) -> None:
        """Delete deck and cascade all cards using core statement."""
        await self.db.execute(delete(FlashcardDeck).where(FlashcardDeck.id == deck_id))
        await self.db.flush()

    async def get_cards_by_deck_id(self, deck_id: str) -> list[Flashcard]:
        """Fetch all cards belonging to a deck ordered by Leitner box."""
        result = await self.db.execute(
            select(Flashcard)
            .where(Flashcard.deck_id == deck_id)
            .order_by(Flashcard.box.asc(), Flashcard.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_card_by_id(self, card_id: str) -> Flashcard | None:
        """Fetch a single card by its ID."""
        result = await self.db.execute(select(Flashcard).where(Flashcard.id == card_id))
        return result.scalars().first()

    async def get_deck_mastery_stats(self, deck_id: str) -> dict[str, int]:
        """Compute distribution of Leitner mastery across cards in a deck."""
        mastered_res = await self.db.execute(
            select(func.count(Flashcard.id)).where(
                Flashcard.deck_id == deck_id,
                Flashcard.mastery_status == MasteryStatus.MASTERED,
            )
        )
        learning_res = await self.db.execute(
            select(func.count(Flashcard.id)).where(
                Flashcard.deck_id == deck_id,
                Flashcard.mastery_status == MasteryStatus.LEARNING,
            )
        )
        new_res = await self.db.execute(
            select(func.count(Flashcard.id)).where(
                Flashcard.deck_id == deck_id,
                Flashcard.mastery_status == MasteryStatus.NEW,
            )
        )

        return {
            "mastered_count": mastered_res.scalar() or 0,
            "learning_count": learning_res.scalar() or 0,
            "new_count": new_res.scalar() or 0,
        }
