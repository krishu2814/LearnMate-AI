from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.prompts.flashcard_prompts import build_flashcard_generation_prompt
from app.ai.providers.gemini import GeminiProvider
from app.core.exceptions import BadRequestException, NotFoundException
from app.core.logging import logger
from app.models.flashcard import Flashcard, FlashcardDeck, MasteryStatus
from app.repositories.flashcard_repo import FlashcardRepository
from app.repositories.learning_repo import LearningRepository
from app.schemas.flashcard import (
    AIGenerateDeckRequest,
    CardReviewResult,
    FlashcardDeckCreate,
    FlashcardDeckDetailResponse,
    FlashcardDeckResponse,
    FlashcardDeckUpdate,
    FlashcardResponse,
    StudySessionResponse,
    StudySessionSubmission,
)
from app.services.gamification_service import GamificationService


class FlashcardService:
    """Orchestrates active recall deck generation, Leitner review sessions, and mastery tracking."""

    def __init__(self, db: AsyncSession, ai_provider: GeminiProvider | None = None):
        self.db = db
        self.repo = FlashcardRepository(db)
        self.learning_repo = LearningRepository(db)
        self.ai_provider = ai_provider or GeminiProvider()
        self.gamification_service = GamificationService(db)

    async def create_deck(
        self,
        user_id: str,
        payload: FlashcardDeckCreate,
    ) -> FlashcardDeckDetailResponse:
        """Manually author an active recall flashcard deck with custom cards."""
        if payload.lesson_id:
            lesson = await self.learning_repo.get_lesson_by_id(payload.lesson_id)
            if not lesson:
                raise NotFoundException(f"Lesson '{payload.lesson_id}' not found")

        deck = FlashcardDeck(
            user_id=user_id,
            title=payload.title,
            topic=payload.topic,
            description=payload.description,
            lesson_id=payload.lesson_id,
            is_public=payload.is_public,
        )

        for card_data in payload.cards:
            card = Flashcard(
                deck_id=deck.id,
                front=card_data.front,
                back=card_data.back,
                hint=card_data.hint,
                key_concept=card_data.key_concept,
                box=1,
                mastery_status=MasteryStatus.NEW,
            )
            deck.cards.append(card)

        deck.card_count = len(deck.cards)
        await self.repo.create_deck(deck)
        await self.db.commit()

        logger.info(
            "flashcard_deck_created",
            deck_id=deck.id,
            user_id=user_id,
            card_count=deck.card_count,
        )

        return await self._format_deck_detail_response(deck)

    async def generate_ai_deck(
        self,
        user_id: str,
        payload: AIGenerateDeckRequest,
    ) -> FlashcardDeckDetailResponse:
        """Generate high-yield active recall deck using Gemini structured JSON outputs."""
        lesson_title = None
        lesson_content = None

        if payload.lesson_id:
            lesson = await self.learning_repo.get_lesson_by_id(payload.lesson_id)
            if not lesson:
                raise NotFoundException(f"Lesson '{payload.lesson_id}' not found")
            lesson_title = lesson.title
            lesson_content = lesson.content

        prompt = build_flashcard_generation_prompt(
            topic=payload.topic,
            num_cards=payload.num_cards,
            difficulty=payload.difficulty,
            lesson_title=lesson_title,
            lesson_content=lesson_content,
            custom_instructions=payload.custom_instructions,
        )

        ai_payload = await self.ai_provider.generate_flashcards(
            prompt=prompt,
            topic=payload.topic,
            count=payload.num_cards,
            difficulty=payload.difficulty,
        )

        deck = FlashcardDeck(
            user_id=user_id,
            title=ai_payload.title,
            topic=ai_payload.topic,
            description=ai_payload.description,
            lesson_id=payload.lesson_id,
            is_public=False,
        )

        for card_data in ai_payload.cards:
            card = Flashcard(
                deck_id=deck.id,
                front=card_data.front,
                back=card_data.back,
                hint=card_data.hint,
                key_concept=card_data.key_concept,
                box=1,
                mastery_status=MasteryStatus.NEW,
            )
            deck.cards.append(card)

        deck.card_count = len(deck.cards)
        await self.repo.create_deck(deck)
        await self.db.commit()

        logger.info(
            "ai_flashcard_deck_generated",
            deck_id=deck.id,
            user_id=user_id,
            topic=deck.topic,
            cards_count=deck.card_count,
        )

        return await self._format_deck_detail_response(deck)

    async def get_deck_detail(
        self,
        user_id: str,
        deck_id: str,
    ) -> FlashcardDeckDetailResponse:
        """Fetch a specific flashcard deck and its cards with ownership enforcement."""
        deck = await self.repo.get_deck_by_id(deck_id=deck_id, user_id=user_id)
        if not deck:
            raise NotFoundException(f"Flashcard deck '{deck_id}' not found")

        return await self._format_deck_detail_response(deck)

    async def list_decks(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
        topic: str | None = None,
        lesson_id: str | None = None,
    ) -> list[FlashcardDeckResponse]:
        """List flashcard decks for the current user with aggregated Leitner mastery stats."""
        decks = await self.repo.list_user_decks(
            user_id=user_id,
            skip=skip,
            limit=limit,
            topic=topic,
            lesson_id=lesson_id,
        )

        responses: list[FlashcardDeckResponse] = []
        for deck in decks:
            stats = await self.repo.get_deck_mastery_stats(deck.id)
            responses.append(
                FlashcardDeckResponse(
                    id=deck.id,
                    user_id=deck.user_id,
                    lesson_id=deck.lesson_id,
                    title=deck.title,
                    description=deck.description,
                    topic=deck.topic,
                    card_count=deck.card_count,
                    is_public=deck.is_public,
                    mastered_count=stats["mastered_count"],
                    learning_count=stats["learning_count"],
                    new_count=stats["new_count"],
                    created_at=deck.created_at,
                    updated_at=deck.updated_at,
                )
            )
        return responses

    async def update_deck(
        self,
        user_id: str,
        deck_id: str,
        payload: FlashcardDeckUpdate,
    ) -> FlashcardDeckDetailResponse:
        """Update deck metadata with strict row-level ownership check."""
        deck = await self.repo.get_deck_by_id(deck_id=deck_id, user_id=user_id)
        if not deck or deck.user_id != user_id:
            raise NotFoundException(f"Flashcard deck '{deck_id}' not found")

        if payload.title is not None:
            deck.title = payload.title
        if payload.topic is not None:
            deck.topic = payload.topic
        if payload.description is not None:
            deck.description = payload.description
        if payload.is_public is not None:
            deck.is_public = payload.is_public

        await self.db.commit()
        return await self._format_deck_detail_response(deck)

    async def delete_deck(self, user_id: str, deck_id: str) -> None:
        """Delete flashcard deck with strict row-level ownership check."""
        deck = await self.repo.get_deck_by_id(deck_id=deck_id, user_id=user_id)
        if not deck or deck.user_id != user_id:
            raise NotFoundException(f"Flashcard deck '{deck_id}' not found")

        await self.repo.delete_deck(deck.id)
        await self.db.commit()

        logger.info("flashcard_deck_deleted", deck_id=deck_id, user_id=user_id)

    async def study_deck_session(
        self,
        user_id: str,
        deck_id: str,
        payload: StudySessionSubmission,
    ) -> StudySessionResponse:
        """
        Record recall self-assessments using Leitner 5-box intervals.
        Awards gamification XP and advances daily active streaks.
        """
        deck = await self.repo.get_deck_by_id(deck_id=deck_id, user_id=user_id)
        if not deck:
            raise NotFoundException(f"Flashcard deck '{deck_id}' not found")

        cards_map = {card.id: card for card in deck.cards}
        results: list[CardReviewResult] = []
        promoted_count = 0
        demoted_count = 0
        newly_mastered_count = 0

        for review in payload.reviews:
            card = cards_map.get(review.card_id)
            if not card:
                raise BadRequestException(
                    f"Card '{review.card_id}' does not belong to deck '{deck_id}'"
                )

            previous_box = card.box
            was_mastered = card.mastery_status == MasteryStatus.MASTERED

            is_promoted = card.record_review(review.rating)

            if is_promoted:
                promoted_count += 1
            elif review.rating == 1 and previous_box > 1:
                demoted_count += 1

            if not was_mastered and card.mastery_status == MasteryStatus.MASTERED:
                newly_mastered_count += 1

            results.append(
                CardReviewResult(
                    card_id=card.id,
                    previous_box=previous_box,
                    new_box=card.box,
                    is_promoted=is_promoted,
                    new_mastery_status=card.mastery_status,
                )
            )

        # Gamification: +5 base XP per card reviewed + +10 bonus per newly mastered card
        total_xp = (len(payload.reviews) * 5) + (newly_mastered_count * 10)
        await self.gamification_service.award_xp(user_id=user_id, amount=total_xp)

        await self.db.commit()

        logger.info(
            "flashcard_study_completed",
            deck_id=deck_id,
            user_id=user_id,
            reviewed=len(payload.reviews),
            promoted=promoted_count,
            xp_awarded=total_xp,
        )

        return StudySessionResponse(
            deck_id=deck_id,
            total_reviewed=len(payload.reviews),
            promoted_count=promoted_count,
            demoted_count=demoted_count,
            newly_mastered_count=newly_mastered_count,
            xp_awarded=total_xp,
            results=results,
        )

    async def _format_deck_detail_response(
        self,
        deck: FlashcardDeck,
    ) -> FlashcardDeckDetailResponse:
        stats = await self.repo.get_deck_mastery_stats(deck.id)
        cards = await self.repo.get_cards_by_deck_id(deck.id)
        cards_response = [FlashcardResponse.model_validate(card) for card in cards]

        return FlashcardDeckDetailResponse(
            id=deck.id,
            user_id=deck.user_id,
            lesson_id=deck.lesson_id,
            title=deck.title,
            description=deck.description,
            topic=deck.topic,
            card_count=deck.card_count,
            is_public=deck.is_public,
            mastered_count=stats["mastered_count"],
            learning_count=stats["learning_count"],
            new_count=stats["new_count"],
            created_at=deck.created_at,
            updated_at=deck.updated_at,
            cards=cards_response,
        )
