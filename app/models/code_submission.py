import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.course import Lesson
    from app.models.user import User


class CodeSubmission(Base, UUIDMixin, TimestampMixin):
    """Stores student code playground submissions and AI architectural code reviews."""

    __tablename__ = "code_submissions"

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
    language: Mapped[str] = mapped_column(String(50), default="python", nullable=False)
    source_code: Mapped[str] = mapped_column(Text, nullable=False)

    # AI Review Metrics & Feedback
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    time_complexity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    space_complexity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    review_summary: Mapped[str] = mapped_column(Text, nullable=False)
    strengths: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    issues: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)
    refactored_code: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="code_submissions")
    lesson: Mapped[Optional["Lesson"]] = relationship("Lesson", foreign_keys=[lesson_id])

    def __init__(
        self,
        user_id: str,
        title: str,
        source_code: str,
        language: str = "python",
        lesson_id: str | None = None,
        score: int = 0,
        is_passed: bool = False,
        time_complexity: str | None = None,
        space_complexity: str | None = None,
        review_summary: str = "",
        strengths: list[str] | None = None,
        issues: list[dict] | None = None,
        refactored_code: str | None = None,
        id: str | None = None,
        **kwargs,
    ):
        super().__init__(id=id or str(uuid.uuid4()), **kwargs)
        self.user_id = user_id
        self.title = title
        self.source_code = source_code
        self.language = language
        self.lesson_id = lesson_id
        self.score = score
        self.is_passed = is_passed
        self.time_complexity = time_complexity
        self.space_complexity = space_complexity
        self.review_summary = review_summary
        self.strengths = strengths or []
        self.issues = issues or []
        self.refactored_code = refactored_code

    def __repr__(self) -> str:
        return f"<CodeSubmission id={self.id} user={self.user_id} title='{self.title}' score={self.score}>"
