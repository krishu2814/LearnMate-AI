import enum
import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.course import Lesson
    from app.models.user import User


class PathStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ItemType(str, enum.Enum):
    LESSON = "lesson"
    QUIZ = "quiz"
    REVISION = "revision"


class LearningPath(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "learning_paths"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[PathStatus] = mapped_column(
        Enum(PathStatus, name="path_status_enum", native_enum=False),
        default=PathStatus.ACTIVE,
        nullable=False,
    )
    total_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    daily_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="learning_paths")
    items: Mapped[List["LearningPathItem"]] = relationship(
        "LearningPathItem",
        back_populates="learning_path",
        cascade="all, delete-orphan",
        order_by="LearningPathItem.position",
        lazy="selectin",
    )

    def __init__(
        self,
        user_id: str,
        title: str,
        goal: str,
        status: PathStatus = PathStatus.ACTIVE,
        total_days: int = 30,
        daily_minutes: int = 60,
        id: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(id=id or str(uuid.uuid4()), **kwargs)
        self.user_id = user_id
        self.title = title
        self.goal = goal
        self.status = status
        self.total_days = total_days
        self.daily_minutes = daily_minutes

    def __repr__(self) -> str:
        return f"<LearningPath '{self.title}' (user_id={self.user_id}, status={self.status})>"


class LearningPathItem(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "learning_path_items"

    learning_path_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("learning_paths.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    lesson_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("lessons.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    item_type: Mapped[ItemType] = mapped_column(
        Enum(ItemType, name="item_type_enum", native_enum=False),
        default=ItemType.LESSON,
        nullable=False,
    )
    is_optional: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    learning_path: Mapped["LearningPath"] = relationship("LearningPath", back_populates="items")
    lesson: Mapped["Lesson"] = relationship("Lesson", back_populates="path_items", lazy="selectin")

    def __init__(
        self,
        learning_path_id: str,
        lesson_id: str,
        position: int = 1,
        item_type: ItemType = ItemType.LESSON,
        is_optional: bool = False,
        is_completed: bool = False,
        id: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(id=id or str(uuid.uuid4()), **kwargs)
        self.learning_path_id = learning_path_id
        self.lesson_id = lesson_id
        self.position = position
        self.item_type = item_type
        self.is_optional = is_optional
        self.is_completed = is_completed

    def __repr__(self) -> str:
        return f"<LearningPathItem path={self.learning_path_id} lesson={self.lesson_id} pos={self.position}>"
