import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.quiz import QuizQuestion
    from app.models.user import User


class ReviewItem(Base, UUIDMixin, TimestampMixin):
    """Spaced Repetition System (SRS) review tracker based on SM-2 algorithm."""

    __tablename__ = "review_items"
    __table_args__ = (
        Index("ix_review_items_user_question", "user_id", "question_id", unique=True),
        Index("ix_review_items_user_next_review", "user_id", "next_review_at"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    question_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("quiz_questions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    # SM-2 Spaced Repetition Parameters
    interval_days: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    repetitions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5, nullable=False)
    next_review_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        index=True,
        nullable=False,
    )
    last_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Performance & Mastery Metrics
    total_reviews: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    correct_reviews: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    consecutive_correct: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    topic_tag: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="review_items")
    question: Mapped["QuizQuestion"] = relationship("QuizQuestion", lazy="selectin")

    def __init__(
        self,
        user_id: str,
        question_id: str,
        topic_tag: str | None = None,
        interval_days: int = 1,
        repetitions: int = 0,
        ease_factor: float = 2.5,
        next_review_at: datetime | None = None,
        last_reviewed_at: datetime | None = None,
        total_reviews: int = 0,
        correct_reviews: int = 0,
        consecutive_correct: int = 0,
        id: str | None = None,
        **kwargs,
    ):
        super().__init__(id=id or str(uuid.uuid4()), **kwargs)
        self.user_id = user_id
        self.question_id = question_id
        self.topic_tag = topic_tag
        self.interval_days = interval_days
        self.repetitions = repetitions
        self.ease_factor = ease_factor
        self.next_review_at = next_review_at or datetime.now(UTC)
        self.last_reviewed_at = last_reviewed_at
        self.total_reviews = total_reviews
        self.correct_reviews = correct_reviews
        self.consecutive_correct = consecutive_correct

    def __repr__(self) -> str:
        return (
            f"<ReviewItem user={self.user_id} q={self.question_id} "
            f"interval={self.interval_days}d due={self.next_review_at}>"
        )

