import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.course import Lesson
    from app.models.user import User


class ProgressStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class LessonProgress(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "lesson_progress"
    __table_args__ = (
        Index("ix_lesson_progress_user_lesson", "user_id", "lesson_id", unique=True),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    lesson_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("lessons.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[ProgressStatus] = mapped_column(
        Enum(ProgressStatus, name="progress_status_enum", native_enum=False),
        default=ProgressStatus.NOT_STARTED,
        nullable=False,
    )
    time_spent_seconds: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="lesson_progress")
    lesson: Mapped["Lesson"] = relationship("Lesson", back_populates="progress_records")

    def __init__(
        self,
        user_id: str,
        lesson_id: str,
        status: ProgressStatus = ProgressStatus.NOT_STARTED,
        time_spent_seconds: int = 0,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        id: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(id=id or str(uuid.uuid4()), **kwargs)
        self.user_id = user_id
        self.lesson_id = lesson_id
        self.status = status
        self.time_spent_seconds = time_spent_seconds
        self.started_at = started_at
        self.completed_at = completed_at

    def mark_started(self) -> None:
        if not self.started_at:
            self.started_at = datetime.now(timezone.utc)
        self.status = ProgressStatus.IN_PROGRESS

    def mark_completed(self, additional_seconds: int = 0) -> None:
        now = datetime.now(timezone.utc)
        if not self.started_at:
            self.started_at = now
        self.completed_at = now
        self.status = ProgressStatus.COMPLETED
        self.time_spent_seconds += additional_seconds

    def __repr__(self) -> str:
        return f"<LessonProgress user={self.user_id} lesson={self.lesson_id} status={self.status}>"
