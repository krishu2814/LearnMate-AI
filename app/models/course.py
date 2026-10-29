import enum
import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.learning_path import LearningPathItem
    from app.models.progress import LessonProgress


class DifficultyLevel(str, enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class Course(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "courses"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    subject_tag: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    difficulty: Mapped[DifficultyLevel] = mapped_column(
        Enum(DifficultyLevel, name="difficulty_level_enum", native_enum=False),
        default=DifficultyLevel.BEGINNER,
        nullable=False,
    )
    owner_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    modules: Mapped[List["Module"]] = relationship(
        "Module",
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="Module.position",
        lazy="selectin",
    )

    def __init__(
        self,
        title: str,
        description: str,
        subject_tag: str,
        difficulty: DifficultyLevel = DifficultyLevel.BEGINNER,
        owner_id: Optional[str] = None,
        is_published: bool = True,
        id: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(id=id or str(uuid.uuid4()), **kwargs)
        self.title = title
        self.description = description
        self.subject_tag = subject_tag
        self.difficulty = difficulty
        self.owner_id = owner_id
        self.is_published = is_published

    def __repr__(self) -> str:
        return f"<Course {self.title} (difficulty={self.difficulty})>"


class Module(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "modules"

    course_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("courses.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    course: Mapped["Course"] = relationship("Course", back_populates="modules")
    lessons: Mapped[List["Lesson"]] = relationship(
        "Lesson",
        back_populates="module",
        cascade="all, delete-orphan",
        order_by="Lesson.position",
        lazy="selectin",
    )

    def __init__(
        self,
        course_id: str,
        title: str,
        position: int = 1,
        summary: Optional[str] = None,
        id: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(id=id or str(uuid.uuid4()), **kwargs)
        self.course_id = course_id
        self.title = title
        self.position = position
        self.summary = summary

    def __repr__(self) -> str:
        return f"<Module {self.title} (position={self.position})>"


class Lesson(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "lessons"

    module_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("modules.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Relationships
    module: Mapped["Module"] = relationship("Module", back_populates="lessons")
    path_items: Mapped[List["LearningPathItem"]] = relationship(
        "LearningPathItem",
        back_populates="lesson",
        cascade="all, delete-orphan",
    )
    progress_records: Mapped[List["LessonProgress"]] = relationship(
        "LessonProgress",
        back_populates="lesson",
        cascade="all, delete-orphan",
    )

    def __init__(
        self,
        module_id: str,
        title: str,
        content: str,
        estimated_minutes: int = 15,
        position: int = 1,
        id: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(id=id or str(uuid.uuid4()), **kwargs)
        self.module_id = module_id
        self.title = title
        self.content = content
        self.estimated_minutes = estimated_minutes
        self.position = position

    def __repr__(self) -> str:
        return f"<Lesson {self.title} (est={self.estimated_minutes}m)>"
