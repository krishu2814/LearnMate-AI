import enum
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.course import Lesson
    from app.models.user import User


class MasteryStatus(enum.StrEnum):
    NEW = "new"
    LEARNING = "learning"
    MASTERED = "mastered"


class FlashcardDeck(Base, UUIDMixin, TimestampMixin):
    """Collection of active recall flashcards tied to a learner and optional lesson."""

    __tablename__ = "flashcard_decks"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    lesson_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("lessons.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    topic: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    card_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="flashcard_decks",
    )
    lesson: Mapped[Optional["Lesson"]] = relationship(
        "Lesson",
        lazy="selectin",
    )
    cards: Mapped[list["Flashcard"]] = relationship(
        "Flashcard",
        back_populates="deck",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
        order_by="Flashcard.box",
    )

    def __init__(
        self,
        user_id: str,
        title: str,
        topic: str,
        description: str | None = None,
        lesson_id: str | None = None,
        card_count: int = 0,
        is_public: bool = False,
        id: str | None = None,
        **kwargs,
    ):
        super().__init__(id=id or str(uuid.uuid4()), **kwargs)
        self.user_id = user_id
        self.title = title
        self.topic = topic
        self.description = description
        self.lesson_id = lesson_id
        self.card_count = card_count
        self.is_public = is_public

    def __repr__(self) -> str:
        return f"<FlashcardDeck {self.title} (cards={self.card_count})>"


class Flashcard(Base, UUIDMixin, TimestampMixin):
    """Individual flashcard with Leitner 5-box spaced interval tracking."""

    __tablename__ = "flashcards"

    deck_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("flashcard_decks.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    front: Mapped[str] = mapped_column(Text, nullable=False)
    back: Mapped[str] = mapped_column(Text, nullable=False)
    hint: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_concept: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Leitner Box Progress (Box 1 = Novice, Box 5 = Mastered)
    box: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    correct_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    mastery_status: Mapped[MasteryStatus] = mapped_column(
        Enum(MasteryStatus, name="mastery_status_enum", native_enum=False),
        default=MasteryStatus.NEW,
        nullable=False,
    )

    # Relationships
    deck: Mapped["FlashcardDeck"] = relationship(
        "FlashcardDeck",
        back_populates="cards",
    )

    def __init__(
        self,
        deck_id: str,
        front: str,
        back: str,
        hint: str | None = None,
        key_concept: str | None = None,
        box: int = 1,
        review_count: int = 0,
        correct_count: int = 0,
        last_reviewed_at: datetime | None = None,
        mastery_status: MasteryStatus = MasteryStatus.NEW,
        id: str | None = None,
        **kwargs,
    ):
        super().__init__(id=id or str(uuid.uuid4()), **kwargs)
        self.deck_id = deck_id
        self.front = front
        self.back = back
        self.hint = hint
        self.key_concept = key_concept
        self.box = box
        self.review_count = review_count
        self.correct_count = correct_count
        self.last_reviewed_at = last_reviewed_at
        self.mastery_status = mastery_status

    def record_review(self, rating: int) -> bool:
        """
        Record study rating and apply Leitner box transitions:
        Rating 1: Again (reset to Box 1, status = learning)
        Rating 2: Hard (stays in current box or Box 1)
        Rating 3: Good (promotes to next box up to 5)
        Rating 4: Easy (promotes by +2 boxes up to 5)
        Returns True if promoted, False otherwise.
        """
        self.review_count += 1
        self.last_reviewed_at = datetime.now(UTC)

        old_box = self.box
        if rating == 1:
            self.box = 1
            self.mastery_status = MasteryStatus.LEARNING
            return False
        elif rating == 2:
            self.box = max(1, self.box)
            self.mastery_status = MasteryStatus.LEARNING
            return False
        elif rating == 3:
            self.correct_count += 1
            self.box = min(5, self.box + 1)
        elif rating == 4:
            self.correct_count += 1
            self.box = min(5, self.box + 2)

        if self.box >= 4:
            self.mastery_status = MasteryStatus.MASTERED
        else:
            self.mastery_status = MasteryStatus.LEARNING

        return self.box > old_box

    def __repr__(self) -> str:
        return f"<Flashcard deck={self.deck_id} box={self.box} status={self.mastery_status}>"
