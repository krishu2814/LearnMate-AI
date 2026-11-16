import uuid

import pytest

from app.ai.prompts.flashcard_prompts import build_flashcard_generation_prompt
from app.ai.providers.gemini import GeminiProvider
from app.models.course import DifficultyLevel
from app.models.flashcard import Flashcard, FlashcardDeck, MasteryStatus


def test_flashcard_deck_and_card_models():
    user_id = str(uuid.uuid4())
    deck = FlashcardDeck(
        user_id=user_id,
        title="Async Python Internals",
        topic="Python Concurrency",
        description="High yield deck on event loops and coroutines",
    )

    assert deck.user_id == user_id
    assert deck.title == "Async Python Internals"
    assert deck.topic == "Python Concurrency"
    assert deck.card_count == 0
    assert deck.is_public is False
    assert "Async Python Internals" in repr(deck)

    card = Flashcard(
        deck_id=deck.id,
        front="What does 'await' yield control to?",
        back="The active asyncio event loop thread scheduler.",
        hint="Think about event loop scheduling.",
        key_concept="Asyncio Coroutine",
    )

    assert card.deck_id == deck.id
    assert card.box == 1
    assert card.mastery_status == MasteryStatus.NEW
    assert card.review_count == 0
    assert "box=1" in repr(card)


def test_leitner_box_transition_logic():
    deck_id = str(uuid.uuid4())
    card = Flashcard(
        deck_id=deck_id,
        front="Concept Prompt",
        back="Concept Answer",
    )

    # 1. First review: Good (rating 3) -> promotes from Box 1 to Box 2
    promoted = card.record_review(rating=3)
    assert promoted is True
    assert card.box == 2
    assert card.review_count == 1
    assert card.correct_count == 1
    assert card.mastery_status == MasteryStatus.LEARNING
    assert card.last_reviewed_at is not None

    # 2. Hard review (rating 2) -> stays in Box 2
    promoted_hard = card.record_review(rating=2)
    assert promoted_hard is False
    assert card.box == 2
    assert card.review_count == 2
    assert card.mastery_status == MasteryStatus.LEARNING

    # 3. Easy review (rating 4) -> promotes by +2 boxes (Box 2 to Box 4) -> MASTERED
    promoted_easy = card.record_review(rating=4)
    assert promoted_easy is True
    assert card.box == 4
    assert card.mastery_status == MasteryStatus.MASTERED

    # 4. Another Easy review (rating 4) -> reaches max Box 5
    card.record_review(rating=4)
    assert card.box == 5
    assert card.mastery_status == MasteryStatus.MASTERED

    # 5. Rating 1 (Again / Reset) -> resets back to Box 1, status = learning
    promoted_reset = card.record_review(rating=1)
    assert promoted_reset is False
    assert card.box == 1
    assert card.mastery_status == MasteryStatus.LEARNING


def test_build_flashcard_generation_prompt():
    prompt = build_flashcard_generation_prompt(
        topic="Database Indexing",
        num_cards=6,
        difficulty=DifficultyLevel.ADVANCED,
        lesson_title="B-Tree & Hash Indexes",
        lesson_content="B-Tree indexes maintain logarithmic depth for range scans.",
        custom_instructions="Include write amplification trade-offs",
    )

    assert "Database Indexing" in prompt
    assert "ADVANCED" in prompt
    assert "B-Tree & Hash Indexes" in prompt
    assert "logarithmic depth" in prompt
    assert "write amplification trade-offs" in prompt


@pytest.mark.asyncio
async def test_gemini_provider_mock_deck_generation():
    provider = GeminiProvider(api_key=None)

    deck_payload = await provider.generate_flashcards(
        prompt="dummy_prompt",
        topic="FastAPI Microservices",
        count=5,
        difficulty=DifficultyLevel.INTERMEDIATE,
    )

    assert "FastAPI Microservices" in deck_payload.title
    assert len(deck_payload.cards) == 5
    for c in deck_payload.cards:
        assert len(c.front) > 0
        assert len(c.back) > 0
        assert c.hint is not None
        assert c.key_concept is not None
